from sqlmodel import Session, SQLModel, create_engine

from backend.core.config import settings

db_url = settings.DATABASE_URL

connect_args = {"check_same_thread": False}
engine = create_engine(db_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
