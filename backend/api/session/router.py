"""Session management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.api.session.dependencies import get_session_service
from backend.schemas.session import CreateSession, ReadSession, UpdateSession
from backend.services.session_service import SessionService

router = APIRouter(prefix="/session", tags=["session"])


@router.get("/", response_model=list[ReadSession], status_code=status.HTTP_200_OK)
async def get_sessions(
    session_service: SessionService = Depends(get_session_service),
) -> list[ReadSession]:
    """Retrieves a list of all sessions.

    Args:
        session_service (SessionService): The injected session service.

    Returns:
        list[ReadSession]: A list of session schemas.
    """
    sessions = session_service.get_all_sessions()
    return [ReadSession.model_validate(s) for s in sessions]


@router.get(
    "/{session_id}", response_model=ReadSession, status_code=status.HTTP_200_OK
)
async def get_session(
    session_id: UUID,
    session_service: SessionService = Depends(get_session_service),
) -> ReadSession:
    """Retrieves a specific session by its ID.

    Args:
        session_id (UUID): The unique identifier of the session.
        session_service (SessionService): The injected session service.

    Returns:
        ReadSession: The session schema.
    """
    session = session_service.get_session(session_id)
    return ReadSession.model_validate(session)


@router.post(
    "/", response_model=ReadSession, status_code=status.HTTP_201_CREATED
)
async def create_session(
    session_data: CreateSession,
    session_service: SessionService = Depends(get_session_service),
) -> ReadSession:
    """Creates a new session.

    Args:
        session_data (CreateSession): The schema containing session creation details.
        session_service (SessionService): The injected session service.

    Returns:
        ReadSession: The newly created session schema.
    """
    session = session_service.create_session(session_data)
    return ReadSession.model_validate(session)


@router.patch(
    "/{session_id}", response_model=ReadSession, status_code=status.HTTP_200_OK
)
async def update_session(
    session_id: UUID,
    session_data: UpdateSession,
    session_service: SessionService = Depends(get_session_service),
) -> ReadSession:
    """Updates an existing session.

    Args:
        session_id (UUID): The unique identifier of the session to update.
        session_data (UpdateSession): The schema containing the fields to update.
        session_service (SessionService): The injected session service.

    Returns:
        ReadSession: The updated session schema.
    """
    session = session_service.update_session(session_id, session_data)
    return ReadSession.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    session_service: SessionService = Depends(get_session_service),
) -> None:
    """Deletes a session from the system.

    Args:
        session_id (UUID): The unique identifier of the session to delete.
        session_service (SessionService): The injected session service.
    """
    session_service.delete_session(session_id)
