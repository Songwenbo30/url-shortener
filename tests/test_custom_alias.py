import pytest


@pytest.mark.anyio
async def test_create_with_custom_alias(client):
    """指定 custom_alias，应成功创建并返回 201"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "custom_alias": "my-link"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["short_code"] == "my-link"
    assert data["original_url"] == "https://www.example.com"


@pytest.mark.anyio
async def test_custom_alias_conflict(client):
    """同一个 alias 用两次，第二次应返回 409"""
    await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "custom_alias": "dup-link"}
    )
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.other.com", "custom_alias": "dup-link"}
    )
    assert resp.status_code == 409
    assert "already taken" in resp.json()["detail"]


@pytest.mark.anyio
async def test_custom_alias_invalid_chars(client):
    """非法字符应返回 422"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "custom_alias": "bad@link!"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_custom_alias_too_short(client):
    """太短的 alias 应返回 422"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com", "custom_alias": "ab"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_no_alias_uses_auto_generation(client):
    """不传 custom_alias，行为与原来一致"""
    resp = await client.post(
        "/shorten",
        json={"url": "https://www.example.com"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "short_code" in data
    # 自动生成的短码不应包含用户指定的字符串
    assert data["short_code"] != "my-link"