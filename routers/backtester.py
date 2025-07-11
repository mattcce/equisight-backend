from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, date
from typing import Optional, Literal, Dict
import yfinance as yf
import pandas as pd
import numpy as np
import asyncio

from database import get_async_session
from auth import current_active_user
from models import User, TickerEntry, TickerInfo
import schemas

router = APIRouter(prefix="/backtester", tags=["backtester"])


async def get_historical_data(
    ticker: str, start_date: date, end_date: date, db: Session
) -> Dict[str, float]:
    ticker = ticker.upper()

    # Get timezone info for the ticker
    info_stmt = select(TickerInfo).filter(TickerInfo.ticker == ticker)
    info_result = await db.execute(info_stmt)
    ticker_info = info_result.scalars().first()

    if not ticker_info:
        # Get ticker info from yfinance and store it
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        ticker_info = TickerInfo(
            ticker=ticker, exchangeTimezoneName=info.get("exchangeTimezoneName")
        )
        db.add(ticker_info)
        await db.commit()

    # Convert dates to timestamps
    start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

    # 1. Query for existing data in the requested range
    cached_stmt = (
        select(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.timestamp >= start_timestamp,
            TickerEntry.timestamp <= end_timestamp,
        )
        .order_by(TickerEntry.timestamp.asc())
    )

    cached_result = await db.execute(cached_stmt)
    cached_entries = cached_result.scalars().all()

    # 2. Check if we have all dates in the requested range
    cached_dates = {e.timestamp for e in cached_entries}

    def get_yf_history_timestamps():
        hist = yf.Ticker(ticker).history(
            start=start_date, end=end_date + pd.Timedelta(days=1)
        )
        return hist.index.astype(np.int64) // 10**9

    yf_timestamps = await asyncio.to_thread(get_yf_history_timestamps)
    trading_days = set(yf_timestamps)
    missing_timestamps = sorted(trading_days - cached_dates)

    if missing_timestamps:
        # 3. Fetch missing data from yfinance
        fetch_start = datetime.fromtimestamp(missing_timestamps[0]).date()
        fetch_end = datetime.fromtimestamp(missing_timestamps[-1]).date()

        def get_missing_data():
            df = yf.Ticker(ticker).history(
                start=fetch_start, end=fetch_end + pd.Timedelta(days=1)
            )
            return df.reset_index()

        df = await asyncio.to_thread(get_missing_data)

        # 4. Store new data in DB
        new_entries_count = 0
        for _, row in df.iterrows():
            row_timestamp = int(row["Date"].timestamp())
            if row_timestamp in missing_timestamps:
                # Check if entry already exists
                exists_stmt = select(TickerEntry).filter_by(
                    ticker=ticker, timestamp=row_timestamp
                )
                exists_result = await db.execute(exists_stmt)
                if not exists_result.scalars().first():
                    db_entry = TickerEntry(
                        ticker=ticker,
                        timestamp=row_timestamp,
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    )
                    db.add(db_entry)
                    new_entries_count += 1

        await db.commit()

        # 5. Re-query to get all data including newly stored
        all_entries_result = await db.execute(cached_stmt)
        all_entries = all_entries_result.scalars().all()
    else:
        all_entries = cached_entries

    # Convert to dictionary mapping timestamps to close prices
    result_dict = {entry.timestamp: entry.close for entry in all_entries}
    return result_dict


@router.get("/calculate-return/{ticker}")
async def calculate_backtest_return_get(
    ticker: str,
    purchaseDate: date = Query(
        ..., description="Historical purchase date (YYYY-MM-DD)"
    ),
    sellDate: date = Query(..., description="Sell date (YYYY-MM-DD)"),
    investmentType: Literal["lumpSum", "dca"] = Query(
        ..., description="Investment type: lumpSum or dca"
    ),
    lumpSumAmount: Optional[float] = Query(
        default=1000,
        gt=0,
        description="Lump sum investment amount (required if investmentType is lumpSum)",
    ),
    dcaAmount: Optional[float] = Query(
        default=100,
        gt=0,
        description="Amount to invest per DCA period (required if investmentType is dca)",
    ),
    dcaFrequency: Optional[Literal["weekly", "monthly", "yearly"]] = Query(
        default=None, description="DCA frequency (required if investmentType is dca)"
    ),
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    try:
        # Validate input parameters
        if investmentType == "lumpSum" and not lumpSumAmount:
            raise HTTPException(
                status_code=400,
                detail="lumpSumAmount is required when investmentType is lumpSum",
            )

        if investmentType == "dca" and (not dcaAmount or not dcaFrequency):
            raise HTTPException(
                status_code=400,
                detail="dcaAmount and dcaFrequency are required when investmentType is dca",
            )

        # Validate that sellDate is not in the future
        if sellDate > date.today():
            raise HTTPException(
                status_code=400,
                detail=f"Sell date ({sellDate}) cannot be in the future. Current date is {date.today()}",
            )

        # Validate that sellDate is not before purchaseDate
        if sellDate < purchaseDate:
            raise HTTPException(
                status_code=400,
                detail=f"Sell date ({sellDate}) cannot be before purchase date ({purchaseDate})",
            )

        # Get historical data from database/yfinance
        historical_data = await get_historical_data(ticker, purchaseDate, sellDate, db)

        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker} from {purchaseDate} to today",
            )

        # Sort timestamps
        sorted_timestamps = sorted(historical_data.keys())

        # Get current price (most recent)
        current_price = historical_data[sorted_timestamps[-1]]
        total_shares = 0
        total_invested = 0
        number_of_purchases = 0

        if investmentType == "dca":
            # Dollar Cost Averaging
            purchase_dates = []

            # Generate purchase dates based on frequency
            current_date = purchaseDate
            end_date_obj = sellDate

            while current_date <= end_date_obj:
                purchase_dates.append(current_date)

                if dcaFrequency == "weekly":
                    current_date += pd.DateOffset(weeks=1)
                elif dcaFrequency == "monthly":
                    current_date += pd.DateOffset(months=1)
                elif dcaFrequency == "yearly":
                    current_date += pd.DateOffset(years=1)

                current_date = current_date.date()

            # Execute DCA strategy
            for purchase_date_item in purchase_dates:
                # Find the closest available trading day
                purchase_timestamp = int(
                    datetime.combine(
                        purchase_date_item, datetime.min.time()
                    ).timestamp()
                )

                # Find the nearest available price within 7 days
                closest_timestamp = None
                min_diff = float("inf")

                for ts in sorted_timestamps:
                    diff = abs(ts - purchase_timestamp)
                    if diff <= 7 * 24 * 60 * 60:  # Within 7 days
                        if diff < min_diff:
                            min_diff = diff
                            closest_timestamp = ts

                if closest_timestamp:
                    purchase_price = historical_data[closest_timestamp]
                    shares_bought = dcaAmount / purchase_price

                    total_shares += shares_bought
                    total_invested += dcaAmount
                    number_of_purchases += 1

            if number_of_purchases == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No valid purchase dates found for DCA strategy",
                )

            average_purchase_price = total_invested / total_shares

        else:
            # Lump sum investment
            purchase_timestamp = int(
                datetime.combine(purchaseDate, datetime.min.time()).timestamp()
            )

            # Find the closest available price
            closest_timestamp = None
            min_diff = float("inf")

            for ts in sorted_timestamps:
                diff = abs(ts - purchase_timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_timestamp = ts

            if not closest_timestamp:
                raise HTTPException(
                    status_code=400,
                    detail=f"No price data available for {ticker} near {purchaseDate}",
                )

            purchase_price = historical_data[closest_timestamp]
            total_shares = lumpSumAmount / purchase_price
            total_invested = lumpSumAmount
            average_purchase_price = purchase_price
            number_of_purchases = 1

        # Calculate current value and returns
        current_value = total_shares * current_price
        total_return = current_value - total_invested
        total_return_percentage = (total_return / total_invested) * 100

        # Calculate days held and annualized return
        days_held = (sellDate - purchaseDate).days
        years_held = days_held / 365.25

        if years_held > 0:
            annualized_return = (
                (current_value / total_invested) ** (1 / years_held) - 1
            ) * 100
        else:
            annualized_return = 0

        return schemas.BacktestResponse(
            ticker=ticker.upper(),
            currency=yf.Ticker(ticker).info.get("currency").upper(),
            purchaseDate=purchaseDate,
            sellDate=sellDate,
            investmentType=investmentType,
            lumpSumAmount=lumpSumAmount,
            dcaAmount=dcaAmount,
            dcaFrequency=dcaFrequency,
            totalInvested=round(total_invested, 2),
            totalSharesPurchased=round(total_shares, 4),
            averagePurchasePrice=round(average_purchase_price, 2),
            sellPrice=round(current_price, 2),
            sellValue=round(current_value, 2),
            totalReturn=round(total_return, 2),
            totalReturnPercentage=round(total_return_percentage, 2),
            annualizedReturn=round(annualized_return, 2),
            daysHeld=days_held,
            numberOfPurchases=number_of_purchases,
            timestamp=int(datetime.now().timestamp()),
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500, detail=f"Error calculating backtest for {ticker}: {str(e)}"
        )
