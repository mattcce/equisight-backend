from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, exceptions
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from database import get_async_session
from schemas import UserCreate

from fastapi_users.password import PasswordHelper
import re

SECRET = "dev"


class CustomPasswordHelper(PasswordHelper):
    def validate(self, password: str):
        if len(password) < 4:
            raise exceptions.InvalidPasswordException(
                reason="Password must be at least 4 characters long."
            )
        if not re.search(r"[A-Z]", password):
            raise exceptions.InvalidPasswordException(
                reason="Password must contain at least one uppercase letter."
            )
        if not re.search(r"[a-z]", password):
            raise exceptions.InvalidPasswordException(
                reason="Password must contain at least one lowercase letter."
            )
        if not re.search(r"\d", password):
            raise exceptions.InvalidPasswordException(
                reason="Password must contain at least one digit."
            )
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise exceptions.InvalidPasswordException(
                reason="Password must contain at least one special character."
            )


class CustomSQLAlchemyUserDatabase(SQLAlchemyUserDatabase[User, int]):
    async def get_by_username(self, username: str) -> Optional[User]:
        statement = select(self.user_table).where(self.user_table.username == username)
        return await self._get_user(statement)


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
        print(
            f"Verification token requested for user {user.id} (Email: {user.email}, Username: {user.username})."
        )
        print(f"Generated verficiation token: {token}")
        # TODO: Implement sending the verification email to user.email with token

    async def on_after_verify(self, user: User, request: Optional[Request] = None):
        print(
            f"User {user.id} (Email: {user.email}, Username: {user.username} has successfully verified their email.)"
        )

    # Uses username to find the user
    async def authenticate(
        self, credentials: OAuth2PasswordRequestForm
    ) -> Optional[User]:
        if not isinstance(self.user_db, CustomSQLAlchemyUserDatabase):
            raise RuntimeError(
                "User DB not an instance of CustomSQLAlchemyUserDatabase"
            )

        user = await self.user_db.get_by_username(credentials.username)

        if user is None:
            return None

        if not user.is_active:
            return None

        verified, updated_password_hash = self.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )

        if not verified:
            return None

        if updated_password_hash is not None:
            await self.user_db.update(user, {"hashed password": updated_password_hash})

        return user

    async def validate_password(self, password: str, user_create: UserCreate):
        try:
            self.password_helper.validate(password)
        except exceptions.InvalidPasswordException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "REGISTER_INVALID_PASSWORD",
                    "reason": e.reason or "The provided password is not valid.",
                },
            )

    # Check if username already exists
    async def create(
        self,
        user_create: UserCreate,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        await self.validate_password(user_create.password, user_create)

        existing_user_by_email = await self.user_db.get_by_email(user_create.email)
        if existing_user_by_email is not None:
            raise exceptions.UserAlreadyExists()

        if not isinstance(self.user_db, CustomSQLAlchemyUserDatabase):
            raise RuntimeError(
                "User DB is not an instance of CustomSQLAlchemyUserDatabase"
            )
        existing_user_by_email = await self.user_db.get_by_username(
            user_create.username
        )
        if existing_user_by_email is not None:
            raise HTTPException(
                status_code=400, detail="REGISTER_USERNAME_ALREADY_EXISTS"
            )

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        # Temporary fix to ensure is_active, is_superuser, and is_verified cannot be specified by user
        user_dict.pop("is_active", None)
        user_dict.pop("is_superuser", None)
        user_dict.pop("is_verified", None)

        if "email" not in user_dict:
            user_dict["email"] = user_create.email
        if "username" not in user_dict:
            user_dict["username"] = user_create.username

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield CustomSQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: CustomSQLAlchemyUserDatabase = Depends(get_user_db),
):
    yield UserManager(user_db, password_helper=CustomPasswordHelper())


cookie_transport = CookieTransport(
    cookie_name="equisightauth",
    cookie_max_age=3600,
    cookie_secure=True,
    cookie_httponly=True,
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
