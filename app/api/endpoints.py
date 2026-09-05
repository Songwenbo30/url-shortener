from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, field_validator
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.utils.visit_queue import enqueue_visit
from datetime import datetime, timedelta


from app.db.models import ShortURL
from app.db.session import get_session
from app.utils.shortcode_generator import generate_short_code

router = APIRouter()


class URLCreate(BaseModel):
    url: HttpUrl
    custom_alias: str | None = None  # 新增:可选字段
    expires_in_days: int | None = None  # 新增:几天后过期，None 表示永不过期

    @field_validator("url", mode="after")
    @classmethod
    def normalize(cls, v: HttpUrl) -> str:
        return str(v).rstrip("/")

    @field_validator("custom_alias", mode="after")
    @classmethod
    def validate_alias(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 3 or len(v) > 20:
            raise ValueError("custom_alias must be between 3 and 20 characters")
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("custom_alias can only contain letters, digits, hyphens and underscores")
        return v

    @field_validator("expires_in_days", mode="after")
    @classmethod
    def validate_expires_in_days(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("expires_in_days must be a positive integer")
        return v


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
    # 新增：计算过期时间
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    # 1. 幂等检查：已存在直接返回
    stmt = select(ShortURL).where(ShortURL.original_url == payload.url)
    result = await session.exec(stmt)
    existing = result.first()

    if existing:
        base_url = str(request.base_url).rstrip("/")
        return URLResponse(
            short_code=existing.short_code,
            original_url=existing.original_url,
            short_url=f"{base_url}/{existing.short_code}",
        )

    # 2. URL 不存在，创建新记录
    if payload.custom_alias:
        code = payload.custom_alias
        short_url = ShortURL(
            original_url=payload.url,
            short_code=code,
            expires_at=expires_at,
        )
        session.add(short_url)
        try:
            await session.commit()
            await session.refresh(short_url)
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Short code '{code}' is already taken"
            )
    else:
        max_retries = 5
        for retry in range(max_retries):
            code = generate_short_code(payload.url)
            short_url = ShortURL(
                original_url=payload.url,
                short_code=code,
                expires_at=expires_at,
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

        # 新增:过期判断
    if short_url.expires_at and short_url.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="URL has expired")

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
