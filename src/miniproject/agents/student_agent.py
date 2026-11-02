import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext

from miniproject.tools.student_tool import (
    get_all_students,
    get_student,
    add_student,
    update_student,
    delete_student,
)


def before_agent_clb1(context: CallbackContext):
    agent_name = context.agent_name
    print(f"---------------- agent_name: {agent_name}")


student_agent = Agent(
    name="student_agent",
    model=LiteLlm(
        model="openai/deepseek/deepseek-v4-flash",
        api_base="https://velona.in/v1",
        api_key=os.getenv("VELONA_API_KEY", ""),
        max_tokens=1024,
    ),
    description=(
        "Handles student records, student accounts, "
        "library registration, and student services."
    ),
    instruction="""
    You are the Student Agent for LibraryHub.

    You can manage student records using your available tools:
    - get_all_students: Retrieve student records.
    - get_student: Retrieve a specific student by student ID.
    - add_student: Register a new student (requires name and phone, optional email, address).
    - update_student: Update a student record.
    - delete_student: Delete a student record.

    Use the appropriate tool when a request requires actual student data
    or a database operation. Never invent tool results.

    Response rules:
    - Return clean plain text only. Never use Markdown, asterisks, hashes,
      tables, or code fences.
    - Keep responses short, helpful, and friendly.
    - For delete, confirm the student ID and name before calling delete_student.
    """,
    before_agent_callback=before_agent_clb1,
    tools=[
        get_all_students,
        get_student,
        add_student,
        update_student,
        delete_student,
    ],
)
