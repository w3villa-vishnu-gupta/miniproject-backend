import os

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm

from miniproject.agents.student_agent import student_agent
from miniproject.agents.books_agent import book_agent
# Configure the Ollama server.
os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"


def before_agent_clb(context: CallbackContext):
    print(f"Agent: {context.agent_name}")


root_agent = Agent(
    name="library_assistant",

    model=LiteLlm(
        model="openai/deepseek/deepseek-v4-flash",
        api_base="https://velona.in/v1",
        api_key=os.getenv("VELONA_API_KEY", ""),
        max_tokens=1024,
    ),

    description="AI assistant for the LibraryHub application.",

    instruction="""
    
You are the LibraryHub assistant.

You have exactly one subagent available:
student_agent

IMPORTANT ROUTING RULE:

If the user asks anything about a student, you MUST transfer
control to student_agent using the available agent transfer mechanism.

Examples:
- Show all students.
- Find student ID 2.
- Get student details.
- Add a new student.

Do not answer student-related questions yourself.
Do not call student tools directly.
Do not tell the user that you are going to retrieve data.
Transfer control to student_agent immediately.
    """,

    sub_agents=[student_agent,book_agent],
    before_agent_callback=before_agent_clb,
)