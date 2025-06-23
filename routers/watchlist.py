from fastapi import APIRouter, Depends, HTTPException
import yfinance as yf
import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_async_session
from datetime import datetime
from models import User, WatchlistEntry
from auth import current_active_user
from collections import defaultdict

SYSTEM_WATCH_DIRECTION = "SYSTEM_WATCH"
SYSTEM_WATCH_QUANTITY = -1
SYSTEM_WATCH_UNITCOST = -1


router = APIRouter(prefix="/users/me/watchlist", tags=["watchlist"])


@router.get(
    "",
    response_model=schemas.UserWatchlistResponse,
)
async def get_user_watchlist(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    stmt = select(WatchlistEntry).where(WatchlistEntry.user_id == current_user.id)
    result = await db.execute(stmt)
    user_entries = result.scalars().all()

    grouped_watchlist = defaultdict(list)

    all_watched_tickers = set(entry.ticker for entry in user_entries)
    for ticker_symbol in all_watched_tickers:
        grouped_watchlist[ticker_symbol] = []

    for entry in user_entries:
        if entry.direction != SYSTEM_WATCH_DIRECTION:
            position = schemas.PositionOutputSchema(
                direction=entry.direction,
                quantity=entry.quantity,
                unitCost=entry.unitCost,
                createdAt=entry.createdAt,
            )
            grouped_watchlist[entry.ticker].append(position)
    return schemas.UserWatchlistResponse(
        identifier=current_user.email,
        watchlist=dict(grouped_watchlist),
    )


@router.delete("/{ticker_symbol}", status_code=204)
async def remove_ticker_from_watchlist(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker_upper = ticker_symbol.upper()

    check_stmt = (
        select(WatchlistEntry)
        .where(
            (WatchlistEntry.user_id == current_user.id)
            & (WatchlistEntry.ticker == ticker_upper)
        )
        .limit(1)
    )
    check_result = await db.execute(check_stmt)
    if not check_result.scalars().first():
        raise HTTPException(
            status_code=404, detail=f"Ticker {ticker_upper} not found in watchlist"
        )

    delete_all_stmt = delete(WatchlistEntry).where(
        (WatchlistEntry.user_id == current_user.id)
        & (WatchlistEntry.ticker == ticker_upper)
    )

    await db.execute(delete_all_stmt)
    await db.commit()


@router.get(
    "/{ticker_symbol}",
    response_model=schemas.UserWatchlistTickerResponse,
)
async def get_ticker_watchlist(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker_upper = ticker_symbol.upper()

    stmt_check_watched = select(WatchlistEntry).where(
        (WatchlistEntry.user_id == current_user.id)
        & (WatchlistEntry.ticker == ticker_upper)
    )
    result_check_watched = await db.execute(stmt_check_watched)
    if not result_check_watched.scalars().first():
        raise HTTPException(
            status_code=400, detail=f"{ticker_upper} is not in your watchlist."
        )

    stmt_positions = select(WatchlistEntry).where(
        WatchlistEntry.user_id == current_user.id,
        WatchlistEntry.ticker == ticker_upper,
        WatchlistEntry.direction != SYSTEM_WATCH_DIRECTION,
    )
    result_positions = await db.execute(stmt_positions)
    ticker_items = result_positions.scalars().all()

    grouped_positions = []
    for entry in ticker_items:
        position = schemas.PositionOutputSchema(
            direction=entry.direction,
            quantity=entry.quantity,
            unitCost=entry.unitCost,
            createdAt=entry.createdAt,
        )
        grouped_positions.append(position)
    return schemas.UserWatchlistTickerResponse(positions=grouped_positions)


@router.put(
    "/{ticker_symbol}",
    response_model=schemas.UserWatchlistTickerResponse,
)
async def update_ticker_in_watchlist(
    ticker_symbol: str,
    request_body: schemas.UpdateTickerWatchlistRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker_upper = ticker_symbol.upper()

    delete_stmt = delete(WatchlistEntry).where(
        (WatchlistEntry.user_id == current_user.id)
        & (WatchlistEntry.ticker == ticker_upper)
    )

    await db.execute(delete_stmt)

    new_positions_db = []
    if request_body.positions:
        try:
            yf.Ticker(ticker_upper).info
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=400, detail=f"{ticker_upper} is not a valid ticker."
            )

        for position_data in request_body.positions:
            db_watchlist_entry = WatchlistEntry(
                user_id=current_user.id,
                ticker=ticker_upper,
                direction=position_data.direction,
                quantity=position_data.quantity,
                unitCost=position_data.unitCost,
                createdAt=int(datetime.now().timestamp()),
            )
            db.add(db_watchlist_entry)
            new_positions_db.append(db_watchlist_entry)
    else:
        try:
            yf.Ticker(ticker_upper).info
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=400, detail=f"{ticker_upper} is not a valid ticker."
            )
        placeholder_entry = WatchlistEntry(
            user_id=current_user.id,
            ticker=ticker_upper,
            direction=SYSTEM_WATCH_DIRECTION,
            quantity=SYSTEM_WATCH_QUANTITY,
            unitCost=SYSTEM_WATCH_UNITCOST,
            createdAt=int(datetime.now().timestamp()),
        )
        db.add(placeholder_entry)

    await db.commit()

    response_positions = []
    for entry in new_positions_db:
        await db.refresh(entry)
        response_positions.append(schemas.PositionOutputSchema.model_validate(entry))

    return schemas.UserWatchlistTickerResponse(positions=response_positions)


@router.post(
    "/{ticker_symbol}",
    response_model=schemas.WatchlistEntryTicker,
)
async def add_ticker_to_watchlist(
    ticker_symbol: str,
    watchlist_item_create: schemas.WatchlistEntryCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker_upper = ticker_symbol.upper()
    direction = watchlist_item_create.direction
    quantity = watchlist_item_create.quantity
    unitCost = watchlist_item_create.unitCost
    createdAt = int(datetime.now().timestamp())

    try:
        yf.Ticker(ticker_upper).info
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"{ticker_upper} is not a valid ticker"
        )

    db_watchlist_entry = WatchlistEntry(
        user_id=current_user.id,
        ticker=ticker_upper,
        direction=direction,
        quantity=quantity,
        unitCost=unitCost,
        createdAt=createdAt,
    )
    db.add(db_watchlist_entry)
    await db.commit()
    await db.refresh(db_watchlist_entry)
    return db_watchlist_entry
