import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import BackgroundTasks

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.core.setting import settings
from app.db.session import get_session


class ImmediateBackgroundTasks(BackgroundTasks):
    def add_task(self, func, *args, **kwargs):
        return func(*args, **kwargs)


def override_background_tasks():
    return ImmediateBackgroundTasks()


test_engine = create_async_engine(settings.PG_DSN)

TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session
        await session.commit()


@pytest.fixture(scope="session", autouse=True)
async def init_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def clean_data():
    async with test_engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
    yield


@pytest.fixture
async def client():
    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[BackgroundTasks] = override_background_tasks

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
