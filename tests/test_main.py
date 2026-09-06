import asyncio
import pytest
from sqlmodel import select, func
from app.db.models import ShortURL, URLVisit
from app.db.session import create_async_session
from app.utils.visit_queue import flush_queue
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestShortURLAPI:

    async def test_full_lifecycle(self, client):
        """
        Test the full lifecycle of a short URL:
        1. Create short URL
        2. Redirect to original URL
        3. Check visit statistics
        """
        original_url = "https://google.com"

        # 1️⃣ Create short URL
        response = await client.post("/shorten", json={"url": original_url})
        assert response.status_code == 201
        response_data = response.json()
        short_code = response_data["short_code"]

        assert response_data["original_url"] == original_url
        assert response_data["short_url"].endswith(f"/{short_code}")

        # 2️⃣ Redirect
        redirect_response = await client.get(f"/r/{short_code}", follow_redirects=False)
        assert redirect_response.status_code in (302, 307)
        assert redirect_response.headers["location"] == original_url

        # Flush visit queue to ensure visit counting works
        await flush_queue()

        # 3️⃣ Check statistics
        stats_response = await client.get(f"/stats/{short_code}")
        stats_data = stats_response.json()
        assert stats_data["original_url"] == original_url
        assert stats_data["total_visits"] == 1

    async def test_idempotent_short_url_creation(self, client):
        """Ensure that creating a short URL for the same original URL is idempotent."""
        original_url = "https://unique.test"

        first_response = await client.post("/shorten", json={"url": original_url})
        second_response = await client.post("/shorten", json={"url": original_url})

        first_data = first_response.json()
        second_data = second_response.json()

        assert first_data["short_code"] == second_data["short_code"]
        assert first_data["original_url"] == second_data["original_url"]

    async def test_short_url_not_found(self, client):
        """Accessing a non-existing short code should return 404."""
        response = await client.get("/r/invalidCode", follow_redirects=False)
        assert response.status_code == 404
        assert response.json()["detail"] == "URL not found"

    @patch("app.api.endpoints.set_cached_url", new_callable=AsyncMock)
    @patch("app.api.endpoints.get_cached_url", new_callable=AsyncMock, return_value=None)
    async def test_high_concurrency_redirects(self, mock_get, mock_set, client):
        """
        Test concurrent access to a short URL to ensure visit counting works.
        Redis is mocked to avoid MaxConnectionsError.
        """
        original_url = "https://stress.test"
        create_response = await client.post("/shorten", json={"url": original_url})
        assert create_response.status_code == 201
        short_code = create_response.json()["short_code"]

        concurrent_requests = 100
        await asyncio.gather(
            *[client.get(f"/r/{short_code}", follow_redirects=False) for _ in range(concurrent_requests)]
        )
        await flush_queue()

        stats_response = await client.get(f"/stats/{short_code}")
        assert stats_response.json()["total_visits"] == concurrent_requests

    @patch("app.api.endpoints.set_cached_url", new_callable=AsyncMock)
    @patch("app.api.endpoints.get_cached_url", new_callable=AsyncMock, return_value=None)
    async def test_atomic_visit_counter(self, mock_get, mock_set, client):
        """
        Test atomicity of visit counter under high concurrency.
        Redis is mocked to avoid connection pool exhaustion.
        """
        original_url = "https://atomic.test"
        create_response = await client.post("/shorten", json={"url": original_url})
        assert create_response.status_code == 201
        short_code = create_response.json()["short_code"]

        concurrent_requests = 50
        await asyncio.gather(
            *[client.get(f"/r/{short_code}", follow_redirects=False) for _ in range(concurrent_requests)]
        )
        await flush_queue()

        # 1️⃣ Check total_visits via API
        stats_response = await client.get(f"/stats/{short_code}")
        stats_data = stats_response.json()
        assert stats_data["total_visits"] == concurrent_requests

        # 2️⃣ Check actual URLVisit records in DB
        session_factory = create_async_session()
        async with session_factory() as session:
            stmt = select(ShortURL).where(ShortURL.short_code == short_code)
            short_url = (await session.exec(stmt)).first()
            assert short_url is not None

            stmt = select(func.count()).select_from(URLVisit).where(URLVisit.short_url_id == short_url.id)
            visit_count = (await session.exec(stmt)).one()
            assert visit_count == concurrent_requests

    async def test_invalid_url_validation(self, client):
        """Ensure invalid URLs are rejected by the API."""
        response = await client.post("/shorten", json={"url": "not-a-url"})
        assert response.status_code == 422

        error_detail = response.json()["detail"][0]
        assert "url" in error_detail["loc"]
        assert error_detail["type"] in ("value_error.url", "url_parsing")