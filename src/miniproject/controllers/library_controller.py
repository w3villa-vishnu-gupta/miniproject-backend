from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from miniproject.auth.auth import get_current_owner
from miniproject.connections.db import engine
from miniproject.schemas.Library import LibraryCreate

router = APIRouter(tags=["libraries"])


@router.get("/libraries")
def get_owner_libraries(
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    with engine.connect() as connection:
        libraries = connection.execute(
            text("""
                SELECT id, name, address, latitude, longitude, created_at
                FROM libraries
                WHERE owner_id = :owner_id
                ORDER BY created_at DESC, id DESC
            """),
            {"owner_id": owner_id},
        ).mappings().all()

    return [dict(lib) for lib in libraries]


@router.post("/libraries")
@router.post("/createaccount/addlibrary")
def add_library(
    data: LibraryCreate,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    library_name = data.name.strip()
    if not library_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Library name cannot be blank",
        )

    with engine.begin() as connection:
        # Check if library name already exists for this owner
        checkif_exists = connection.execute(
            text("""
                SELECT id FROM libraries 
                WHERE owner_id = :owner_id AND LOWER(name) = LOWER(:library_name)
            """),
            {
                "owner_id": owner_id,
                "library_name": library_name,
            },
        ).fetchone()

        if checkif_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A library named '{library_name}' already exists in your account.",
            )

        result = connection.execute(
            text("""
                INSERT INTO libraries (owner_id, name, address, latitude, longitude)
                VALUES (:owner_id, :library_name, :address, :latitude, :longitude)
                RETURNING id, name, address, created_at
            """),
            {
                "owner_id": owner_id,
                "library_name": library_name,
                "address": data.address,
                "latitude": data.latitude,
                "longitude": data.longitude,
            },
        )
        new_lib = result.mappings().one()

    return {
        "message": f"Library '{library_name}' created successfully",
        "library_id": new_lib["id"],
        "library": dict(new_lib),
    }
