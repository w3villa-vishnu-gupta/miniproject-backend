import os
import uuid

import httpx
from fastapi import APIRouter, Header, HTTPException
from google.adk.sessions import DatabaseSessionService
from pydantic import BaseModel
from sqlalchemy import text

from miniproject.connections.db import engine

router = APIRouter(tags=["chat"])

DATABASE_URL = os.environ.get("DATABASE_URL", "")
session_service = DatabaseSessionService(
    db_url=DATABASE_URL
)


class ChatMessageRequest(BaseModel):
    message: str
    session_id: str | None = None
    token: str | None = None


@router.post("/chat")
async def chat_api(
    req: ChatMessageRequest,
    authorization: str | None = Header(None),
):
    token = req.token or ""
    user_id = "user"
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        try:
            from miniproject.auth.auth import verify_token
            payload = verify_token(token)
            if payload and payload.get("sub"):
                user_id = str(payload["sub"])
        except Exception:
            pass

    session_id = req.session_id or str(uuid.uuid4())
    from miniproject.agents.runner_service import chat
    print(token)
    reply = await chat(
        message=req.message,
        user_id=user_id,
        session_id=session_id,
        token=token,
    )
    return {"reply": reply, "response": reply, "session_id": session_id}


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    try:
        response = await session_service.list_sessions(
            app_name="libraryhub",
            user_id=user_id,
        )

        return {
            "sessions": [
                {
                    "id": session.id,
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "last_update_time": session.last_update_time,
                }
                for session in response.sessions
            ]
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve sessions",
        ) from exc


@router.get("/sessions/{user_id}/{session_id}")
async def get_chat_history(user_id: str, session_id: str):
    session = await session_service.get_session(
        app_name="libraryhub",
        user_id=user_id,
        session_id=session_id,
    )

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = []

    for event in session.events:
        if not event.content or not event.content.parts:
            continue

        for part in event.content.parts:
            if part.text:
                messages.append({
                    "role": event.author,
                    "text": part.text,
                    "timestamp": event.timestamp,
                })

    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "messages": messages,
    }


@router.get("/create-session-title/{userid}/{sessionid}/{message}")
def create_session_title(userid: int, sessionid: str, message: str):
    if userid is None or sessionid is None or message is None:
        raise HTTPException(status_code=400, detail="Invalid request")

    velona_key = os.getenv("VELONA_API_KEY", "")
    response = httpx.post(
        "https://velona.in/gateway/v1/inference/run",
        headers={"Authorization": f"Bearer {velona_key}"},
        json={
            "model": "deepseek/deepseek-chat",
            "turns": [
                {"role": "system", "content": "Generate a title in 3-5 words. Output only the title."},
                {"role": "user", "content": message}
            ],
            "max_tokens": 12
        },
        timeout=15
    )

    if response.status_code == 200:
        title = response.json()["data"]["output"].strip()

        with engine.begin() as session:
            session.execute(
                text("""
                    INSERT INTO session_title (user_id, session_id, title)
                    VALUES (:user_id, :session_id, :title)
                """),
                {
                    "user_id": userid,
                    "session_id": sessionid,
                    "title": title,
                }
            )

        return {"title": title}

    else:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/get-titles")
def get_titles(session_ids: list[str]):
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT session_id, title
                FROM session_title
                WHERE session_id = ANY(:session_ids)
            """),
            {"session_ids": session_ids}
        )

        titles = {
            row.session_id: row.title
            for row in result
        }

    return {
        "titles": [
            {
                "session_id": session_id,
                "title": titles.get(session_id, "Hi")
            }
            for session_id in session_ids
        ]
    }
