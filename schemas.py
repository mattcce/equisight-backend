from pydantic import BaseModel
from typing import Optional


class TickerInfo(BaseModel):
    symbol: str
    currentPrice: Optional[float]
    marketCap: Optional[int]
    sector: Optional[str]
    industry: Optional[str]
    longBusinessSummary: Optional[str]
