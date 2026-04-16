from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.db.database import create_db_and_tables

from backend.api.auth.router import router as auth_router
from backend.api.queue.router import router as queue_router
from backend.api.search.router import router as search_router
from backend.api.session.router import router as session_router
from backend.api.users.router import router as user_router
from backend.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables in database...")
    create_db_and_tables()
    yield
    print("App closed.")


app = FastAPI(lifespan=lifespan)


app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(queue_router, prefix=f"{settings.API_V1_STR}/queue", tags=["queue"])
app.include_router(search_router, prefix=f"{settings.API_V1_STR}/search", tags=["search"])
app.include_router(session_router, prefix=f"{settings.API_V1_STR}/session", tags=["session"])
app.include_router(user_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
