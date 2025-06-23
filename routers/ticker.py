from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import yfinance as yf
import numpy as np
import exchange_calendars as xcals
import asyncio

import schemas
from database import get_async_session, get_db
from auth import current_active_user
from models import User, TickerInfo, TickerEntry, Intraday, Intraweek
from services import (
    get_and_store_quarterly_metrics,
    get_and_store_annual_metrics,
    getExchangeHours,
    getExchangeISO,
    getHoursWeek,
)

router = APIRouter(prefix="/ticker", tags=["ticker"])


@router.get("/{ticker}/info")
async def info(
    ticker: str,
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    info = yf.Ticker(ticker).info

    stmt = select(TickerInfo).filter(TickerInfo.ticker == ticker)
    result = await db.execute(stmt)
    exists = result.scalars().first()

    if not exists:
        # For caching of timezone info
        data = {"ticker": ticker, "exchangeTimezoneName": info["exchangeTimezoneName"]}
        db.add(TickerInfo(**data))
        db.commit()

    filtered_info = schemas.TickerInfo(**info)

    return filtered_info


# Usage: /history?start=YYYY-MM-DD&end=YYYY-MM-DD (Default to 1mo from current date)
@router.get("/{ticker}/history")
async def history(
    ticker: str,
    start: str = Query(
        (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
        description="Start date in YYYY-MM-DD",
    ),
    end: str = Query(
        datetime.today().strftime("%Y-%m-%d"), description="End date in YYYY-MM-DD"
    ),
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()

    stmt = select(TickerInfo).filter(TickerInfo.ticker == ticker)
    result = await db.execute(stmt)
    present = result.scalars().first()

    if present:
        tz = ZoneInfo(present.exchangeTimezoneName)
    else:
        info = yf.Ticker(ticker).info
        data = {"ticker": ticker, "exchangeTimezoneName": info["exchangeTimezoneName"]}
        db.add(TickerInfo(**data))
        db.commit()
        tz = ZoneInfo(info["exchangeTimezoneName"])

    start_date = int(
        datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=tz).timestamp()
    )
    end_date = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=tz).timestamp())

    # 1. Query for existing data in the requested range
    cached_stmt = (
        select(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.timestamp >= start_date,
            TickerEntry.timestamp <= end_date,
        )
        .order_by(TickerEntry.timestamp.desc())
    )

    cached_result = await db.execute(cached_stmt)
    cached_entries = cached_result.scalars().all()

    # 2. Check if we have all dates in the requested range
    cached_dates = {e.timestamp for e in cached_entries}

    def get_yf_history_timestamps():
        hist = yf.Ticker(ticker).history(start=start_date, end=end_date + 86400)
        return hist.index.astype(np.int64) // 10**9

    yf_timestamps = await asyncio.to_thread(get_yf_history_timestamps)

    trading_days = set(yf_timestamps)
    missing_timestamps = sorted(trading_days - cached_dates)

    if not missing_timestamps:
        # All data is cached, return it
        result = [
            {
                "ticker": e.ticker,
                "timestamp": e.timestamp,
                "close": e.close,
                "volume": e.volume,
            }
            for e in cached_entries
        ]
        print("success")
        result = {"history": result}
        return JSONResponse(content=result)

    # 3. Fetch only missing data from yfinance
    fetch_start = missing_timestamps[0]
    fetch_end = missing_timestamps[-1]

    def get_missing_data():
        df = yf.Ticker(ticker).history(start=fetch_start, end=fetch_end + 86400)
        return df.reset_index()

    df = await asyncio.to_thread(get_missing_data)

    # 4. Store new data in DB
    for _, row in df.iterrows():
        row_date = int(row["Date"].timestamp())
        if row_date in missing_timestamps:
            exists_stmt = select(TickerEntry).filter_by(
                ticker=ticker, timestamp=row_date
            )
            exists_result = await db.execute(exists_stmt)
            if not exists_result.scalars().first():
                db_entry = TickerEntry(
                    ticker=ticker,
                    timestamp=row_date,
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                db.add(db_entry)
    await db.commit()

    # 5. Return all data for the requested period
    all_entries_stmt = (
        select(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.timestamp >= start_date,
            TickerEntry.timestamp <= end_date,
        )
        .order_by(TickerEntry.timestamp.desc())
    )
    all_entries_result = await db.execute(all_entries_stmt)
    all_entries = all_entries_result.scalars().all()

    result = [
        {
            "ticker": e.ticker,
            "timestamp": e.timestamp,
            "close": e.close,
            "volume": e.volume,
        }
        for e in all_entries
    ]
    result = {"history": result}
    return JSONResponse(content=result)


@router.get("/{ticker}/intraday")
async def intraday(
    ticker: str,
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()

    info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)

    marketState = info["marketState"]
    tznStr = info["exchangeTimezoneName"]
    serverTimezone = "Asia/Singapore"
    now = datetime.now(ZoneInfo(serverTimezone))
    tz = ZoneInfo(tznStr)
    currentTime = now.astimezone(tz)
    dayStr = currentTime.strftime("%Y-%m-%d")
    exchangeISO = getExchangeISO(tznStr)
    exchangeHours = getExchangeHours(exchangeISO, dayStr)
    exchange = xcals.get_calendar(exchangeISO)

    # Check if Market is closed, if so return most recent intraday data
    if marketState != "REGULAR":
        # last trading day's hours
        lastClose = int(exchange.previous_close(currentTime).timestamp())
        lastOpen = int(exchange.previous_open(currentTime).timestamp())

        closedDb_stmt = (
            select(Intraday)
            .filter(Intraday.ticker == ticker, Intraday.timestamp >= lastOpen)
            .order_by(Intraday.timestamp.desc())
        )
        closedDb_res = await db.execute(closedDb_stmt)
        closedDb = closedDb_res.scalars().first()

        def get_history_data(start_time=None):
            if start_time:
                return (
                    yf.Ticker(ticker)
                    .history(start=start_time + 1, interval="1m")
                    .reset_index()
                )
            return yf.Ticker(ticker).history(period="1d", interval="1m").reset_index()

        df = await asyncio.to_thread(
            get_history_data, closedDb.timestamp if closedDb else None
        )

        for _, row in df.iterrows():
            row_date = int(row["Datetime"].timestamp())
            db_entry = Intraday(
                ticker=ticker, timestamp=row_date, close=float(row["Close"])
            )
            db.add(db_entry)
        await db.commit()

        all_entries_stmt = (
            select(Intraday)
            .filter(Intraday.ticker == ticker, Intraday.timestamp >= lastOpen)
            .order_by(Intraday.timestamp.desc())
        )
        all_entries_res = await db.execute(all_entries_stmt)
        all_entries = all_entries_res.scalars().all()

        result = [
            {"ticker": e.ticker, "timestamp": e.timestamp, "close": e.close}
            for e in all_entries
        ]
        return JSONResponse(
            content={
                "marketOpen": lastOpen,
                "marketClose": lastClose,
                "intraday": result,
            }
        )

    # Market is Open
    present_stmt = (
        select(Intraday)
        .filter(Intraday.ticker == ticker)
        .order_by(Intraday.timestamp.desc())
    )
    present_res = await db.execute(present_stmt)
    present = present_res.scalars().first()

    def get_open_market_history(latest_timestamp=None):
        if latest_timestamp and exchangeHours["openTimestamp"] <= latest_timestamp:
            return (
                yf.Ticker(ticker)
                .history(start=(latest_timestamp + 1), interval="1m")
                .reset_index()
            )
        return yf.Ticker(ticker).history(period="1d", interval="1m").reset_index()

    df = await asyncio.to_thread(
        get_open_market_history, present.timestamp if present else None
    )

    for _, row in df.iterrows():
        row_date = int(row["Datetime"].timestamp())
        db_entry = Intraday(
            ticker=ticker, timestamp=row_date, close=float(row["Close"])
        )
        db.add(db_entry)
    await db.commit()

    all_entries_stmt = (
        select(Intraday)
        .filter(
            Intraday.ticker == ticker,
            Intraday.timestamp >= exchangeHours["openTimestamp"],
        )
        .order_by(Intraday.timestamp.desc())
    )
    all_entries_res = await db.execute(all_entries_stmt)
    all_entries = all_entries_res.scalars().all()

    result = [
        {"ticker": e.ticker, "timestamp": e.timestamp, "close": e.close}
        for e in all_entries
    ]
    return JSONResponse(
        content={
            "marketOpen": exchangeHours["openTimestamp"],
            "marketClose": exchangeHours["closeTimestamp"],
            "intraday": result,
        }
    )


@router.get("/{ticker}/intraweek")
async def intraweek(
    ticker: str,
    db: Session = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()

    info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)

    marketState = info["marketState"]
    tznStr = info["exchangeTimezoneName"]
    tz = ZoneInfo(tznStr)
    now = datetime.now(tz)
    exchangeISO = getExchangeISO(tznStr)
    hoursDict = getHoursWeek(exchangeISO, now)

    oldestOpen = hoursDict["oldestOpen"]
    latestClose = hoursDict["latestClose"]

    # Check if Market is closed, if so return most recent intraweek data
    if marketState != "REGULAR":
        closedDb_stmt = (
            select(Intraweek)
            .filter(Intraweek.ticker == ticker, Intraweek.timestamp >= oldestOpen)
            .order_by(Intraweek.timestamp.desc())
        )
        closedDb_res = await db.execute(closedDb_stmt)
        closedDb = closedDb_res.scalars().first()

        # Define the synchronous yfinance call as a helper function
        def get_history_data(start_time=None):
            if start_time:
                return (
                    yf.Ticker(ticker)
                    .history(start=start_time + 3599, interval="1h")
                    .reset_index()
                )
            return yf.Ticker(ticker).history(period="5d", interval="1h").reset_index()

        # Run the yfinance call in a separate thread
        df = await asyncio.to_thread(
            get_history_data, closedDb.timestamp if closedDb else None
        )

        for _, row in df.iterrows():
            row_date = int(row["Datetime"].timestamp())
            db_entry = Intraweek(
                ticker=ticker, timestamp=row_date, close=float(row["Close"])
            )
            db.add(db_entry)
        await db.commit()

        # Fetch all entries for the week to return
        all_entries_stmt = (
            select(Intraweek)
            .filter(Intraweek.ticker == ticker, Intraweek.timestamp >= oldestOpen)
            .order_by(Intraweek.timestamp.desc())
        )
        all_entries_res = await db.execute(all_entries_stmt)
        all_entries = all_entries_res.scalars().all()

        result = [
            {"ticker": e.ticker, "timestamp": e.timestamp, "close": e.close}
            for e in all_entries
        ]
        return JSONResponse(
            content={
                "oldestOpen": oldestOpen,
                "latestClose": latestClose,
                "intraweek": result,
            }
        )

    # Market is Open
    present_stmt = (
        select(Intraweek)
        .filter(Intraweek.ticker == ticker)
        .order_by(Intraweek.timestamp.desc())
    )
    present_res = await db.execute(present_stmt)
    present = present_res.scalars().first()

    # Define the synchronous yfinance call as a helper function
    def get_open_market_history(latest_timestamp=None):
        if latest_timestamp and oldestOpen <= latest_timestamp:
            # Ensure no duplicates (threshold is 3599 for 1h interval)
            return (
                yf.Ticker(ticker)
                .history(start=(latest_timestamp + 3599), interval="1h")
                .reset_index()
            )
        return yf.Ticker(ticker).history(period="5d", interval="1h").reset_index()

    # Run the yfinance call in a separate thread
    df = await asyncio.to_thread(
        get_open_market_history, present.timestamp if present else None
    )

    for _, row in df.iterrows():
        row_date = int(row["Datetime"].timestamp())
        db_entry = Intraweek(
            ticker=ticker, timestamp=row_date, close=float(row["Close"])
        )
        db.add(db_entry)
    await db.commit()

    # Fetch all entries for the week to return
    all_entries_stmt = (
        select(Intraweek)
        .filter(Intraweek.ticker == ticker, Intraweek.timestamp >= oldestOpen)
        .order_by(Intraweek.timestamp.desc())
    )
    all_entries_res = await db.execute(all_entries_stmt)
    all_entries = all_entries_res.scalars().all()

    result = [
        {"ticker": e.ticker, "timestamp": e.timestamp, "close": e.close}
        for e in all_entries
    ]
    return JSONResponse(
        content={
            "oldestOpen": oldestOpen,
            "latestClose": latestClose,
            "intraweek": result,
        }
    )


@router.get("/{ticker}/quarterly-reports")
async def quarterly_reports(
    ticker: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()
    try:
        ticker_data_obj = yf.Ticker(ticker)
    except Exception as e:
        print(f"Error creating yfinance.Ticker object for {ticker}: {e}")
        return JSONResponse(
            content={
                "ticker": ticker,
                "error": "Invalid ticker symbol or yfinance error.",
            },
            status_code=400,
        )

    quarterly_reports_data = get_and_store_quarterly_metrics(
        ticker_data_obj, ticker, db
    )

    if not quarterly_reports_data:
        return JSONResponse(
            content={
                "ticker": ticker,
                "quarterlyReports": [],
                "message": "No quarterly metrics data found or processed.",
            },
            status_code=404,
        )

    return JSONResponse(
        content={"ticker": ticker, "quarterlyReports": quarterly_reports_data}
    )


@router.get("/{ticker}/annual-reports")
async def annual_reports(
    ticker: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()
    try:
        ticker_data_obj = yf.Ticker(ticker)
    except Exception as e:
        print(f"Error creating yfinance.Ticker object for {ticker}: {e}")
        return JSONResponse(
            content={
                "ticker": ticker,
                "error": "Invalid ticker symbol or yfinance error.",
            },
            status_code=400,
        )

    annual_reports_data = get_and_store_annual_metrics(ticker_data_obj, ticker, db)

    if not annual_reports_data:
        return JSONResponse(
            content={
                "ticker": ticker,
                "annualReports": [],
                "message": "No annual metrics data found or processed.",
            },
            status_code=404,
        )

    return JSONResponse(
        content={"ticker": ticker, "annualReports": annual_reports_data}
    )


# Usage: /news?count=INT (default to 10)
@router.get("/{ticker}/news")
async def news(
    ticker: str,
    count: int = Query(10, description="Number of articles"),
    user: User = Depends(current_active_user),
):
    ticker = ticker.upper()

    def get_news_sync():
        return yf.Ticker(ticker).get_news(count)

    # Fetch News & Press Releases (List of Dicts)
    news_list = await asyncio.to_thread(get_news_sync)

    # Process the data (Flatten the dictionary and obtain desired fields)
    def flatten(data):
        return {
            "id": data["content"]["id"],
            "title": data["content"]["title"],
            "providerDisplayName": data["content"]["provider"]["displayName"],
            "summary": data["content"]["summary"],
            "canonicalUrl": data["content"]["canonicalUrl"]["url"]
            if data["content"].get("canonicalUrl")
            else None,
            "thumbnailUrl": data["content"]["thumbnail"]["originalUrl"]
            if data["content"].get("thumbnail")
            else None,
            "timestamp": int(
                datetime.strptime(data["content"]["pubDate"], "%Y-%m-%dT%H:%M:%SZ")
                .replace(tzinfo=timezone.utc)
                .timestamp()
            ),
            "alternateThumbnailUrl": (
                data["content"]["thumbnail"]["resolutions"][1]["url"]
                if data["content"].get("thumbnail")
                and len(data["content"]["thumbnail"].get("resolutions", [])) > 1
                else None
            ),
            "clickThroughUrl": data["content"]["clickThroughUrl"]["url"]
            if data["content"].get("clickThroughUrl")
            else None,
        }

    result = []
    for news in news_list:
        result.append(flatten(news))

    result = {"ticker": ticker, "articles": result}

    return JSONResponse(content=result)
