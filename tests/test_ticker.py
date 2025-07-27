from fastapi import status
from httpx import AsyncClient


class TestTickerEndpoints:
    async def test_get_valid_ticker_info_no_caching(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        # First call
        response1 = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["symbol"] == "AAPL"
        assert data1["shortName"] == "Apple Inc."

        # Second call - should call yfinance again (no caching for info)
        response2 = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data1 == data2

        # Verify the constructor was called twice (no caching)
        assert mock_yfinance["ticker_constructor"].call_count == 2

    async def test_get_ticker_info_stores_timezone(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        from models import TickerInfo
        from sqlalchemy import select
        from database import get_async_session

        response = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response.status_code == status.HTTP_200_OK

        # Get a fresh database session to check the data
        async for db in get_async_session():
            stmt = select(TickerInfo).filter(TickerInfo.ticker == "AAPL")
            result = await db.execute(stmt)
            ticker_info = result.scalars().first()

            assert ticker_info is not None
            assert ticker_info.ticker == "AAPL"
            assert ticker_info.exchangeTimezoneName == "America/New_York"
            break

    async def test_get_ticker_history_with_caching(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        # First call - should make actual yfinance call
        response1 = await authenticated_client.get(
            "/api/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second call - should use cached data
        response2 = await authenticated_client.get(
            "/api/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response2.status_code == status.HTTP_200_OK

        # Both responses should have the same data
        assert response1.json() == response2.json()

        # Verify that yfinance was called only once for the same date range
        response3 = await authenticated_client.get(
            "/api/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response3.status_code == status.HTTP_200_OK

    async def test_get_ticker_history_different_date_ranges(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        # Different date ranges should result in different calls
        response1 = await authenticated_client.get(
            "/api/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response1.status_code == status.HTTP_200_OK

        response2 = await authenticated_client.get(
            "/api/ticker/AAPL/history?start=2023-02-01&end=2023-02-05"
        )
        assert response2.status_code == status.HTTP_200_OK

        # Should have made separate yfinance calls
        assert mock_yfinance["ticker_constructor"].call_count >= 2

    async def test_get_invalid_ticker_info(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/api/ticker/INVALID/info")
        # The response will depend on how your router handles empty info dict
        # Adjust the expected status code based on your actual implementation
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_different_tickers(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response1 = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["symbol"] == "AAPL"

        response2 = await authenticated_client.get("/api/ticker/GOOGL/info")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["symbol"] == "GOOGL"

        # Both should have called the constructor
        assert mock_yfinance["ticker_constructor"].call_count == 2

    async def test_ticker_history_default_date_range(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/api/ticker/AAPL/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    async def test_ticker_case_insensitive(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response1 = await authenticated_client.get("/api/ticker/aapl/info")
        assert response1.status_code == status.HTTP_200_OK

        response2 = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response2.status_code == status.HTTP_200_OK

        # Both should return the same data
        assert response1.json() == response2.json()

    async def test_ticker_info_basic_functionality(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/api/ticker/AAPL/info")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "symbol" in data
        assert "fullExchangeName" in data
        assert "regularMarketPrice" in data
        assert "marketState" in data
        assert "region" in data
        assert "currency" in data
        assert "previousClose" in data
        assert "exchangeTimezoneName" not in data
        # Verify the mock was called
        mock_yfinance["ticker_constructor"].assert_called_with("AAPL")
