from pydantic import BaseModel
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


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
