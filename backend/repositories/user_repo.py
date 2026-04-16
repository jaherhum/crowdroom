from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from db.models.user import User
from schemas.user import UserCreate, UserUpdate



class UserRepository:
    def __init__(self, db_session: Session):
        self._db_session = db_session

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self._db_session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self._db_session.exec(select(User).where(User.email == email.lower())).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self._db_session.exec(select(User).where(User.username == username.lower())).first()

    def save(self, user: User) -> User:
        self._db_session.add(user)
        self._db_session.commit()
        self._db_session.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self._db_session.delete(user)
        self._db_session.commit()
