from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    username: str
    pass


class UserCreate(schemas.BaseUserCreate):
    username: str
    pass


class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None
    pass


class WatchlistEntryCreate(BaseModel):
    ticker: str
    direction: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    unitCost: float = Field(gt=0)


class WatchlistEntryTicker(BaseModel):
    direction: Literal["BUY", "SELL"]
    quantity: float
    unitCost: float
    createdAt: int

    class Config:
        from_attributes = True


class PositionOutputSchema(BaseModel):
    direction: Literal["BUY", "SELL"]
    quantity: float
    unitCost: float
    createdAt: int

    class Config:
        from_attributes = True


class PositionInputSchema(BaseModel):
    direction: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    unitCost: float = Field(gt=0)


class UpdateTickerWatchlistRequest(BaseModel):
    positions: List[PositionInputSchema]


class UserWatchlistResponse(BaseModel):
    identifier: str
    watchlist: Dict[str, List[PositionOutputSchema]]


class UserWatchlistTickerResponse(BaseModel):
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
