import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from auth import fastapi_users, cookie_auth_backend
from schemas import UserCreate, UserRead, UserUpdate
from routers import ticker, valuation, watchlist, forex, backtester, user

app = FastAPI(
    title="EquiSight Backend API",
    description="Financial analysis and backtesting API",
    version="1.0.0",
)

allowed_origins = [
    "http://localhost:5173",
]

if os.getenv("ENVIRONMENT") == "development":
    allowed_origins.append("http://localhost:*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Master API Router
api_router = APIRouter(prefix="/api")

# Auth routes
api_router.include_router(
    fastapi_users.get_auth_router(cookie_auth_backend),
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)

api_router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/api/")
async def root():
    return {"message": "Equisight Home Page!"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


api_router.include_router(ticker.router)
api_router.include_router(watchlist.router)
api_router.include_router(forex.router)
api_router.include_router(valuation.router)
api_router.include_router(backtester.router)
api_router.include_router(user.router)

app.include_router(api_router)
