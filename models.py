from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    BigInteger,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from fastapi_users.db import SQLAlchemyBaseUserTable


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    # username = Column(String(length=20), unique=True, nullable=False)
    # Relatonships for user-specific endpoints
    watchlist_entries = relationship(
        "WatchlistEntry", back_populates="user", cascade="all, delete-orphan"
    )


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, index=True, nullable=False)
    direction = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unitCost = Column(Float, nullable=False)
    createdAt = Column(BigInteger, index=True)

    user = relationship("User", back_populates="watchlist_entries")
    # For unique tickers
    # __table_args__ = (UniqueConstraint("user_id", "ticker", name="_user_ticker_uc"),)


class TickerEntry(Base):
    __tablename__ = "ticker_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(BigInteger, index=True)
    close = Column(Float)
    volume = Column(Integer)


class Intraday(Base):
    __tablename__ = "intraday_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(BigInteger, index=True)
    close = Column(Float)


class Intraweek(Base):
    __tablename__ = "intraweek_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(BigInteger, index=True)
    close = Column(Float)


class TickerInfo(Base):
    __tablename__ = "ticker_info"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    exchangeTimezoneName = Column(String)


class QuarterlyMetrics(Base):
    __tablename__ = "quarterly_metrics"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    quarterEndDate = Column(BigInteger, index=True)

    revenue = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    netIncome = Column(Float, nullable=True)
    totalAssets = Column(Float, nullable=True)
    totalLiabilities = Column(Float, nullable=True)
    shareholderEquity = Column(Float, nullable=True)
    longTermDebt = Column(Float, nullable=True)
    cashAndEquivalents = Column(Float, nullable=True)
    operatingCashFlow = Column(Float, nullable=True)
    freeCashFlow = Column(Float, nullable=True)
    grossMargin = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)
    debtToEquity = Column(Float, nullable=True)


class AnnualMetrics(Base):
    __tablename__ = "annual_metrics"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    yearEndDate = Column(BigInteger, index=True)

    revenue = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    netIncome = Column(Float, nullable=True)
    totalAssets = Column(Float, nullable=True)
    totalLiabilities = Column(Float, nullable=True)
    shareholderEquity = Column(Float, nullable=True)
    longTermDebt = Column(Float, nullable=True)
    cashAndEquivalents = Column(Float, nullable=True)
    operatingCashFlow = Column(Float, nullable=True)
    freeCashFlow = Column(Float, nullable=True)
    grossMargin = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)
    debtToEquity = Column(Float, nullable=True)
