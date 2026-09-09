"""
Auth router — thin HTTP controller.
Responsibility: HTTP boundary only. Maps HTTP ↔ Application Commands ↔ Domain Entities.
Zero business logic lives here.
"""

from fastapi import APIRouter, Depends, status

from app.application.commands import AuthenticateUserCommand, RegisterUserCommand
from app.application.services.auth_service import AuthService
from app.domain.entities.user import UserEntity
from app.presentation.dependencies import get_auth_service, get_current_user
from app.presentation.schemas.auth import TokenSchema, UserLoginSchema
from app.presentation.schemas.user import UserCreateSchema, UserResponseSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_to_response(entity: UserEntity) -> UserResponseSchema:
    return UserResponseSchema(
        id=entity.id,
        username=entity.username,
        email=entity.email,
        is_active=entity.is_active,
        created_at=entity.created_at,
    )


@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreateSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponseSchema:
    """Register a new user account."""
    cmd = RegisterUserCommand(username=body.username, email=body.email, password=body.password)
    entity = await auth_service.register(cmd)
    return _user_to_response(entity)


@router.post("/login", response_model=TokenSchema)
async def login(
    credentials: UserLoginSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenSchema:
    """Authenticate and receive a JWT access token."""
    cmd = AuthenticateUserCommand(email=credentials.email, password=credentials.password)
    result = await auth_service.authenticate(cmd)
    return TokenSchema(access_token=result.access_token, token_type=result.token_type)


@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    current_user: UserEntity = Depends(get_current_user),
) -> UserResponseSchema:
    """Retrieve the currently authenticated user's profile."""
    return _user_to_response(current_user)
