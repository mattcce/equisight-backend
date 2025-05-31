from pydantic import BaseModel
from typing import Optional


class TickerInfo(BaseModel):
    symbol: str
    fullExchangeName: Optional[str]
    shortName: Optional[str]
    regularMarketPrice: Optional[float]
    marketState: Optional[str]
    region: Optional[str]
    currency: Optional[str]
    previousClose: Optional[float]
    # marketCap: Optional[int] = None
    # sector: Optional[str] = None
    # industry: Optional[str] = None
    # longBusinessSummary: Optional[str]
