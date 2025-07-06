from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

import schemas
from database import get_async_session
from auth import current_active_user
from models import User, TickerFairValue

from analysis.fundamental.dcf import fair_value
from analysis.relative.reversedcf import reverse_dcf

router = APIRouter(prefix="/analysis", tags=["fundamental"])


@router.get("/{ticker}/fairvalue")
async def fairValue(
    ticker: str,
    high: int = Query(5, description="High Growth Period"),
    stable: int = Query(5, description="Stable Growth Period"),
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()

    stmt = select(TickerFairValue).where(
        TickerFairValue.ticker == ticker,
        TickerFairValue.highGrowthPeriod == high,
        TickerFairValue.stableGrowthPeriod == stable,
    )
    result = await db.execute(stmt)
    present = result.scalars().first()

    if present:
        result = schemas.FundamentalOutput(
            symbol=present.ticker,
            costOfEquity=present.costOfEquity,
            costOfDebt=present.costOfDebt,
            wacc=present.wacc,
            roic=present.roic,
            expectedGrowthRate=present.expectedGrowthRate,
            fairValue=present.fairValue,
        )

        # print("success")
        return result

    # For validity of ticker
    try:
        output = fair_value(ticker, high, stable)
        filtered_output = schemas.FundamentalOutput(
            symbol=output["Ticker"],
            costOfEquity=output["Cost of Equity"],
            costOfDebt=output["Cost of Debt"],
            wacc=output["WACC"],
            roic=output["ROIC"],
            expectedGrowthRate=output["Expected Growth Rate"],
            fairValue=output["Fair Value"],
        )

        db_entry = TickerFairValue(
            ticker=output["Ticker"],
            highGrowthPeriod=high,
            stableGrowthPeriod=stable,
            costOfEquity=output["Cost of Equity"],
            costOfDebt=output["Cost of Debt"],
            wacc=output["WACC"],
            roic=output["ROIC"],
            expectedGrowthRate=output["Expected Growth Rate"],
            fairValue=output["Fair Value"],
        )
        db.add(db_entry)

        await db.commit()

        # print("new entry")
        return filtered_output

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not enough information for ticker: {ticker}",
        )


# Cannot cache data because implied rate is dependent on market price
@router.get("/{ticker}/grahamvalue")
async def grahamValue(
    ticker: str,
    terminal: float = Query(5, description="Terminal Growth Rate"),
    growth: int = Query(10, description="Growth Period"),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()
    terminal_rate = terminal / 100

    try:
        output = reverse_dcf(ticker, terminal_rate, growth)
        filtered_output = schemas.ImpliedGrowthOutput(
            symbol=output["Ticker"],
            wacc=output["WACC"] * 100,
            impliedGrowthRate=output["Implied Growth"] * 100,
            grahamValue=output["Graham Value"],
        )

        return filtered_output
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid ticker: {ticker}"
        )
