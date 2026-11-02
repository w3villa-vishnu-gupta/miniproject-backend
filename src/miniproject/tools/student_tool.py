from datetime import datetime, timezone
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


async def get_all_students(
    tool_context: ToolContext,
    library_id: int | None = None,
) -> dict:
    """Fetch all students from the system, optionally filtered by library_id."""
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, name, email, phone, address, library_id, alumini,
                           status, payment_start_month, last_payment_date
                    FROM students
                    WHERE owner_id = :owner_id AND library_id = :lib_id
                    ORDER BY id DESC
                """),
                {"owner_id": owner_id, "lib_id": lib_id},
            ).mappings().all()

        students = [dict(r) for r in rows]
        # Format date fields for clean JSON serialization
        for s in students:
            if s.get("payment_start_month"):
                s["payment_start_month"] = str(s["payment_start_month"])
            if s.get("last_payment_date"):
                s["last_payment_date"] = str(s["last_payment_date"])

        return {"count": len(students), "students": students}
    except Exception as e:
        return {"error": str(e)}


async def get_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int | None = None,
) -> dict:
    """Fetch a single student by student_id."""
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT id, name, email, phone, address, library_id, alumini,
                           status, payment_start_month, last_payment_date
                    FROM students
                    WHERE id = :student_id AND owner_id = :owner_id AND library_id = :lib_id
                """),
                {"student_id": student_id, "owner_id": owner_id, "lib_id": lib_id},
            ).mappings().first()

        if not row:
            return {"error": f"Student with ID {student_id} not found."}

        data = dict(row)
        if data.get("payment_start_month"):
            data["payment_start_month"] = str(data["payment_start_month"])
        if data.get("last_payment_date"):
            data["last_payment_date"] = str(data["last_payment_date"])

        return {"student": data}
    except Exception as e:
        return {"error": str(e)}


async def add_student(
    tool_context: ToolContext,
    name: str,
    phone: str,
    library_id: int | None = None,
    email: str | None = None,
    address: str | None = None,
    payment_start_month: str | None = None,
) -> dict:
    """
    Register a new student in the library system.

    Args:
        tool_context: Context containing the authenticated user's state.
        name: Student's full name.
        phone: Student's phone number.
        library_id: Optional integer ID of the library (defaults to owner's library).
        email: Student's email address, if provided.
        address: Student's address, if provided.
        payment_start_month: Payment start date in YYYY-MM-DD format, if provided.
    """
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)

        with engine.begin() as conn:
            if email and email.strip():
                existing = conn.execute(
                    text("""
                        SELECT id FROM students 
                        WHERE owner_id = :owner_id AND LOWER(email) = LOWER(:email)
                    """),
                    {"owner_id": owner_id, "email": email.strip()},
                ).first()
                if existing:
                    return {"error": f"Student with email '{email}' already exists."}

            result = conn.execute(
                text("""
                    INSERT INTO students (
                        owner_id, library_id, name, email, phone, address,
                        payment_start_month, last_payment_date, status, alumini
                    )
                    VALUES (
                        :owner_id, :library_id, :name, :email, :phone, :address,
                        :payment_start_month, CURRENT_DATE, 'Active', false
                    )
                    RETURNING id, name, email, phone, library_id
                """),
                {
                    "owner_id": owner_id,
                    "library_id": lib_id,
                    "name": name.strip(),
                    "email": email.strip() if email else None,
                    "phone": phone.strip(),
                    "address": address.strip() if address else None,
                    "payment_start_month": payment_start_month.strip() if payment_start_month else None,
                },
            ).mappings().first()

        return {
            "success": True,
            "message": f"Student '{name}' registered successfully.",
            "student": dict(result),
        }
    except Exception as e:
        return {"error": str(e)}


async def update_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int | None = None,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    status: str | None = None,
    alumini: bool | None = None,
) -> dict:
    """Update student information."""
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)

        update_fields = []
        params = {"student_id": student_id, "owner_id": owner_id, "lib_id": lib_id}

        if name is not None:
            update_fields.append("name = :name")
            params["name"] = name.strip()
        if phone is not None:
            update_fields.append("phone = :phone")
            params["phone"] = phone.strip()
        if email is not None:
            update_fields.append("email = :email")
            params["email"] = email.strip()
        if address is not None:
            update_fields.append("address = :address")
            params["address"] = address.strip()
        if status is not None:
            update_fields.append("status = :status")
            params["status"] = status.strip()
        if alumini is not None:
            update_fields.append("alumini = :alumini")
            params["alumini"] = alumini

        if not update_fields:
            return {"error": "No update fields provided."}

        with engine.begin() as conn:
            sql = f"""
                UPDATE students
                SET {", ".join(update_fields)}
                WHERE id = :student_id AND owner_id = :owner_id AND library_id = :lib_id
            """
            result = conn.execute(text(sql), params)
            if result.rowcount == 0:
                return {"error": f"Student ID {student_id} not found."}

        return {"success": True, "message": f"Student ID {student_id} updated successfully."}
    except Exception as e:
        return {"error": str(e)}


async def delete_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int | None = None,
) -> dict:
    """Delete a student by student_id from a library."""
    try:
        owner_id, lib_id = _get_owner_and_library_id(tool_context, library_id)

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM students
                    WHERE id = :student_id AND owner_id = :owner_id AND library_id = :lib_id
                """),
                {"student_id": student_id, "owner_id": owner_id, "lib_id": lib_id},
            )
            if result.rowcount == 0:
                return {"error": f"Student ID {student_id} not found."}

        return {"success": True, "message": f"Student ID {student_id} deleted successfully."}
    except Exception as e:
        return {"error": str(e)}
