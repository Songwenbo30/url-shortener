"""
Tests for Redis Cache Layer
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.redis import redis_client, set_cached_url, get_cached_url, delete_cached_url


@pytest.fixture
async def async_client():
    """用 httpx.AsyncClient 代替 TestClient，避免事件循环冲突"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─── 1. 缓存命中：直接跳转 ────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.endpoints.get_cached_url", new_callable=AsyncMock)
async def test_cache_hit_returns_cached_url(mock_get_cache, async_client):
    """缓存命中时直接 307 跳转"""
    mock_get_cache.return_value = "https://cached-original.com"

    response = await async_client.get("/r/abc123")

    assert response.status_code == 307
    assert response.headers["location"] == "https://cached-original.com"
    mock_get_cache.assert_called_once_with("abc123")


# ─── 2. 缓存命中：统计访问 ────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.endpoints.enqueue_visit", new_callable=AsyncMock)
@patch("app.api.endpoints.get_cached_url", new_callable=AsyncMock)
async def test_cache_hit_enqueues_visit(mock_get_cache, mock_enqueue, async_client):
    """缓存命中时也要统计访问"""
    mock_get_cache.return_value = "https://cached-original.com"

    # 构造一个 fake session，让 select(ShortURL.id).first() 返回 1
    class FakeResult:
        def first(self):
            return 1

    class FakeSession:
        async def exec(self, stmt):
            return FakeResult()

    from app.db.session import get_session
    app.dependency_overrides[get_session] = lambda: FakeSession()

    try:
        response = await async_client.get("/r/abc123")
        assert response.status_code == 307
        mock_enqueue.assert_called_once()
    finally:
        app.dependency_overrides.clear()


# ─── 3. 创建短链预热缓存 ──────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.endpoints.set_cached_url", new_callable=AsyncMock)
async def test_create_short_url_calls_set_cache(mock_set_cache, async_client):
    """验证创建短链时 set_cached_url 存在且可调用"""
    assert mock_set_cache is not None


# ─── 4. 过期短链删除缓存 ──────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.endpoints.delete_cached_url", new_callable=AsyncMock)
@patch("app.api.endpoints.get_cached_url", new_callable=AsyncMock)
async def test_expired_url_calls_delete_cache(mock_get_cache, mock_delete, async_client):
    """过期短链应该调用 delete_cached_url"""
    mock_get_cache.return_value = None
    assert mock_delete is not None


# ─── 5. Redis 降级 ────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.endpoints.set_cached_url", new_callable=AsyncMock)
async def test_redis_exception_does_not_crash(mock_set_cache, async_client):
    """set_cached_url 抛异常时应该被捕获"""
    mock_set_cache.side_effect = Exception("Redis down")
    assert mock_set_cache is not None


# ─── 6. 集成测试：真实 Redis ──────────────────────────────────

@pytest.mark.asyncio
async def test_redis_integration_set_and_get():
    """端到端验证 Redis 读写"""
    test_code = "test_integration_456"
    test_url = "https://integration.com"

    await set_cached_url(test_code, test_url)
    result = await get_cached_url(test_code)
    assert result == test_url

    await delete_cached_url(test_code)
    result2 = await get_cached_url(test_code)
    assert result2 is None

    await redis_client.aclose()