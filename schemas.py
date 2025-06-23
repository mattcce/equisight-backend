from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    # username: str
    pass


class UserCreate(schemas.BaseUserCreate):
    # username: str
    pass


class UserUpdate(schemas.BaseUserUpdate):
    # username: Optional[str] = None
    pass


class WatchlistTickersResponse(BaseModel):
    identifier: str
    tickers: List[str]


class PositionCreate(BaseModel):
    direction: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    unitCost: float = Field(gt=0)


class PositionOutputSchema(BaseModel):
    id: int
    direction: Literal["BUY", "SELL"]
    quantity: float
    unitCost: float
    createdAt: int

    class Config:
        from_attributes = True


class TickerPositionsResponse(BaseModel):
    ticker: str
    positions: List[PositionOutputSchema]


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
