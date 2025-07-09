from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_async_session
from models import User, UserPreferences
from auth import current_active_user
import schemas
from services import isCurrency

router = APIRouter(prefix="/users/me", tags=["user"])


@router.get(
    "/preferences",
    response_model=schemas.UserPreferencesRead,
)
async def get_user_preferences(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    stmt = select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    result = await db.execute(stmt)
    preferences = result.scalars().first()

    if not preferences:
        # Create default preferences if they don't exist
        preferences = UserPreferences(user_id=current_user.id, currency="USD")
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    return preferences


@router.put(
    "/preferences",
    response_model=schemas.UserPreferencesRead,
)
async def update_user_preferences(
    preferences_update: schemas.UserPreferencesUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    # Validate currency code format (3 uppercase letters)
    currency = preferences_update.currency.upper()
    if not isCurrency(currency):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Currency is invalid"
        )

    stmt = select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    result = await db.execute(stmt)
    preferences = result.scalars().first()

    if not preferences:
        # Create new preferences if they don't exist
        preferences = UserPreferences(user_id=current_user.id, currency=currency)
        db.add(preferences)
    else:
        # Update existing preferences
        preferences.currency = currency

    await db.commit()
    await db.refresh(preferences)

    return preferences
