from fastapi import APIRouter, Depends, HTTPException, status
import yfinance as yf
import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_async_session
from datetime import datetime
from models import User, UserWatchlist, TickerPositions
from auth import current_active_user


router = APIRouter(prefix="/users/me/watchlist", tags=["watchlist"])


@router.get(
    "",
    response_model=schemas.WatchlistTickersResponse,
)
async def get_user_watchlist(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    stmt = select(UserWatchlist.ticker).where(UserWatchlist.user_id == current_user.id)
    result = await db.execute(stmt)
    tickers = result.scalars().all()
    return schemas.WatchlistTickersResponse(
        identifier=current_user.email, tickers=tickers
    )


@router.post(
    "/{ticker_symbol}",
    status_code=status.HTTP_201_CREATED,
)
async def add_ticker_to_watchlist(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt_check = select(UserWatchlist).where(
        UserWatchlist.user_id == current_user.id,
        UserWatchlist.ticker == ticker,
    )
    result_check = await db.execute(stmt_check)
    if result_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticker {ticker} already in watchlist.",
        )

    try:
        yf.Ticker(ticker).info
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{ticker} is not a valid ticker.",
        )

    new_watchlist_entry = UserWatchlist(user_id=current_user.id, ticker=ticker)
    db.add(new_watchlist_entry)
    await db.commit()
    return {"message": f"Ticker {ticker} added to watchlist."}


@router.delete(
    "/{ticker_symbol}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_ticker_from_watchlist(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    # Delete all positions associated with ticker for the user
    delete_positions_stmt = delete(TickerPositions).where(
        (TickerPositions.user_id == current_user.id)
        & (TickerPositions.ticker == ticker)
    )
    await db.execute(delete_positions_stmt)

    delete_watchlist_stmt = delete(UserWatchlist).where(
        (UserWatchlist.user_id == current_user.id) & (UserWatchlist.ticker == ticker)
    )
    result = await db.execute(delete_watchlist_stmt)

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found in watchlist.",
        )

    await db.commit()


@router.get(
    "/{ticker_symbol}",
    response_model=schemas.TickerPositionsResponse,
)
async def get_ticker_from_watchlist(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt_check = select(UserWatchlist).where(
        (UserWatchlist.user_id == current_user.id) & (UserWatchlist.ticker == ticker)
    )
    result_check = await db.execute(stmt_check)
    if not result_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found in watchlist.",
        )

    stmt_positions = select(TickerPositions).where(
        (TickerPositions.user_id == current_user.id)
        & (TickerPositions.ticker == ticker)
    )
    result_positions = await db.execute(stmt_positions)
    positions = result_positions.scalars().all()

    return schemas.TickerPositionsResponse(ticker=ticker, positions=positions)


@router.post(
    "/{ticker_symbol}/positions",
    response_model=schemas.PositionOutputSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_positions_to_ticker(
    ticker_symbol: str,
    position: schemas.PositionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt_check = select(UserWatchlist).where(
        UserWatchlist.user_id == current_user.id,
        UserWatchlist.ticker == ticker,
    )
    result_check = await db.execute(stmt_check)
    if not result_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found in watchlist.",
        )

    new_pos = TickerPositions(
        user_id=current_user.id,
        ticker=ticker,
        direction=position.direction,
        quantity=position.quantity,
        unitCost=position.unitCost,
        createdAt=int(datetime.now().timestamp()),
    )

    db.add(new_pos)
    await db.commit()

    await db.refresh(new_pos)
    return new_pos


@router.get(
    "/{ticker_symbol}/positions",
    response_model=schemas.TickerPositionsResponse,
)
async def get_positions_from_ticker(
    ticker_symbol: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt_check = select(UserWatchlist).where(
        (UserWatchlist.user_id == current_user.id) & (UserWatchlist.ticker == ticker)
    )
    result_check = await db.execute(stmt_check)
    if not result_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found in watchlist.",
        )

    stmt_positions = select(TickerPositions).where(
        (TickerPositions.user_id == current_user.id)
        & (TickerPositions.ticker == ticker)
    )
    result_positions = await db.execute(stmt_positions)
    positions = result_positions.scalars().all()

    return schemas.TickerPositionsResponse(ticker=ticker, positions=positions)


@router.delete(
    "/{ticker_symbol}/positions/{positions_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ticker_position(
    ticker_symbol: str,
    position_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()
    stmt = delete(TickerPositions).where(
        TickerPositions.id == position_id,
        TickerPositions.user_id == current_user.id,
        TickerPositions.ticker == ticker,
    )
    result = await db.execute(stmt)

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Position not found."
        )

    await db.commit()


@router.put(
    "/{ticker_symbol}/positions/{positions_id}",
    response_model=schemas.PositionOutputSchema,
)
async def update_ticker_position(
    ticker_symbol: str,
    position_id: int,
    position_data: schemas.PositionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt = select(TickerPositions).where(
        TickerPositions.id == position_id,
        TickerPositions.user_id == current_user.id,
        TickerPositions.ticker == ticker,
    )
    result = await db.execute(stmt)
    db_position = result.scalars().first()

    if not db_position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Position not found."
        )

    db_position.direction = position_data.direction
    db_position.quantity = position_data.quantity
    db_position.unitCost = position_data.unitCost

    await db.commit()
    await db.refresh(db_position)
    return db_position


@router.get(
    "/{ticker_symbol}/positions/{positions_id}",
    response_model=schemas.PositionOutputSchema,
)
async def get_position_from_id(
    ticker_symbol: str,
    positions_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    ticker = ticker_symbol.upper()

    stmt_check = select(UserWatchlist).where(
        (UserWatchlist.user_id == current_user.id) & (UserWatchlist.ticker == ticker)
    )
    result_check = await db.execute(stmt_check)
    if not result_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found in watchlist.",
        )

    stmt_positions = select(TickerPositions).where(
        (TickerPositions.user_id == current_user.id)
        & (TickerPositions.ticker == ticker)
        & (TickerPositions.id == positions_id)
    )
    result_positions = await db.execute(stmt_positions)
    position = result_positions.scalars().first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {positions_id} for {ticker} not found in watchlist.",
        )

    return schemas.PositionOutputSchema(
        id=position.id,
        direction=position.direction,
        quantity=position.quantity,
        unitCost=position.unitCost,
        createdAt=position.createdAt,
    )
