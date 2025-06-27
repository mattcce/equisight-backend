import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from typing import AsyncGenerator
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from main import app
from database import get_async_session
from models import Base, User
from auth import current_active_user
from unittest.mock import MagicMock
import pandas as pd
from auth import CustomPasswordHelper


# Async database session
@pytest.fixture(scope="function")
async def async_test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingAsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestingAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with TestingAsyncSessionLocal() as session:
        yield session

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# async test client for asynchronous tests
@pytest.fixture(scope="function")
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(async_test_db: AsyncSession):
    # Instantiate custom password helper
    password_helper = CustomPasswordHelper()

    # Define plain text password for user
    plain_password = "P@ssw0rd"

    hashed_password = password_helper.hash(plain_password)

    user = User(
        id=1,  # Set a predictable ID
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)
    return user


# Override current_active_user dependency
@pytest.fixture
async def authenticated_client(async_client: AsyncClient, test_user: User):
    def override_get_current_user():
        return test_user

    app.dependency_overrides[current_active_user] = override_get_current_user

    yield async_client

    app.dependency_overrides.clear()


def get_mock_ticker_info(symbol: str) -> dict:
    """Returns mock data for yfinance.Ticker(symbol).info based on the actual yfinance API structure"""
    base_info = {
        "symbol": symbol.upper(),
        "longName": f"{symbol.upper()} Inc.",
        "shortName": f"{symbol.upper()} Inc.",
        "exchangeTimezoneName": "America/New_York",
        "exchangeTimezoneShortName": "EST",
        "gmtOffSetMilliseconds": -18000000,
        "market": "us_market",
        "exchange": "NMS",
        "quoteType": "EQUITY",
        "currency": "USD",
        "marketState": "REGULAR",
        "fullExchangeName": "NasdaqGS",
        "region": "US",
        "financialCurrency": "USD",
        "currentPrice": 200.0,
        "previousClose": 199.0,
        "open": 200.5,
        "dayLow": 199.0,
        "dayHigh": 201.0,
        "regularMarketPreviousClose": 199.0,
        "regularMarketOpen": 200.5,
        "regularMarketDayLow": 199.0,
        "regularMarketDayHigh": 201.0,
        "regularMarketPrice": 200.0,
        "regularMarketVolume": 1000000,
        "averageVolume": 1000000,
        "marketCap": 3000000000000,
        "beta": 1.2,
        "trailingPE": 25.0,
        "forwardPE": 22.0,
        "dividendRate": 1.0,
        "dividendYield": 0.005,
        "payoutRatio": 0.25,
        "bookValue": 8.0,
        "priceToBook": 25.0,
        "earningsGrowth": 0.10,
        "revenueGrowth": 0.08,
        "totalRevenue": 400000000000,
        "totalDebt": 100000000000,
        "totalCash": 50000000000,
        "debtToEquity": 125.0,
        "returnOnAssets": 0.20,
        "returnOnEquity": 1.5,
        "grossMargins": 0.40,
        "operatingMargins": 0.30,
        "ebitdaMargins": 0.35,
        "profitMargins": 0.25,
        "fiftyTwoWeekLow": 150.0,
        "fiftyTwoWeekHigh": 250.0,
        "fiftyDayAverage": 195.0,
        "twoHundredDayAverage": 185.0,
        "sharesOutstanding": 15000000000,
        "floatShares": 14000000000,
        "heldPercentInsiders": 0.02,
        "heldPercentInstitutions": 0.70,
        "volume": 1000000,
        "averageVolume10days": 1100000,
        "averageDailyVolume10Day": 1100000,
        "bid": 199.5,
        "ask": 200.5,
        "bidSize": 100,
        "askSize": 100,
    }

    if symbol.upper() == "AAPL":
        base_info.update(
            {
                "longName": "Apple Inc.",
                "shortName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "website": "https://www.apple.com",
                "currentPrice": 201.0,
                "marketCap": 3010457239552,
            }
        )
    elif symbol.upper() == "GOOGL":
        base_info.update(
            {
                "longName": "Alphabet Inc.",
                "shortName": "Alphabet Inc.",
                "sector": "Communication Services",
                "industry": "Internet Content & Information",
                "website": "https://www.google.com",
                "currentPrice": 180.0,
                "marketCap": 2200000000000,
            }
        )
    elif symbol.upper() == "MSFT":
        base_info.update(
            {
                "longName": "Microsoft Corporation",
                "shortName": "Microsoft Corporation",
                "sector": "Technology",
                "industry": "Software—Infrastructure",
                "website": "https://www.microsoft.com",
                "currentPrice": 420.0,
                "marketCap": 3100000000000,
            }
        )

    return base_info


def get_mock_history_df(symbol: str = "AAPL") -> pd.DataFrame:
    """Returns a mock pandas DataFrame for yfinance.Ticker(symbol).history()"""
    # Create realistic historical data
    dates = pd.date_range(start="2023-01-01", end="2023-01-05", freq="D")

    history_data = {
        "Open": [195.0, 196.0, 197.0, 198.0, 199.0],
        "High": [197.0, 198.0, 199.0, 200.0, 201.0],
        "Low": [194.0, 195.0, 196.0, 197.0, 198.0],
        "Close": [196.0, 197.0, 198.0, 199.0, 200.0],
        "Volume": [50000000, 51000000, 52000000, 53000000, 54000000],
    }

    df = pd.DataFrame(history_data, index=dates)
    df.index.name = "Date"
    return df


@pytest.fixture
def mock_yfinance(mocker):
    """
    Mock the yfinance library to match its actual API structure.
    This mock handles both .info (dict) and .history() (DataFrame) calls.
    """
    # Mock the Ticker class constructor
    mock_ticker_constructor = mocker.patch("yfinance.Ticker")

    # Create a mock instance that will be returned by the constructor
    mock_ticker_instance = MagicMock()

    def ticker_side_effect(ticker_symbol, session=None):
        """Side effect function to handle different ticker symbols"""

        # Handle invalid tickers
        if ticker_symbol.upper() == "INVALID":
            # Create an instance that will raise an exception when .info is accessed
            invalid_instance = MagicMock()
            invalid_instance.info = {}  # yfinance returns empty dict for invalid tickers
            return invalid_instance

        # For valid tickers, get the mock data
        info_data = get_mock_ticker_info(ticker_symbol)
        history_data = get_mock_history_df(ticker_symbol)

        # Configure the mock instance
        mock_ticker_instance.info = info_data
        mock_ticker_instance.history.return_value = history_data

        return mock_ticker_instance

    # Set up the side effect
    mock_ticker_constructor.side_effect = ticker_side_effect

    # Also mock yfinance.download if needed
    mock_download = mocker.patch("yfinance.download")
    mock_download.return_value = get_mock_history_df()

    return {
        "ticker_constructor": mock_ticker_constructor,
        "ticker_instance": mock_ticker_instance,
        "download": mock_download,
    }
