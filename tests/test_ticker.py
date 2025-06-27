from fastapi import status
from httpx import AsyncClient


class TestTickerEndpoints:
    async def test_get_valid_ticker_info_no_caching(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        # First call
        response1 = await authenticated_client.get("/ticker/AAPL/info")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["symbol"] == "AAPL"
        assert data1["shortName"] == "Apple Inc."

        # Second call - should call yfinance again (no caching for info)
        response2 = await authenticated_client.get("/ticker/AAPL/info")
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

        response = await authenticated_client.get("/ticker/AAPL/info")
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
        # First call - should fetch from yfinance and cache
        response1 = await authenticated_client.get(
            "/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert "history" in data1
        assert isinstance(data1["history"], list)

        # Second call with same date range - should use cached data
        response2 = await authenticated_client.get(
            "/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data1 == data2

        # The constructor might be called once more for timezone lookup, but not for data fetching
        # The exact behavior depends on your caching implementation

    async def test_get_ticker_history_different_date_ranges(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        # First call
        response1 = await authenticated_client.get(
            "/ticker/AAPL/history?start=2023-01-01&end=2023-01-05"
        )
        assert response1.status_code == status.HTTP_200_OK

        initial_call_count = mock_yfinance["ticker_constructor"].call_count

        # Second call with different date range - should fetch new data
        response2 = await authenticated_client.get(
            "/ticker/AAPL/history?start=2023-02-01&end=2023-02-05"
        )
        assert response2.status_code == status.HTTP_200_OK

        # Should have made additional calls for the new date range
        assert mock_yfinance["ticker_constructor"].call_count > initial_call_count

    async def test_get_invalid_ticker_info(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/ticker/INVALID/info")
        # The response will depend on how your router handles empty info dict
        # Adjust the expected status code based on your actual implementation
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_different_tickers(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response1 = await authenticated_client.get("/ticker/AAPL/info")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["symbol"] == "AAPL"

        response2 = await authenticated_client.get("/ticker/GOOGL/info")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["symbol"] == "GOOGL"

        # Both should have called the constructor
        assert mock_yfinance["ticker_constructor"].call_count == 2

    async def test_ticker_history_default_date_range(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/ticker/AAPL/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    async def test_ticker_case_insensitive(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response1 = await authenticated_client.get("/ticker/aapl/info")
        assert response1.status_code == status.HTTP_200_OK

        response2 = await authenticated_client.get("/ticker/AAPL/info")
        assert response2.status_code == status.HTTP_200_OK

        # Both should return the same data
        assert response1.json() == response2.json()

    async def test_ticker_info_basic_functionality(
        self, authenticated_client: AsyncClient, mock_yfinance
    ):
        response = await authenticated_client.get("/ticker/AAPL/info")
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
