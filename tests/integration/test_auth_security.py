import os

import httpx
import pytest


BASE_URL = os.getenv("INTEGRATION_BASE_URL")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        BASE_URL is None,
        reason="defina INTEGRATION_BASE_URL para executar contra a API real",
    ),
]


async def test_logout_revokes_access_token() -> None:
    assert BASE_URL is not None

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        login = await client.post(
            "/api/v1/auth/token",
            data={
                "username": os.environ["SEED_USERNAME"],
                "password": os.environ["SEED_PASSWORD"],
            },
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        before_logout = await client.get("/api/v1/products", headers=headers)
        assert before_logout.status_code == 200, before_logout.text

        logout = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout.status_code == 204, logout.text

        after_logout = await client.get("/api/v1/products", headers=headers)
        assert after_logout.status_code == 401, after_logout.text
