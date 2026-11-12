from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import text

from miniproject.auth.auth import get_current_owner
from miniproject.connections.db import engine
from miniproject.schemas.student import Student

router = APIRouter(tags=["students"])


@router.post("/createaccount/addstudent")
def addstudent(
    stu_data: Student,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]

    with engine.begin() as connection:
        checkmailexists = connection.execute(
            text("""
                SELECT id FROM students 
                WHERE owner_id = :owner_id AND LOWER(email) = LOWER(:email)
            """),
            {
                "owner_id": owner_id,
                "email": stu_data.email,
            },
        ).fetchone()

        if checkmailexists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student with this mail already exists",
            )

        result = connection.execute(
            text("""
                INSERT INTO students (owner_id, library_id, name, email, phone, address, payment_start_month, last_payment_date)
                SELECT :owner_id, libraries.id, :name, :email, :phone, :address, :payment_start_month, :last_payment_date
                FROM libraries
                WHERE libraries.id = :library_id
                  AND libraries.owner_id = :owner_id
                RETURNING id
            """),
            {
                "owner_id": owner_id,
                "library_id": stu_data.library_id,
                "name": stu_data.name,
                "email": stu_data.email,
                "phone": stu_data.phone,
                "address": stu_data.address,
                "payment_start_month": stu_data.payment_start_month,
                "last_payment_date": stu_data.last_payment_date,
            },
        )

        student_id = result.scalar_one_or_none()
        if student_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found for this owner",
            )

    return {
        "message": f"Student '{stu_data.name}' added successfully",
        "student_id": student_id,
        "library_id": stu_data.library_id,
    }


@router.get("/getallstudents")
def get_all_students(
    library_id: int | None = None,
    page: int | None = None,
    limit: int = 10,
    search: str | None = None,
    alumini: bool | None = None,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]

    with engine.connect() as connection:
        if library_id is not None:
            library = connection.execute(
                text("""
                    SELECT id
                    FROM libraries
                    WHERE id = :library_id AND owner_id = :owner_id
                """),
                {"library_id": library_id, "owner_id": owner_id},
            ).first()
            if library is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Library not found for this owner",
                )

        where_clauses = ["students.owner_id = :owner_id"]
        params: dict = {"owner_id": owner_id}

        if library_id is not None:
            where_clauses.append("students.library_id = :library_id")
            params["library_id"] = library_id

        if alumini is True:
            where_clauses.append("students.alumini = TRUE")
        elif alumini is False:
            where_clauses.append("(students.alumini IS NULL OR students.alumini = FALSE)")

        if search and search.strip():
            where_clauses.append(
                "("
                "students.name ILIKE :search "
                "OR COALESCE(students.email, '') ILIKE :search "
                "OR COALESCE(students.phone, '') ILIKE :search "
                "OR COALESCE(students.address, '') ILIKE :search "
                "OR COALESCE(students.status, '') ILIKE :search"
                ")"
            )
            params["search"] = f"%{search.strip()}%"

        where_sql = " AND ".join(where_clauses)

        # Backwards-compatible: return plain list if page is not specified
        if page is None:
            result = connection.execute(
                text(f"""
                    SELECT students.id, students.name, students.email, students.phone,
                           students.address, students.library_id, students.alumini,
                           students.status, students.payment_start_month,
                           students.last_payment_date
                    FROM students
                    WHERE {where_sql}
                    ORDER BY students.id DESC
                """),
                params,
            )
            return result.mappings().all()

        # Server-side pagination when page is specified
        page = max(1, page)
        limit = max(1, min(100, limit))
        offset = (page - 1) * limit

        total = connection.execute(
            text(f"SELECT COUNT(*) FROM students WHERE {where_sql}"),
            params,
        ).scalar_one()

        total_pages = max(1, (total + limit - 1) // limit)
        if page > total_pages:
            page = total_pages
            offset = (page - 1) * limit

        paginated_params = {**params, "limit": limit, "offset": offset}
        rows = connection.execute(
            text(f"""
                SELECT students.id, students.name, students.email, students.phone,
                       students.address, students.library_id, students.alumini,
                       students.status, students.payment_start_month,
                       students.last_payment_date
                FROM students
                WHERE {where_sql}
                ORDER BY students.id DESC
                LIMIT :limit OFFSET :offset
            """),
            paginated_params,
        ).mappings().all()

        return {
            "students": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }


@router.patch("/students/{student_id}")
def update_student_info(
    student_id: int,
    library_id: int,
    student: dict = Body(...),
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]

    with engine.begin() as connection:
        result = connection.execute(
            text("""
                UPDATE students
                SET name = :name,
                    email = :email,
                    phone = :phone,
                    address = :address,
                    status = :status,
                    alumini = :alumini,
                    payment_start_month = COALESCE(:payment_start_month, payment_start_month),
                    last_payment_date = COALESCE(:last_payment_date, last_payment_date)
                WHERE id = :student_id
                  AND owner_id = :owner_id
                  AND library_id = :library_id
            """),
            {
                "name": student["name"],
                "email": student["email"],
                "phone": student["phone"],
                "address": student["address"],
                "status": student["status"],
                "alumini": student["alumini"],
                "payment_start_month": student.get("payment_start_month"),
                "last_payment_date": student.get("last_payment_date"),
                "student_id": student_id,
                "owner_id": owner_id,
                "library_id": library_id,
            },
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found for this owner and library",
            )

        return {"message": "Student information updated successfully"}


@router.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    with engine.begin() as connection:
        result = connection.execute(
            text("""DELETE FROM students
                  WHERE id = :student_id AND owner_id = :owner_id AND library_id = :library_id"""),
            {"student_id": student_id, "owner_id": current_owner["owner_id"], "library_id": library_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found for this owner and library")
    return {"message": "Student deleted successfully"}


@router.get("/students/{student_id}")
def get_student(
    student_id: int,
    library_id: int,
    current_owner: dict = Depends(get_current_owner),
):
    with engine.begin() as connection:
        result = connection.execute(
            text("""SELECT * FROM students
                  WHERE id = :student_id AND owner_id = :owner_id AND library_id = :library_id"""),
            {"student_id": student_id, "owner_id": current_owner["owner_id"], "library_id": library_id},
        )
        student = result.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student
