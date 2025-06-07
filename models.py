from sqlalchemy import Column, Integer, String, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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
