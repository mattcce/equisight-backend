from fastapi import FastAPI, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import schemas
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import TickerEntry, Intraday, TickerInfo
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from services import get_and_store_quarterly_metrics


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "Equisight Home Page!"}


# TODO: Change to /{ticker}/info
@app.get("/ticker/{ticker}/info")
async def info(ticker: str, db: Session = Depends(get_db)):
    info = yf.Ticker(ticker).info

    exists = db.query(TickerInfo).filter(TickerInfo.ticker == ticker).first()
    if not exists:
        # For caching of timezone info
        data = {"ticker": ticker, "exchangeTimezoneName": info["exchangeTimezoneName"]}
        db.add(TickerInfo(**data))
        db.commit()

    filtered_info = schemas.TickerInfo(**info)

    return filtered_info


# Usage: /history?start=YYYY-MM-DD&end=YYYY-MM-DD (Default to 1mo from current date)
@app.get("/ticker/{ticker}/history")
async def history(
    ticker: str,
    start: str = Query(
        (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
        description="Start date in YYYY-MM-DD",
    ),
    end: str = Query(
        datetime.today().strftime("%Y-%m-%d"), description="End date in YYYY-MM-DD"
    ),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper()
    present = db.query(TickerInfo).filter(TickerInfo.ticker == ticker).first()
    if present:
        tz = ZoneInfo(present.exchangeTimezoneName)
    else:
        # For caching of timezone info
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
    cached_entries = (
        db.query(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.timestamp >= start_date,
            TickerEntry.timestamp <= end_date,
        )
        .order_by(TickerEntry.timestamp.desc())
        .all()
    )

    # 2. Check if we have all dates in the requested range
    cached_dates = set(e.timestamp for e in cached_entries)
    yf_timestamp = (
        yf.Ticker(ticker)
        .history(start=start_date, end=end_date + 86400)
        .index.astype(np.int64)
        // 10**9
    )

    trading_days = set(yf_timestamp)
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
    df = yf.Ticker(ticker).history(start=fetch_start, end=fetch_end + 86400)
    df = df.reset_index()

    # 4. Store new data in DB
    for _, row in df.iterrows():
        row_date = (
            int(row["Date"].timestamp())
            if hasattr(row["Date"], "date")
            else row["Date"]
        )
        if row_date in missing_timestamps:
            exists = (
                db.query(TickerEntry)
                .filter_by(ticker=ticker, timestamp=row_date)
                .first()
            )
            if not exists:
                db_entry = TickerEntry(
                    ticker=ticker,
                    timestamp=row_date,
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                db.add(db_entry)
    db.commit()

    # 5. Return all data for the requested period
    all_entries = (
        db.query(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.timestamp >= start_date,
            TickerEntry.timestamp <= end_date,
        )
        .order_by(TickerEntry.timestamp.desc())
        .all()
    )
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


@app.get("/ticker/{ticker}/intraday")
async def intraday(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()

    # Check if Market is closed, if so return most recent intraday data
    info = yf.Ticker(ticker).info
    marketState = info["marketState"]
    tz = ZoneInfo(info["exchangeTimezoneName"])

    # Check if records are present
    present = (
        db.query(Intraday)
        .filter(Intraday.ticker == ticker)
        .order_by(Intraday.timestamp.desc())
        .first()
    )

    if marketState != "REGULAR":
        # if present:
        #     latestDate = yf.Ticker(ticker).history(period="1d").reset_index()['Date'][0]
        #     start = int(datetime.combine(latestDate.date(), time(0,0), tzinfo=tz).timestamp)
        #     end = int(datetime.combine(latestDate.date(), time(23,59), tzinfo=tz).timestamp)

        recentData = (
            yf.Ticker(ticker)
            .history(period="1d", interval="1m")
            .reset_index()[["Datetime", "Close"]]
        )
        result = {
            "intraday": [
                {
                    "timestamp": int(row["Datetime"].timestamp()),
                    "close": float(row["Close"]),
                }
                for _, row in recentData.iterrows()
            ]
        }
        return JSONResponse(content=result)

    # Market is Open
    # Current trading date timestamp
    dateTimestamp = int(
        datetime.combine(datetime.now(tz).date(), time.min, tzinfo=tz).timestamp()
    )

    if present:
        # Check last recorded timestamp
        latestTimestamp = present.timestamp
        # Timestamp belongs to current date -> return the difference
        if dateTimestamp < latestTimestamp:
            df = (
                yf.Ticker(ticker)
                .history(start=(latestTimestamp + 1), interval="1m")
                .reset_index()
            )

    # Timestamp belongs to previous trading day // No Data cached -> return full day data up to that point
    else:
        df = yf.Ticker(ticker).history(period="1d", interval="1m").reset_index()

    for _, row in df.iterrows():
        row_date = (
            int(row["Datetime"].timestamp())
            if hasattr(row["Datetime"], "date")
            else row["Datetime"]
        )

        db_entry = Intraday(
            ticker=ticker, timestamp=row_date, close=float(row["Close"])
        )
        db.add(db_entry)
    db.commit()

    # Return all data from current trading day
    all_entries = (
        db.query(Intraday)
        .filter(
            Intraday.ticker == ticker,
            Intraday.timestamp >= dateTimestamp,
        )
        .order_by(Intraday.timestamp.desc())
        .all()
    )

    result = [
        {"ticker": e.ticker, "timestamp": e.timestamp, "close": e.close}
        for e in all_entries
    ]
    result = {"intraday": result}
    return JSONResponse(content=result)


@app.get("/ticker/{ticker}/metrics")
async def metrics(ticker: str, db: Session = Depends(get_db)):
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


# Usage: /news?count=INT (default to 10)
@app.get("/ticker/{ticker}/news")
async def news(ticker: str, count: int = Query(10, description="Number of articles")):
    ticker = ticker.upper()

    # Fetch News & Press Releases (List of Dicts)
    news_list = yf.Ticker(ticker).get_news(count)

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
