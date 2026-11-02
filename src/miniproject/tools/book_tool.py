import os
from datetime import datetime, timedelta, timezone
from google.adk.tools import ToolContext
from sqlalchemy import text

from miniproject.connections.db import engine
from miniproject.auth.auth import verify_token


def _get_owner_and_library_id(tool_context: ToolContext, library_id: int | None = None) -> tuple[int, int]:
    """Helper to extract authenticated owner_id and active library_id."""
    token = tool_context.state.get("access_token")
    if not token:
        raise ValueError("Authentication token is missing. Please log in first.")

    payload = verify_token(token)
    owner_id = int(payload["sub"])

    with engine.connect() as conn:
        if library_id is not None:
            lib = conn.execute(
                text("SELECT id FROM libraries WHERE id = :lib_id AND owner_id = :owner_id"),
                {"lib_id": library_id, "owner_id": owner_id},
            ).first()
            if not lib:
                raise ValueError(f"Library ID {library_id} not found for this account.")
            return owner_id, library_id

        # Automatically use owner's primary library if library_id is omitted
        lib = conn.execute(
            text("SELECT id FROM libraries WHERE owner_id = :owner_id ORDER BY id ASC LIMIT 1"),
            {"owner_id": owner_id},
        ).first()
        if not lib:
            raise ValueError("No library found. Please create a library first.")
        return owner_id, lib[0]


async def create_book(
    tool_context: ToolContext,
    title: str,
    author: str,
    category: str,
    copies: int = 1,
    description: str | None = None,
    library_id: int | None = None,
) -> dict:
    """
    Add a new book to the library catalog.

    Args:
        title: Title of the book.
        author: Author of the book.
        category: Genre/Category (e.g. Fiction, Story, Science, History, Novel).
        copies: Number of physical copies (default is 1).
        description: Brief description, synopsis, or storyline of the book.
        library_id: Optional library ID (defaults to owner's library).
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        copies = max(1, int(copies))

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO books (owner_id, library_id, title, author, category, copies, issued_copies, status, description)
                    VALUES (:owner_id, :library_id, :title, :author, :category, :copies, 0, 'Available', :description)
                    RETURNING id, title, author, category, copies, status, description
                """),
                {
                    "owner_id": owner_id,
                    "library_id": lib_id,
                    "title": title.strip(),
                    "author": author.strip(),
                    "category": category.strip(),
                    "copies": copies,
                    "description": description.strip() if description else None,
                },
            ).mappings().first()

        return {
            "success": True,
            "message": f"Book '{title}' by {author} added successfully with {copies} copies.",
            "book": dict(result),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_book(
    tool_context: ToolContext,
    book_id: int | None = None,
    title: str | None = None,
    library_id: int | None = None,
) -> dict:
    """
    Get detailed information about a specific book by ID or title.

    Args:
        book_id: Numeric ID of the book (optional if title is provided).
        title: Title or partial title of the book to look up.
        library_id: Optional library ID.
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)

        with engine.connect() as conn:
            if book_id is not None:
                row = conn.execute(
                    text("""
                        SELECT id, title, author, category, copies, issued_copies, status, description
                        FROM books
                        WHERE id = :book_id AND owner_id = :owner_id AND library_id = :lib_id
                    """),
                    {"book_id": book_id, "owner_id": owner_id, "lib_id": lib_id},
                ).mappings().first()
            elif title:
                row = conn.execute(
                    text("""
                        SELECT id, title, author, category, copies, issued_copies, status, description
                        FROM books
                        WHERE owner_id = :owner_id AND library_id = :lib_id AND title ILIKE :title
                        LIMIT 1
                    """),
                    {"title": f"%{title.strip()}%", "owner_id": owner_id, "lib_id": lib_id},
                ).mappings().first()
            else:
                return {"error": "Please provide either book_id or title to search."}

        if not row:
            return {"error": "Book not found in this library."}

        book_data = dict(row)
        book_data["available_copies"] = max(0, book_data["copies"] - book_data["issued_copies"])
        return {"book": book_data}
    except Exception as e:
        return {"error": str(e)}


async def get_all_books(
    tool_context: ToolContext,
    library_id: int | None = None,
    limit: int = 50,
) -> dict:
    """
    Fetch all books available in the library catalog.

    Args:
        library_id: Optional library ID.
        limit: Maximum number of books to return (default 50).
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, title, author, category, copies, issued_copies, status, description
                    FROM books
                    WHERE owner_id = :owner_id AND library_id = :lib_id
                    ORDER BY id DESC
                    LIMIT :limit
                """),
                {"owner_id": owner_id, "lib_id": lib_id, "limit": limit},
            ).mappings().all()

        books = [dict(r) for r in rows]
        for b in books:
            b["available_copies"] = max(0, b["copies"] - b["issued_copies"])

        return {"count": len(books), "books": books}
    except Exception as e:
        return {"error": str(e)}


async def get_book_by_category(
    tool_context: ToolContext,
    category: str,
    library_id: int | None = None,
    limit: int = 20,
) -> dict:
    """
    Find books belonging to a specific category or genre.

    Args:
        category: The category name (e.g. 'Story', 'Science', 'Fiction', 'History', etc.).
        library_id: Optional library ID.
        limit: Maximum number of books to return (default 20).
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, title, author, category, copies, issued_copies, status, description
                    FROM books
                    WHERE owner_id = :owner_id AND library_id = :lib_id AND category ILIKE :cat
                    ORDER BY id DESC
                    LIMIT :limit
                """),
                {"owner_id": owner_id, "lib_id": lib_id, "cat": f"%{category.strip()}%", "limit": limit},
            ).mappings().all()

        books = [dict(r) for r in rows]
        for b in books:
            b["available_copies"] = max(0, b["copies"] - b["issued_copies"])

        return {"category": category, "count": len(books), "books": books}
    except Exception as e:
        return {"error": str(e)}


async def get_all_book_description_by_category(
    tool_context: ToolContext,
    category: str | None = None,
    query: str | None = None,
    limit: int = 10,
    library_id: int | None = None,
) -> dict:
    """
    Retrieve book descriptions filtered by category or topic.
    Use this to recommend or suggest books when a user describes what kind of story or topic they want to read.

    Args:
        category: Optional category or genre to filter by.
        query: Optional keyword or topic to search within description or title.
        limit: Number of book descriptions to retrieve (default 10). AI can adjust limit as needed.
        library_id: Optional library ID.
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        limit = max(1, min(50, int(limit)))

        sql = """
            SELECT id, title, author, category, description, copies, issued_copies, status
            FROM books
            WHERE owner_id = :owner_id AND library_id = :lib_id
        """
        params = {"owner_id": owner_id, "lib_id": lib_id, "limit": limit}

        if category and category.strip():
            sql += " AND category ILIKE :cat"
            params["cat"] = f"%{category.strip()}%"

        if query and query.strip():
            sql += " AND (description ILIKE :q OR title ILIKE :q)"
            params["q"] = f"%{query.strip()}%"

        sql += " ORDER BY id DESC LIMIT :limit"

        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        descriptions = []
        for r in rows:
            descriptions.append({
                "id": r["id"],
                "title": r["title"],
                "author": r["author"],
                "category": r["category"],
                "description": r["description"] or "No description provided.",
                "available": (r["copies"] - r["issued_copies"]) > 0,
            })

        return {"count": len(descriptions), "books": descriptions}
    except Exception as e:
        return {"error": str(e)}


async def issue_book(
    tool_context: ToolContext,
    book_id: int | None = None,
    book_title: str | None = None,
    student_id: int | None = None,
    student_name: str | None = None,
    return_date: str | None = None,
    library_id: int | None = None,
) -> dict:
    """
    Issue or assign a book to a registered student.

    Args:
        book_id: ID of the book to issue (or provide book_title).
        book_title: Title of the book if ID is not known.
        student_id: ID of the student receiving the book (or provide student_name).
        student_name: Name of the student if ID is not known.
        return_date: Due return date in YYYY-MM-DD format (defaults to 14 days from today).
        library_id: Optional library ID.
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)

        # Default return date: 14 days from today
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not return_date or not str(return_date).strip():
            due_dt = datetime.now(timezone.utc) + timedelta(days=14)
            return_date = due_dt.strftime("%Y-%m-%d")
        else:
            return_date = str(return_date).strip()

        with engine.begin() as conn:
            # 1. Lookup Book
            if book_id is not None:
                book = conn.execute(
                    text("SELECT id, title, copies, issued_copies, status FROM books WHERE id = :bid AND owner_id = :oid AND library_id = :lid"),
                    {"bid": book_id, "oid": owner_id, "lid": lib_id},
                ).mappings().first()
            elif book_title:
                book = conn.execute(
                    text("SELECT id, title, copies, issued_copies, status FROM books WHERE owner_id = :oid AND library_id = :lid AND title ILIKE :title LIMIT 1"),
                    {"title": f"%{book_title.strip()}%", "oid": owner_id, "lid": lib_id},
                ).mappings().first()
            else:
                return {"error": "Please provide either book_id or book_title to issue."}

            if not book:
                return {"error": "Book not found in this library."}

            if book["issued_copies"] >= book["copies"]:
                return {"error": f"All {book['copies']} copies of '{book['title']}' are currently issued out."}

            # 2. Lookup Student
            if student_id is not None:
                student = conn.execute(
                    text("SELECT id, name, phone, email FROM students WHERE id = :sid AND owner_id = :oid AND library_id = :lid"),
                    {"sid": student_id, "oid": owner_id, "lid": lib_id},
                ).mappings().first()
            elif student_name:
                student = conn.execute(
                    text("SELECT id, name, phone, email FROM students WHERE owner_id = :oid AND library_id = :lid AND name ILIKE :name LIMIT 1"),
                    {"name": f"%{student_name.strip()}%", "oid": owner_id, "lid": lib_id},
                ).mappings().first()
            else:
                return {"error": "Please provide either student_id or student_name."}

            if not student:
                return {"error": "Student not found in this library. Please check the name/ID or register the student first."}

            # 3. Create book assignment
            res = conn.execute(
                text("""
                    INSERT INTO book_assignments (owner_id, library_id, book_id, student_id, assigned_date, return_date, status)
                    VALUES (:owner_id, :library_id, :book_id, :student_id, :assigned_date, :return_date, 'issued')
                    RETURNING id, assigned_date, return_date, status
                """),
                {
                    "owner_id": owner_id,
                    "library_id": lib_id,
                    "book_id": book["id"],
                    "student_id": student["id"],
                    "assigned_date": today_str,
                    "return_date": return_date,
                },
            ).mappings().first()

            # 4. Increment issued copies on book
            new_issued = book["issued_copies"] + 1
            new_status = "Issued" if new_issued >= book["copies"] else "Available"
            conn.execute(
                text("UPDATE books SET issued_copies = :issued, status = :status WHERE id = :bid"),
                {"issued": new_issued, "status": new_status, "bid": book["id"]},
            )

        return {
            "success": True,
            "message": f"Successfully issued '{book['title']}' to student {student['name']} (ID: {student['id']}). Due return date is {return_date}.",
            "assignment_id": res["id"],
            "book": book["title"],
            "student": student["name"],
            "return_date": return_date,
        }
    except Exception as e:
        return {"error": str(e)}
