from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_request_id_header_is_returned() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health/live", headers={"X-Request-Id": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-123"
