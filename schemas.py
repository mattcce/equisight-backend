from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Literal, List
from fastapi_users import schemas
from datetime import date


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    direction: Literal["BUY", "SELL"]
    quantity: float
    unitCost: float
    createdAt: int


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


class FundamentalOutput(BaseModel):
    symbol: str
    costOfEquity: float
    costOfDebt: float
    wacc: float
    roic: float
    expectedGrowthRate: float
    fairValue: float


class ImpliedGrowthOutput(BaseModel):
    symbol: str
    wacc: float
    impliedGrowthRate: float
    grahamValue: float


class BacktestRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL, GOOGL)")
    purchaseDate: date = Field(..., description="Historical purchase date (YYYY-MM-DD)")
    investmentType: Literal["lumpSum", "dca", "lumpSumDca"] = Field(
        ..., description="Investment type: lumpSum or dca"
    )
    lumpSumAmount: Optional[float] = Field(
        default=None,
        gt=0,
        description="Lump sum investment amount (required if investment_type is lump_sum)",
    )
    dcaAmount: Optional[float] = Field(
        default=None,
        gt=0,
        description="Amount to invest per DCA period (required if investment_type is dca)",
    )
    dcaFrequency: Optional[Literal["weekly", "monthly", "yearly"]] = Field(
        default=None, description="DCA frequency (required if investment_type is dca)"
    )

    @field_validator("purchaseDate")
    def validate_purchase_date(cls, v):
        if v >= date.today():
            raise ValueError("Purchase date must be in the past")
        return v

    @field_validator("lumpSumAmount")
    def validate_lump_sum_amount(cls, v, values):
        if values.get("investment_type") in ["lumpSum", "lumpSumDca"] and not v:
            raise ValueError(
                "Lump sum amount is required when investment_type is lumpSum"
            )
        return v

    @field_validator("dcaAmount")
    def validate_dca_amount(cls, v, values):
        if values.get("investment_type") == "dca" and not v:
            raise ValueError("DCA amount is required when investment_type is dca")
        return v

    @field_validator("dcaFrequency")
    def validate_dca_frequency(cls, v, values):
        if values.get("investment_type") == "dca" and not v:
            raise ValueError("DCA frequency is required when investment_type is dca")
        return v


class BacktestResponse(BaseModel):
    ticker: str
    currency: str
    purchaseDate: date
    sellDate: date
    investmentType: str
    lumpSumAmount: Optional[float]
    dcaAmount: Optional[float]
    dcaFrequency: Optional[str]
    totalInvested: float
    totalSharesPurchased: float
    averagePurchasePrice: float
    sellPrice: float
    sellValue: float
    totalReturn: float
    totalReturnPercentage: float
    annualizedReturn: float
    daysHeld: int
    numberOfPurchases: int
    timestamp: int


class UserPreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str


class UserPreferencesUpdate(BaseModel):
    currency: str = Field(
        ...,
        # min_length=3,
        # max_length=3,
        description="Currency code (e.g. SGD, USD, EUR)",
    )

    class Config:
        json_schema_extra = {"example": {"currency": "USD"}}
