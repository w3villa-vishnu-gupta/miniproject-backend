import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext

from miniproject.tools.book_tool import get_all_books

def before_agent_clb1(context: CallbackContext):
    agent_name = context.agent_name
    print(f"---------------- agent_name: {agent_name}")


book_agent = Agent(
    name="book_agent",
    model=LiteLlm(
        model="openai/deepseek/deepseek-v4-flash",
        api_base="https://velona.in/v1",
        api_key=os.getenv("VELONA_API_KEY", ""),
        max_tokens=1024,
    ),
    
    description=(
        "Manages book inventory, catalog searches, book availability, "
        "and library book records."
    ),
    instruction="""
    You are the Book Agent for LibraryHub.

    You can manage library inventory and lookups using your available tools:
    - get_all_books: Retrieve books catalog for a library.

    Use the appropriate tool when a request requires actual book data.
    Never invent tool results.

    Response rules:
    - Return clean plain text only. Never use Markdown, asterisks, hashes,
      tables, or code fences.
    - Keep responses short and structured with simple labels and one item per
      line, for example: "Title: ..." and "ISBN: ...".
    """,
    before_agent_callback=before_agent_clb1,
    tools=[
        get_all_books
    ],
)
