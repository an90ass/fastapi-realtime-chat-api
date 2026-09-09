"""
AuthService — Application Use Case for user registration and authentication.

Dependency graph (no violations):
  AuthService → IUserRepository (domain port)
  AuthService → core/security   (cross-cutting concern, not infrastructure)
  AuthService → core/exceptions  (cross-cutting concern)
  AuthService → domain entities
  AuthService → application commands/results

Zero imports from: SQLAlchemy, FastAPI, Redis, or any Pydantic schema.
"""

from app.application.commands import (
    AuthTokenResult,
    AuthenticateUserCommand,
    RegisterUserCommand,
)
from app.core.exceptions import AuthenticationError, EntityAlreadyExistsError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.entities.user import UserEntity
from app.domain.ports.repositories import IUserRepository


class AuthService:
    """Use case encapsulating authentication and user registration business logic."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def register(self, cmd: RegisterUserCommand) -> UserEntity:
        """Register a new user. Raises EntityAlreadyExistsError on duplicate."""
        if await self._user_repo.get_by_email(cmd.email):
            raise EntityAlreadyExistsError("Email is already registered.")
        if await self._user_repo.get_by_username(cmd.username):
            raise EntityAlreadyExistsError("Username is already taken.")

        new_user = UserEntity(
            username=cmd.username,
            email=cmd.email,
            hashed_password=hash_password(cmd.password),
            is_active=True,
        )
        return await self._user_repo.create(new_user)

    async def authenticate(self, cmd: AuthenticateUserCommand) -> AuthTokenResult:
        """Authenticate user and return signed JWT access token."""
        user = await self._user_repo.get_by_email(cmd.email)
        if not user or not verify_password(cmd.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("User account is inactive.")

        token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )
        return AuthTokenResult(access_token=token)

    async def get_user_from_token(self, token: str) -> UserEntity:
        """Validate JWT token and return the associated active user entity."""
        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            raise AuthenticationError("Invalid or expired authentication token.")

        try:
            user_id = int(payload["sub"])
        except (ValueError, TypeError):
            raise AuthenticationError("Malformed token subject.")

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("Authenticated user no longer exists.")
        if not user.is_active:
            raise AuthenticationError("User account is deactivated.")

        return user
