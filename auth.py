from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from database import get_async_session

SECRET = "dev"


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")
        # TODO: Implement sending a password reset email

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification token requested for user {user.id} (Email: {user.email}).")
        print(f"Generated verficiation token: {token}")
        # TODO: Implement sending the verification email to user.email with token

    async def on_after_verify(self, user: User, request: Optional[Request] = None):
        print(
            f"User {user.id} (Email: {user.email} has successfully verified their email.)"
        )


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_name="equisightauth",
    cookie_max_age=3600,
<<<<<<< HEAD
    cookie_secure=False,  # for HTTP dev
=======
    cookie_secure=True,
    cookie_httponly=True,
>>>>>>> 0643791 (added authentication framework)
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [cookie_auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
optional_current_user = fastapi_users.current_user(optional=True)
