from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException

from backend.api.users.dependencies import get_user_service
from backend.schemas.user import UserCreate, UserRead, UserUpdate
from backend.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead], status_code=status.HTTP_200_OK)
async def get_users(
    user_service: UserService = Depends(get_user_service)) -> list[UserRead]:
    """Retrieves a list of all users.

    Args:
        user_service (UserService): The injected user service.

    Returns:
        list[UserRead]: A list of user schemas.
    """
    return user_service.get_all_users()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, user_service: UserService = Depends(get_user_service)) -> UserRead:
    """Creates a new user.

    Args:
        user_data (UserCreate): The schema containing user creation details.
        user_service (UserService): The injected user service.

    Returns:
        UserRead: The newly created user schema.
    """
    return user_service.create_user(user_data)


@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_user(user_id: UUID, user_data: UserUpdate, user_service: UserService = Depends(get_user_service)) -> UserRead:
    """Updates an existing user's information.

    Args:
        user_id (UUID): The unique identifier of the user to update.
        user_data (UserUpdate): The schema containing the fields to update.
        user_service (UserService): The injected user service.

    Returns:
        UserRead: The updated user schema.
    """
    return user_service.update_user(user_id, user_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, user_service: UserService = Depends(get_user_service),) -> None:
    """Deletes a user from the system.

    Args:
        user_id (UUID): The unique identifier of the user to delete.
        user_service (UserService): The injected user service.
    """
    user_service.delete_user(user_id)
