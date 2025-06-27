import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User


class TestAuthenticationEndpoints:
    async def test_register_new_user(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        user_data = {"email": "newuser@example.com", "password": "strongpAssword123!"}

        response = await async_client.post("/auth/register", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "id" in data
        assert data["email"] == user_data["email"]
        assert "password" not in data

        # Verify user was created in mock database
        stmt = select(User).filter(User.email == user_data["email"])
        result = await async_test_db.execute(stmt)
        created_user = result.scalars().first()
        assert created_user is not None
        assert created_user.email == user_data["email"]

    async def test_register_duplicate_email(
        self, async_client: AsyncClient, test_user: User, async_test_db: AsyncSession
    ):
        user_data = {"email": test_user.email, "password": "anotherpassword123"}

        response = await async_client.post("/auth/register", json=user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_register_invalid_email(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        user_data = {"email": "invalid-email-format", "password": "strongpassword123"}

        response = await async_client.post("/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_weak_password(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        user_data = {"email": "newuser@example.com", "password": "123"}

        response = await async_client.post("/auth/register", json=user_data)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    async def test_login_valid_credentials(
        self, async_client: AsyncClient, test_user: User, async_test_db: AsyncSession
    ):
        login_data = {"username": test_user.email, "password": "P@ssw0rd"}

        response = await async_client.post("/auth/login", data=login_data)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert "equisightauth" in response.cookies
        assert response.cookies["equisightauth"] is not None

    async def test_login_invalid_email(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        login_data = {"username": "nonexistent@example.com", "password": "anypassword"}

        response = await async_client.post("/auth/login", data=login_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_login_invalid_password(
        self, async_client: AsyncClient, test_user: User, async_test_db: AsyncSession
    ):
        login_data = {"username": test_user.email, "password": "wrongpassword"}

        response = await async_client.post("/auth/login", data=login_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_login_missing_credentials(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        # Missing password
        response = await async_client.post(
            "/auth/login", data={"username": "test@example.com"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing username
        response = await async_client.post("/auth/login", data={"password": "password"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_protected_endpoint_with_valid_token(
        self, authenticated_client: AsyncClient, async_test_db: AsyncSession
    ):
        # Use any protected endpoint - watchlist for example
        response = await authenticated_client.get("/users/me/watchlist")
        assert response.status_code == status.HTTP_200_OK

    async def test_protected_endpoint_without_token(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        response = await async_client.get("/users/me/watchlist")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_protected_endpoint_with_invalid_token(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await async_client.get("/users/me/watchlist", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/users/me/watchlist",
            "/ticker/AAPL/info",
            "/ticker/AAPL/history",
        ],
    )
    async def test_multiple_protected_endpoints_require_auth(
        self, async_client: AsyncClient, endpoint: str, async_test_db: AsyncSession
    ):
        response = await async_client.get(endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_expiration_handling(
        self, async_client: AsyncClient, async_test_db: AsyncSession
    ):
        # This would require creating an expired token or waiting for expiration
        # Implementation depends on your token expiration logic
        expired_token = "expired_jwt_token_here"
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = await async_client.get("/users/me/watchlist", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
