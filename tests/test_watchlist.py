import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, UserWatchlist


class TestWatchlistEndpoints:
    async def test_add_ticker_to_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"
        response = await authenticated_client.post(
            f"/api/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Verify ticker was added to database
        stmt = select(UserWatchlist).filter(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol,
        )
        result = await async_test_db.execute(stmt)
        watchlist_entry = result.scalars().first()
        assert watchlist_entry is not None
        assert watchlist_entry.ticker == ticker_symbol

    async def test_add_duplicate_ticker_to_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"
        # Add ticker first time
        response1 = await authenticated_client.post(
            f"/api/users/me/watchlist/{ticker_symbol}"
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to add the same ticker again
        response2 = await authenticated_client.post(
            f"/api/users/me/watchlist/{ticker_symbol}"
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

    async def test_watchlist_requires_authentication(self, async_client: AsyncClient):
        # Test GET endpoint
        response = await async_client.get("/api/users/me/watchlist")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test POST endpoint
        response = await async_client.post("/api/users/me/watchlist/AAPL")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test DELETE endpoint
        response = await async_client.delete("/api/users/me/watchlist/AAPL")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("ticker_symbol", ["aapl", "AAPL", "AaPl"])
    async def test_ticker_case_insensitive(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
        ticker_symbol: str,
    ):
        response = await authenticated_client.post(
            f"/api/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the ticker is stored as uppercase
        stmt = select(UserWatchlist).filter(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol.upper(),
        )
        result = await async_test_db.execute(stmt)
        watchlist_entry = result.scalars().first()
        assert watchlist_entry is not None
        assert watchlist_entry.ticker == ticker_symbol.upper()

    async def test_remove_ticker_from_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"
        # First add the ticker
        await authenticated_client.post(f"/api/users/me/watchlist/{ticker_symbol}")

        # Then remove it
        response = await authenticated_client.delete(
            f"/api/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify ticker was removed from database
        stmt = select(UserWatchlist).filter(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol,
        )
        result = await async_test_db.execute(stmt)
        watchlist_entry = result.scalars().first()
        assert watchlist_entry is None

    async def test_remove_ticker_not_in_watchlist(
        self, authenticated_client: AsyncClient, async_test_db: AsyncSession
    ):
        # Try to remove a ticker that was never added
        response = await authenticated_client.delete("/api/users/me/watchlist/FAKE")
        assert response.status_code == status.HTTP_404_NOT_FOUND
