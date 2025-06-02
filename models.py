from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TickerEntry(Base):
    __tablename__ = "ticker_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(Integer, index=True)
    close = Column(Float)
    volume = Column(Integer)


class Intraday(Base):
    __tablename__ = "intraday_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(Integer, index=True)
    close = Column(Float)


class TickerInfo(Base):
    __tablename__ = "ticker_info"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    exchangeTimezoneName = Column(String)
