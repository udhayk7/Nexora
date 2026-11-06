from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.auth import UserResponse

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve profile of currently authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return profile details for the authenticated user."""
    return UserResponse.model_validate(current_user)
