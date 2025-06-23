from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from auth import current_active_user
from models import User
from services import getForex

router = APIRouter(tags=["forex"])


# Usage: /forex?fromCur=SGD&toCur=USD
@router.get("/forex")
async def forex(
    fromCur: str = Query("USD"),
    toCur: str = Query("SGD"),
    user: User = Depends(current_active_user),
):
    fromCur = fromCur.upper()
    toCur = toCur.upper()
    exchangeRate = getForex(fromCur, toCur)
    result = {"fromCurrency": fromCur, "toCurrency": toCur, "forexRate": exchangeRate}
    return JSONResponse(content=result)
