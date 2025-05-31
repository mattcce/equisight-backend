from fastapi import FastAPI, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import schemas
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import TickerEntry
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


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
async def info(ticker):
    info = yf.Ticker(ticker).info
    filtered_info = schemas.TickerInfo(**info)

    return filtered_info


# Usage: /history?start=YYYY-MM-DD&end=YYYY-MM-DD (Default to 1mo from current date)
@app.api_route("/ticker/{ticker}/history", methods=["GET", "POST"])
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
    start_date = int(
        datetime.strptime(start, "%Y-%m-%d")
        .replace(tzinfo=ZoneInfo("America/New_York"))
        .timestamp()
    )
    end_date = int(
        datetime.strptime(end, "%Y-%m-%d")
        .replace(tzinfo=ZoneInfo("America/New_York"))
        .timestamp()
    )

    # 1. Query for existing data in the requested range
    cached_entries = (
        db.query(TickerEntry)
        .filter(
            TickerEntry.ticker == ticker,
            TickerEntry.date >= start_date,
            TickerEntry.date <= end_date,
        )
        .order_by(TickerEntry.date.desc())
        .all()
    )

    # 2. Check if we have all dates in the requested range
    cached_dates = set(e.date for e in cached_entries)
    yf_dates = (
        yf.Ticker(ticker)
        .history(start=start_date, end=end_date + 86400)
        .index.astype(np.int64)
        // 10**9
    )

    trading_days = set(yf_dates)
    missing_dates = sorted(trading_days - cached_dates)

    if not missing_dates:
        # All data is cached, return it
        result = [
            {
                "ticker": e.ticker,
                "date": e.date,
                "close": e.close,
                "volume": e.volume,
            }
            for e in cached_entries
        ]
        print("success")
        result = {"history": result}
        return JSONResponse(content=result)

    # 3. Fetch only missing data from yfinance
    fetch_start = missing_dates[0]
    fetch_end = missing_dates[-1]
    df = yf.Ticker(ticker).history(start=fetch_start, end=fetch_end + 86400)
    df = df.reset_index()

    # 4. Store new data in DB
    for _, row in df.iterrows():
        row_date = (
            int(row["Date"].timestamp())
            if hasattr(row["Date"], "date")
            else row["Date"]
        )
        if row_date in missing_dates:
            exists = (
                db.query(TickerEntry).filter_by(ticker=ticker, date=row_date).first()
            )
            if not exists:
                db_entry = TickerEntry(
                    ticker=ticker,
                    date=row_date,
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
            TickerEntry.date >= start_date,
            TickerEntry.date <= end_date,
        )
        .order_by(TickerEntry.date.desc())
        .all()
    )
    result = [
        {
            "ticker": e.ticker,
            "date": e.date,
            "close": e.close,
            "volume": e.volume,
        }
        for e in all_entries
    ]
    result = {"history": result}
    return JSONResponse(content=result)


# Usage: /news?count=INT (default to 10)
@app.get("/ticker/{ticker}/news")
async def news(ticker: str, count: int = Query(10, description="Number of articles")):
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
