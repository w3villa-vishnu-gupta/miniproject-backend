import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pwdlib import PasswordHash
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from miniproject.connections.db import engine
from miniproject.schemas.user import UserCreate
from miniproject.controllers.scheduler import (
    start_scheduler,
    stop_scheduler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        start_scheduler()
    except Exception as e:
        print(f"[Scheduler Warning] Could not start scheduler: {e}")
    yield
    try:
        stop_scheduler()
    except Exception as e:
        print(f"[Scheduler Warning] Could not stop scheduler: {e}")


app = FastAPI(lifespan=lifespan)

password_hash = PasswordHash.recommended()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost",
    "https://library-hub-w3villa.vercel.app",
]

# Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "supersecret-session-key"),
    same_site="lax",
    https_only=False
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


@app.get("/health")
def health_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS connected"))
        return result.mappings().one()["connected"] == 1



@app.post("/users/")
def create_user(user: UserCreate):
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO users (name, email, password_hash)
                VALUES (:name, :email, :password_hash)
                RETURNING id
            """),
            {
                "name": user.name,
                "email": user.email,
                "password_hash": password_hash.hash(user.password),
            },
        )
        user_id = result.scalar()
        return {"id": user_id, "name": user.name, "email": user.email}


@app.get("/getallusers")
def get_all_users():
    with engine.connect() as conn:
        allusers = conn.execute(
            text("SELECT id, name, email, created_at FROM users")
        )
        return allusers.mappings().all()


from miniproject.controllers.createaccount import router as owner_router
from miniproject.auth.facebook import router as facebook_router
from miniproject.auth.google import router as google_router


app.include_router(owner_router)
app.include_router(facebook_router)
app.include_router(google_router)
