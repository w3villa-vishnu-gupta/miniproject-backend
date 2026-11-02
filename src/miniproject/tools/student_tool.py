import os
import httpx
from google.adk.tools import ToolContext

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")


async def get_all_students(
    tool_context: ToolContext,
    library_id: int | None = None,
) -> dict:
    """Fetch all students from the system, optionally filtered by library_id."""
    token = tool_context.state.get("access_token")
    if not token:
        return {"error": "Authentication token is missing."}

    params = {}
    if library_id is not None:
        params["library_id"] = library_id

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/getallstudents",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if response.status_code == 401:
        return {"error": "Authentication failed or token expired."}

    response.raise_for_status()
    return response.json()


async def get_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int | None = None,
) -> dict:
    """Fetch a single student by student_id."""
    token = tool_context.state.get("access_token")
    if not token:
        return {"error": "Authentication token is missing."}

    params = {}
    if library_id is not None:
        params["library_id"] = library_id

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/students/{student_id}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    if response.status_code == 422:
        print("Validation error:", response.json())

    response.raise_for_status()
    if response.status_code == 401:
        return {"error": "Authentication failed or token expired."}

    response.raise_for_status()
    return response.json()


async def add_student(
    tool_context: ToolContext,
    name: str,
    phone: str,
    library_id: int,
    email: str | None = None,
    address: str | None = None,
    payment_start_month: str | None = None,
) -> dict:
    """
    Register a new student in the library system.

    Args:
        tool_context: Context containing the authenticated user's state.
        name: Student's full name.
        phone: Student's phone number, passed as a string.
        library_id: Integer ID of the library where the student will register.
        email: Student's email address, if provided.
        address: Student's address, if provided.
        payment_start_month: Payment start date in YYYY-MM-DD format,
            if provided.
    """
    token = tool_context.state.get("access_token")
    if not token:
        return {"error": "Authentication token is missing."}

    payload = {
        "name": name,
        "phone": phone,
        "library_id": library_id,
        "email": email,
        "address": address,
        "payment_start_month": payment_start_month,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/createaccount/addstudent",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if response.status_code == 401:
        return {"error": "Authentication failed or token expired."}

    response.raise_for_status()
    return response.json()


async def update_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    status: str | None = None,
    alumini: bool | None = None,
) -> dict:
    """Update student information."""
    token = tool_context.state.get("access_token")
    if not token:
        return {"error": "Authentication token is missing."}

    payload = {}
    if name is not None:
        payload["name"] = name
    if phone is not None:
        payload["phone"] = phone
    if email is not None:
        payload["email"] = email
    if address is not None:
        payload["address"] = address
    if status is not None:
        payload["status"] = status
    if alumini is not None:
        payload["alumini"] = alumini

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{BASE_URL}/students/{student_id}",
            params={"library_id": library_id},
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if response.status_code == 401:
        return {"error": "Authentication failed or token expired."}

    response.raise_for_status()
    return response.json()


async def delete_student(
    tool_context: ToolContext,
    student_id: int,
    library_id: int,
) -> dict:
    """Delete a student by student_id from a library."""
    token = tool_context.state.get("access_token")
    if not token:
        return {"error": "Authentication token is missing."}

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}/students/{student_id}",
            params={"library_id": library_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if response.status_code == 401:
        return {"error": "Authentication failed or token expired."}

    response.raise_for_status()
    return response.json()
