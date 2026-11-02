from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import text

from miniproject.auth.auth import get_current_owner
from miniproject.connections.db import engine
from miniproject.schemas.book import Book
from miniproject.schemas.Bookassigned import Bookassigned

router = APIRouter(tags=["books"])


@router.post("/createaccount/addbook")
@router.post("/books")
def add_book(
    book_data: Book,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        library = connection.execute(
            text("SELECT id FROM libraries WHERE id = :library_id AND owner_id = :owner_id"),
            {"library_id": book_data.library_id, "owner_id": owner_id},
        ).first()

        if not library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found for this owner",
            )

        result = connection.execute(
            text("""
                INSERT INTO books (owner_id, library_id, title, author, category, copies, issued_copies, status, description)
                VALUES (:owner_id, :library_id, :title, :author, :category, :copies, :issued_copies, :status, :description)
                RETURNING id, title, author, category, copies, issued_copies, status, description, created_at
            """),
            {
                "owner_id": owner_id,
                "library_id": book_data.library_id,
                "title": book_data.title.strip(),
                "author": book_data.author.strip(),
                "category": book_data.category.strip(),
                "copies": max(1, book_data.copies),
                "issued_copies": max(0, getattr(book_data, "issued_copies", 0)),
                "status": book_data.status or "Available",
                "description": book_data.description.strip() if book_data.description else None,
            },
        )
        new_book = result.mappings().first()

    return {
        "message": f"Book '{book_data.title}' added successfully",
        "book": dict(new_book),
        "book_id": new_book["id"],
        "library_id": book_data.library_id,
    }


@router.get("/getallbooks")
@router.get("/books")
def get_all_books(
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.connect() as connection:
        library = connection.execute(
            text("SELECT id FROM libraries WHERE id = :library_id AND owner_id = :owner_id"),
            {"library_id": library_id, "owner_id": owner_id},
        ).first()

        if not library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found for this owner",
            )

        result = connection.execute(
            text("""
                SELECT id, library_id, title, author, category, copies, issued_copies, status, description, created_at
                FROM books
                WHERE owner_id = :owner_id AND library_id = :library_id
                ORDER BY id DESC
            """),
            {"owner_id": owner_id, "library_id": library_id},
        )
        return result.mappings().all()


@router.patch("/books/{book_id}")
def update_book(
    book_id: int,
    library_id: int,
    book_update: dict = Body(...),
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                UPDATE books
                SET title = COALESCE(:title, title),
                    author = COALESCE(:author, author),
                    category = COALESCE(:category, category),
                    copies = COALESCE(:copies, copies),
                    issued_copies = COALESCE(:issued_copies, issued_copies),
                    status = COALESCE(:status, status),
                    description = COALESCE(:description, description)
                WHERE id = :book_id AND owner_id = :owner_id AND library_id = :library_id
            """),
            {
                "title": book_update.get("title"),
                "author": book_update.get("author"),
                "category": book_update.get("category"),
                "copies": book_update.get("copies"),
                "issued_copies": book_update.get("issued_copies"),
                "status": book_update.get("status"),
                "description": book_update.get("description"),
                "book_id": book_id,
                "owner_id": owner_id,
                "library_id": library_id,
            },
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found for this library",
            )
    return {"message": "Book updated successfully"}


@router.delete("/books/{book_id}")
def delete_book(
    book_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM books WHERE id = :book_id AND owner_id = :owner_id AND library_id = :library_id"),
            {"book_id": book_id, "owner_id": owner_id, "library_id": library_id},
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found for this library",
            )
    return {"message": "Book deleted successfully"}


@router.get("/books/{book_id}")
def get_single_book(
    book_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, library_id, title, author, category, copies, issued_copies, status, description, created_at
                FROM books
                WHERE id = :book_id AND owner_id = :owner_id AND library_id = :library_id
            """),
            {"book_id": book_id, "owner_id": owner_id, "library_id": library_id},
        )
        book = result.mappings().first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book


@router.post("/assign-book")
@router.post("/book-assignments")
@router.post("/createaccount/assignbook")
def assign_book(
    assignment: Bookassigned,
    library_id: int | None = None,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        # 1. Fetch and verify the book
        book_query = text("""
            SELECT id, library_id, title, copies, issued_copies, status
            FROM books
            WHERE id = :book_id AND owner_id = :owner_id
        """)
        book = connection.execute(book_query, {"book_id": assignment.book_id, "owner_id": owner_id}).mappings().first()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found for this owner")

        lib_id = library_id if library_id is not None else book["library_id"]

        # Check copies availability
        if book["issued_copies"] >= book["copies"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All {book['copies']} copies of '{book['title']}' are currently issued.",
            )

        # 2. Verify student exists
        student = connection.execute(
            text("SELECT id, name FROM students WHERE id = :student_id AND owner_id = :owner_id AND library_id = :library_id"),
            {"student_id": assignment.student_id, "owner_id": owner_id, "library_id": lib_id},
        ).mappings().first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found in this library")

        # 3. Insert assignment record
        result = connection.execute(
            text("""
                INSERT INTO book_assignments (owner_id, library_id, book_id, student_id, assigned_date, return_date, status)
                VALUES (:owner_id, :library_id, :book_id, :student_id, :assigned_date, :return_date, :status)
                RETURNING id, book_id, student_id, assigned_date, return_date, status, created_at
            """),
            {
                "owner_id": owner_id,
                "library_id": lib_id,
                "book_id": assignment.book_id,
                "student_id": assignment.student_id,
                "assigned_date": str(assignment.assigned_date).strip(),
                "return_date": str(assignment.return_date).strip(),
                "status": assignment.status or "issued",
            },
        )
        new_assignment = result.mappings().first()

        # 4. Increment book issued_copies & update status if fully issued
        new_issued = book["issued_copies"] + 1
        new_status = "Issued" if new_issued >= book["copies"] else book["status"]

        connection.execute(
            text("""
                UPDATE books
                SET issued_copies = :issued_copies,
                    status = :status
                WHERE id = :book_id
            """),
            {"issued_copies": new_issued, "status": new_status, "book_id": assignment.book_id},
        )

    return {
        "message": f"Book '{book['title']}' assigned to {student['name']} successfully",
        "assignment": dict(new_assignment),
        "book_title": book["title"],
        "student_name": student["name"],
    }


@router.get("/assigned-books")
@router.get("/book-assignments")
def get_assigned_books(
    library_id: int,
    status_filter: str | None = None,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.connect() as connection:
        query = """
            SELECT
                ba.id,
                ba.library_id,
                ba.book_id,
                ba.student_id,
                ba.assigned_date,
                ba.return_date,
                ba.status,
                ba.created_at,
                b.title AS book_title,
                b.author AS book_author,
                b.category AS book_category,
                s.name AS student_name,
                s.phone AS student_phone,
                s.email AS student_email
            FROM book_assignments ba
            JOIN books b ON ba.book_id = b.id
            JOIN students s ON ba.student_id = s.id
            WHERE ba.owner_id = :owner_id AND ba.library_id = :library_id
        """
        params = {"owner_id": owner_id, "library_id": library_id}
        if status_filter:
            query += " AND ba.status = :status_filter"
            params["status_filter"] = status_filter

        query += " ORDER BY ba.id DESC"

        result = connection.execute(text(query), params)
        return result.mappings().all()


@router.patch("/return-book/{assignment_id}")
@router.post("/return-book/{assignment_id}")
def return_assigned_book(
    assignment_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        assignment = connection.execute(
            text("""
                SELECT id, book_id, student_id, status
                FROM book_assignments
                WHERE id = :assignment_id AND owner_id = :owner_id AND library_id = :library_id
            """),
            {"assignment_id": assignment_id, "owner_id": owner_id, "library_id": library_id},
        ).mappings().first()

        if not assignment:
            raise HTTPException(status_code=404, detail="Book assignment not found")

        if assignment["status"] == "returned":
            raise HTTPException(status_code=400, detail="This book has already been returned")

        # Mark assignment as returned
        connection.execute(
            text("UPDATE book_assignments SET status = 'returned' WHERE id = :assignment_id"),
            {"assignment_id": assignment_id},
        )

        # Decrement issued_copies and set book status to Available
        connection.execute(
            text("""
                UPDATE books
                SET issued_copies = GREATEST(0, issued_copies - 1),
                    status = 'Available'
                WHERE id = :book_id
            """),
            {"book_id": assignment["book_id"]},
        )

    return {"message": "Book marked as returned successfully"}


@router.delete("/assigned-books/{assignment_id}")
@router.delete("/book-assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.begin() as connection:
        assignment = connection.execute(
            text("SELECT id, book_id, status FROM book_assignments WHERE id = :id AND owner_id = :owner_id AND library_id = :library_id"),
            {"id": assignment_id, "owner_id": owner_id, "library_id": library_id},
        ).mappings().first()

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        # If it was still issued, decrement issued_copies
        if assignment["status"] != "returned":
            connection.execute(
                text("UPDATE books SET issued_copies = GREATEST(0, issued_copies - 1), status = 'Available' WHERE id = :book_id"),
                {"book_id": assignment["book_id"]},
            )

        connection.execute(
            text("DELETE FROM book_assignments WHERE id = :id"),
            {"id": assignment_id},
        )

    return {"message": "Assignment deleted successfully"}
