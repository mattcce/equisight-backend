from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TickerEntry(Base):
    __tablename__ = "ticker_entries"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(Integer, index=True)
    close = Column(Float)
    volume = Column(Integer)
