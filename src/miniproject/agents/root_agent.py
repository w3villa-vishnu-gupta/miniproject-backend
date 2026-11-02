import os

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm

from miniproject.agents.student_agent import student_agent
from miniproject.agents.books_agent import book_agent

# Configure the Ollama server if needed.
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
You are the primary LibraryHub AI assistant.

You have two specialized subagents available:
1. student_agent: Handles all student-related operations, including adding students, updating records, searching students, and listing students.
2. book_agent: Handles all book-related operations, including listing books, searching catalog, finding books by category, book descriptions/recommendations (like stories or topics), creating books, and issuing books to students.

ROUTING RULES:
- If the user asks about students (e.g., "create a student", "list students", "find student", "update student"), transfer control to student_agent immediately.
- If the user asks about books (e.g., "show books", "recommend a story book", "add book", "issue book to student", "books in category"), transfer control to book_agent immediately.
- If the user sends a greeting (e.g., "hi", "hello"), greet them warmly and briefly mention that you can help with books and students.
- Do not attempt to call database tools yourself; immediately route to the respective subagent.
    """,
    sub_agents=[student_agent, book_agent],
    before_agent_callback=before_agent_clb,
)
