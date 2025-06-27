import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, UserWatchlist


class TestWatchlistEndpoints:
    async def test_get_empty_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
    ):
        # Empty watchlist
        response = await authenticated_client.get("/users/me/watchlist")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["identifier"] == test_user.email
        assert data["tickers"] == []

    async def test_add_ticker_to_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"

        # Adding ticker to watchlist
        response = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}"
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify ticker was added to database
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol.upper(),
        )
        result = await async_test_db.execute(stmt)
        watchlist_item = result.scalars().first()

        assert watchlist_item is not None
        assert watchlist_item.ticker == ticker_symbol.upper()
        assert watchlist_item.user_id == test_user.id

    async def test_add_duplicate_ticker_to_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        # Duplicate ticker test
        ticker_symbol = "AAPL"

        # Add ticker first time
        response1 = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to add same ticker again
        response2 = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

    async def test_get_watchlist_with_tickers(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        # Add multiple tickers
        tickers = ["AAPL", "GOOGL", "MSFT"]

        for ticker in tickers:
            response = await authenticated_client.post(f"/users/me/watchlist/{ticker}")
            assert response.status_code == status.HTTP_201_CREATED

        # Get watchlist
        response = await authenticated_client.get("/users/me/watchlist")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["identifier"] == test_user.email
        assert len(data["tickers"]) == 3
        assert set(data["tickers"]) == set(tickers)

    async def test_watchlist_requires_authentication(self, async_client: AsyncClient):
        # Test GET without authentication
        response = await async_client.get("/users/me/watchlist")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test POST without authentication
        response = await async_client.post("/users/me/watchlist/AAPL")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test DELETE without authentication
        response = await async_client.delete("/users/me/watchlist/AAPL")
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
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Verify ticker is stored in uppercase
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol.upper(),
        )
        result = await async_test_db.execute(stmt)
        watchlist_item = result.scalars().first()

        assert watchlist_item is not None
        assert watchlist_item.ticker == "AAPL"

    async def test_remove_ticker_from_watchlist(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"

        # Add ticker to watchlist
        await authenticated_client.post(f"/users/me/watchlist/{ticker_symbol}")

        # Remove ticker from watchlist
        response = await authenticated_client.delete(
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify ticker was removed
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == test_user.id,
            UserWatchlist.ticker == ticker_symbol.upper(),
        )
        result = await async_test_db.execute(stmt)
        watchlist_item = result.scalars().first()
        assert watchlist_item is None

    async def test_remove_ticker_not_in_watchlist(
        self,
        authenticated_client: AsyncClient,
    ):
        # Attempt to remove a ticker that hasn't been added
        response = await authenticated_client.delete("/users/me/watchlist/FAKE")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_add_position_to_ticker(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AAPL"
        # Add ticker to watchlist first
        await authenticated_client.post(f"/users/me/watchlist/{ticker_symbol}")

        position_data = {"direction": "SELL", "quantity": 10, "unitCost": 210.5}
        response = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position_data
        )
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["direction"] == position_data["direction"]
        assert data["quantity"] == position_data["quantity"]
        assert data["unitCost"] == position_data["unitCost"]

    async def test_get_ticker_positions(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "MSFT"
        # Add ticker to watchlist
        await authenticated_client.post(f"/users/me/watchlist/{ticker_symbol}")

        # Add positions
        position1 = {"direction": "BUY", "quantity": 5, "unitCost": 300.0}
        position2 = {"direction": "SELL", "quantity": 5, "unitCost": 350.345435}
        position3 = {"direction": "BUY", "quantity": 20, "unitCost": 295.324}
        await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position1
        )
        await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position2
        )
        await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position3
        )

        # Get positions for the ticker
        response = await authenticated_client.get(
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["positions"]) == 3

    async def test_update_ticker_position(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "GOOGL"
        await authenticated_client.post(f"/users/me/watchlist/{ticker_symbol}")
        position_data = {"direction": "BUY", "quantity": 12, "unitCost": 145.67}
        response = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position_data
        )
        position_id = response.json()["id"]

        update_data = {"direction": "BUY", "quantity": 15, "unitCost": 155.23}
        response = await authenticated_client.put(
            f"/users/me/watchlist/{ticker_symbol}/positions/{position_id}",
            json=update_data,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["unitCost"] == update_data["unitCost"]
        assert data["quantity"] == update_data["quantity"]

    async def test_delete_ticker_position(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        async_test_db: AsyncSession,
        mock_yfinance,
    ):
        ticker_symbol = "AMZN"
        await authenticated_client.post(f"/users/me/watchlist/{ticker_symbol}")
        position_data = {"direction": "BUY", "quantity": 5, "unitCost": 220.12}
        response = await authenticated_client.post(
            f"/users/me/watchlist/{ticker_symbol}/positions", json=position_data
        )
        position_id = response.json()["id"]

        response = await authenticated_client.delete(
            f"/users/me/watchlist/{ticker_symbol}/positions/{position_id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify the position is deleted
        response = await authenticated_client.get(
            f"/users/me/watchlist/{ticker_symbol}"
        )
        assert len(response.json()["positions"]) == 0
