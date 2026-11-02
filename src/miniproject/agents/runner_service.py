from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.events import Event, EventActions
from google.genai import types

from miniproject.agents.root_agent import root_agent

import os
import httpx
from urllib.parse import quote

DATABASE_URL = os.environ["DATABASE_URL"]

APP_NAME = "libraryhub"

# Create this only once when the module loads.
session_service = DatabaseSessionService(
    db_url=DATABASE_URL
)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


async def chat(
    message: str,
    user_id: str,
    session_id: str,
    token: str = "",
) -> str:

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    if not session:
        print("No session found. Creating a new session.")

        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={"access_token": token},
        )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                result = await client.get(
                    "http://localhost:8001/create-session-title/"
                    f"{user_id}/{session.id}/{quote(message, safe='')}",
                    timeout=60.0,
                )
                result.raise_for_status()

        except httpx.HTTPError as e:
            print(f"Title generation failed: {e}")

    else:
        print("Session found.")
        print(f"Existing session user: {session.user_id}")

        if token and session.state.get("access_token") != token:
            await session_service.append_event(
                session,
                Event(
                    author="user",
                    actions=EventActions(
                        state_delta={"access_token": token}
                    ),
                ),
            )

    content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )

    response_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            response_text = "".join(
                part.text or ""
                for part in event.content.parts
                if part.text
            )

    return response_text