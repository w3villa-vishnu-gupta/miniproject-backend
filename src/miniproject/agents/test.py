import os
import asyncio

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# Ollama configuration
os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"

MODEL = "ollama_chat/qwen2.5:1.5b-instruct"
APP_NAME = "library_test"
USER_ID = "user_1"


# In-memory student database
students = {
    1: {
        "name": "Rahul",
        "email": "rahul@example.com",
        "borrowed_books": ["Python Basics", "Clean Code"],
        "membership": "Active",
    },
    2: {
        "name": "Priya",
        "email": "priya@example.com",
        "borrowed_books": ["Database Systems"],
        "membership": "Active",
    },
    3: {
        "name": "Amit",
        "email": "amit@example.com",
        "borrowed_books": [],
        "membership": "Inactive",
    },
}


# Tool for the student agent
def get_student_details(student_id: int) -> dict:
    """Get a student's details, membership, and borrowed books by student ID."""

    print(f"\n[TOOL EXECUTED] get_student_details({student_id})")

    student = students.get(student_id)

    if student is None:
        return {
            "success": False,
            "message": f"No student found with ID {student_id}",
        }

    return {
        "success": True,
        "student_id": student_id,
        "name": student["name"],
        "email": student["email"],
        "membership": student["membership"],
        "borrowed_books": student["borrowed_books"],
        "borrowed_book_count": len(student["borrowed_books"]),
    }


# Subagent
student_agent = Agent(
    name="student_agent",
    model=LiteLlm(model=MODEL),
    description="Handles student records and student-related queries.",
    instruction="""
    You are a student records assistant.

    When asked for student details, ALWAYS call get_student_details.
    Answer using the actual tool result.
    Never invent student information.
    """,
    tools=[get_student_details],
)


# Root agent
root_agent = Agent(
    name="library_assistant",
    model=LiteLlm(model=MODEL),
    description="Assistant for library operations.",
    instruction="""
    You are the main library assistant.

    For any request involving student records or student details,
    delegate the request to student_agent.

    Do not answer student record queries yourself.
    Do not invent tool names.
    Use the result returned by student_agent to answer the user.
    """,
    sub_agents=[student_agent],
)


# Run a test
async def main():
    session_service = InMemorySessionService()

    runner = Runner(
        agent=student_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    query = (
        "Find student ID 2. Tell me their name, email, "
        "membership status, and how many books they have borrowed."
    )

    print(f"\n[USER QUERY] {query}\n")
    print("[AGENT EXECUTION STARTED]\n")

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=query)],
        ),
    ):
        print(f"[EVENT] author={event.author}")

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(
                        f"[FUNCTION CALL] "
                        f"{part.function_call.name}: "
                        f"{part.function_call.args}"
                    )

                if part.function_response:
                    print(
                        f"[FUNCTION RESPONSE] "
                        f"{part.function_response.name}: "
                        f"{part.function_response.response}"
                    )

                if part.text:
                    print(f"[TEXT] {part.text}")

        if event.is_final_response():
            print("\n[FINAL RESPONSE RECEIVED]")


if __name__ == "__main__":
    asyncio.run(main())