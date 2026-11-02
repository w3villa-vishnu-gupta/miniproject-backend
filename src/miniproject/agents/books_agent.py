import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext

from miniproject.tools.book_tool import (
    create_book,
    get_book,
    get_all_books,
    get_book_by_category,
    get_all_book_description_by_category,
    issue_book,
)

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
        "book descriptions, story recommendations, and issuing books to students."
    ),
    instruction="""
    You are the Book Agent for LibraryHub.

    Your capabilities:
    1. get_all_books: Retrieve book catalog for a library (accepts optional limit).
    2. get_book: Look up a specific book by title or book_id to check availability and details.
    3. create_book: Add a new book (title, author, category, copies, optional description).
    4. get_book_by_category: Find books belonging to a specific genre/category (Fiction, Story, Science, etc.).
    5. get_all_book_description_by_category: Fetch book descriptions to suggest or recommend books based on a story topic, category, or keyword. Pass category, query, and limit as needed.
    6. issue_book: Issue/assign a book to a student using book title or ID, and student name or ID.

    Guidelines:
    - When a user asks for book recommendations or wants a story/book on a specific topic, use get_all_book_description_by_category. Pass an appropriate limit (e.g. 5) and suggest matching books based on their descriptions.
    - When issuing a book, pass the book title/id and student name/id to issue_book.
    - When adding a book, call create_book.
    - Return clean, plain text responses. Keep them clear, simple, and helpful. Do not use Markdown tables or code fences.
    """,
    before_agent_callback=before_agent_clb1,
    tools=[
        create_book,
        get_book,
        get_all_books,
        get_book_by_category,
        get_all_book_description_by_category,
        issue_book,
    ],
)
