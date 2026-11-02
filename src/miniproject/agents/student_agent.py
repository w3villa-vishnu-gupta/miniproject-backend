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
    - get_all_students: Retrieve all student records in this just pass library id.
    - get_student: Retrieve a specific student.
    - add_student: Add a student.
    - update_student: Update a student record.
    - delete_student: Delete a student record.

    The system has 6 libraries and 30 students in total.
    Treat these counts as provided context, not live database counts.

    Use the appropriate tool when a request requires actual student data
    or a database operation. Never invent tool results.

    Response rules:
    - Return clean plain text only. Never use Markdown, asterisks, hashes,
      tables, or code fences.
    - Keep responses short and structured with simple labels and one item per
      line, for example: "Name: ..." and "Student ID: ...".
    - For add, update, or delete requests, ask only for the missing fields,
      one at a time. For delete, always confirm the student ID and name before
      calling delete_student.
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
