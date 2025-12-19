from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, field_validator
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.utils.visit_queue import enqueue_visit


from app.db.models import ShortURL
from app.db.session import get_session
from app.utils.shortcode_generator import generate_short_code

router = APIRouter()


class URLCreate(BaseModel):
    url: HttpUrl

    @field_validator("url", mode="after")
    @classmethod
    def normalize(cls, v: HttpUrl) -> str:
        return str(v).rstrip("/")


class URLResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str


class StatsResponse(BaseModel):
    original_url: str
    total_visits: int


@router.post(
    "/shorten",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_short_url(
    payload: URLCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ShortURL).where(ShortURL.original_url == payload.url)
    result = await session.exec(stmt)
    short_url = result.first()

    if short_url:
        base_url = str(request.base_url).rstrip("/")
        return URLResponse(
            short_code=short_url.short_code,
            original_url=short_url.original_url,
            short_url=f"{base_url}/{short_url.short_code}",
        )

    max_retries = 5
    for retry in range(max_retries):
        code = generate_short_code(payload.url)
        short_url = ShortURL(
            original_url=payload.url,
            short_code=code,
        )
        session.add(short_url)
        try:
            await session.commit()
            await session.refresh(short_url)
            break
        except IntegrityError:
            await session.rollback()
            if retry == max_retries - 1:
                raise HTTPException(status_code=500, detail="Failed to generate unique short code")

    base_url = str(request.base_url).rstrip("/")
    return URLResponse(
        short_code=short_url.short_code,
        original_url=short_url.original_url,
        short_url=f"{base_url}/{short_url.short_code}",
    )


@router.get("/r/{short_code}", response_class=RedirectResponse)
async def redirect(
    short_code: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.exec(stmt)
    short_url = result.first()

    if not short_url:
        raise HTTPException(status_code=404, detail="URL not found")

    client_ip = request.client.host if request.client else "unknown"
    await enqueue_visit(short_url.id, client_ip)
    return RedirectResponse(url=short_url.original_url)


@router.get("/stats/{short_code}", response_model=StatsResponse)
async def stats(
    short_code: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.exec(stmt)
    short_url = result.first()

    if not short_url:
        raise HTTPException(status_code=404, detail="URL not found")

    return StatsResponse(
        original_url=short_url.original_url,
        total_visits=short_url.total_visits,
    )
