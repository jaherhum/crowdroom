from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.database import create_db_and_tables

from api.routes.auth import router as auth_router
from api.routes.queue import router as queue_router
from api.routes.search import router as search_router
from api.routes.session import router as session_router
from api.routes.user import router as user_router
from core.config import settings


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
app.include_router(user_router, prefix=f"{settings.API_V1_STR}/user", tags=["user"])

