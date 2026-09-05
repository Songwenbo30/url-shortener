import pytest
from sqlmodel import select
from datetime import datetime, timedelta
from app.db.session import create_async_session
from app.db.models import ShortURL


@pytest.mark.anyio
async def test_create_with_ttl(client):
    """指定 expires_in_days，应成功创建且短链可访问"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "expires_in_days": 7}
    )
    assert resp.status_code == 201
    # 此时应该能正常重定向
    short_code = resp.json()["short_code"]
    redirect_resp = await client.get(f"/r/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code in (302, 307)


@pytest.mark.anyio
async def test_expired_url_returns_410(client):
    """正常创建短链后，直接修改数据库将 expires_at 设为过去时间，验证访问返回 410"""
    # 先正常创建一个
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "expires_in_days": 1}
    )
    short_code = resp.json()["short_code"]

    # 直接改数据库，把 expires_at 设为过去
    session_factory = create_async_session()
    async with session_factory() as session:
        stmt = select(ShortURL).where(ShortURL.short_code == short_code)
        su = (await session.exec(stmt)).first()
        su.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    # 现在访问应该返回 410
    resp = await client.get(f"/r/{short_code}", follow_redirects=False)
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_no_expiry_by_default(client):
    """不指定 expires_in_days，短链永不过期"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com"}
    )
    assert resp.status_code == 201
    short_code = resp.json()["short_code"]
    # 应该能正常访问
    redirect_resp = await client.get(f"/r/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code in (302, 307)


@pytest.mark.anyio
async def test_invalid_expires_in_days(client):
    """expires_in_days 为负数或 0 应返回 422"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "expires_in_days": 0}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_stats_for_expired_url(client):
    """过期短链访问统计仍可查询（410 不影响 stats 端点）"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "expires_in_days": 1}
    )
    short_code = resp.json()["short_code"]

    # 让它过期
    from app.db.session import create_async_session
    session_factory = create_async_session()
    async with session_factory() as session:
        stmt = select(ShortURL).where(ShortURL.short_code == short_code)
        su = (await session.exec(stmt)).first()
        su.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    # stats 仍然能查到
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
