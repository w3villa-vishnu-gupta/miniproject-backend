import os
from datetime import timedelta
from io import BytesIO
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import RedirectResponse
from PIL import Image
from pydantic import BaseModel
from pwdlib import PasswordHash
from sqlalchemy import text

from miniproject.auth.auth import (
    create_access_token,
    get_current_owner,
    create_magic_token,
    verify_magic_token,
)
from miniproject.connections.db import engine
from miniproject.schemas.login import LoginRequest
from miniproject.schemas.Owner import Owner
from miniproject.services import storj
from miniproject.services.email_service import (
    send_magic_link_email,
    send_login_notification_email,
)

router = APIRouter(tags=["authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = 30
password_hash = PasswordHash.recommended()


class MagicLinkRequest(BaseModel):
    email: str
    name: str | None = None
    phone: str | None = None
    password: str | None = None


class MagicLinkConfirmRequest(BaseModel):
    token: str


class OwnerProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    userlocation: str | None = None
    library_id: int | None = None
    avatar_url: str | None = None


@router.post("/auth/magic-link")
def request_magic_link(data: MagicLinkRequest):
    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    with engine.connect() as connection:
        existing_owner = connection.execute(
            text("SELECT id, name, email, phone FROM owners WHERE email = :email"),
            {"email": email},
        ).mappings().first()

    name = data.name.strip() if data.name else (existing_owner["name"] if existing_owner else "Library Owner")
    phone = data.phone.strip() if data.phone else (existing_owner["phone"] if existing_owner else "")
    hashed_password = password_hash.hash(data.password) if data.password else None

    token = create_magic_token({
        "email": email,
        "name": name,
        "phone": phone,
        "password_hash": hashed_password,
    })

    frontend_url = os.getenv("FRONTEND_URL", "https://library-hub-w3villa.vercel.app").rstrip("/")
    magic_url = f"{frontend_url}/auth/magic-callback?token={token}"

    email_sent = send_magic_link_email(
        to_email=email,
        magic_link=magic_url,
        name=name,
    )

    print(f"\n[MAGIC LINK GENERATED] For {email}: {magic_url}\n")

    return {
        "message": f"Magic link has been sent to {email}. Please check your inbox.",
        "email": email,
        "email_sent": email_sent,
        "magic_link": magic_url,
    }


@router.post("/auth/magic-link/confirm")
def confirm_magic_link(data: MagicLinkConfirmRequest):
    payload = verify_magic_token(data.token)
    email = payload.get("email")

    with engine.begin() as connection:
        owner = connection.execute(
            text("SELECT id, name, email, phone, avatar_url, address, latitude, longitude, userlocation FROM owners WHERE email = :email"),
            {"email": email},
        ).mappings().first()

        if owner:
            owner_dict = dict(owner)
            owner_id = owner_dict["id"]
        else:
            hashed = payload.get("password_hash") or password_hash.hash("MagicLink@123")
            res = connection.execute(
                text("""
                    INSERT INTO owners (name, email, phone, password_hash)
                    VALUES (:name, :email, :phone, :password_hash)
                    RETURNING id, name, email, phone, avatar_url, address, latitude, longitude, userlocation
                """),
                {
                    "name": payload.get("name") or "Library Owner",
                    "email": email,
                    "phone": payload.get("phone") or "",
                    "password_hash": hashed,
                },
            ).mappings().first()
            owner_dict = dict(res)
            owner_id = owner_dict["id"]

    access_token = create_access_token(
        {"sub": str(owner_id), "type": "owner"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    send_login_notification_email(
        to_email=email,
        name=owner_dict.get("name", ""),
        method="Magic Link",
    )

    return {
        "message": f"Welcome, {owner_dict.get('name', 'Owner')}! Account verified successfully.",
        "access_token": access_token,
        "token_type": "bearer",
        "owner": owner_dict,
    }


@router.get("/auth/magic-link/callback")
def direct_magic_callback(token: str):
    """Direct backend callback if opened directly from email."""
    try:
        payload = verify_magic_token(token)
        email = payload.get("email")

        with engine.begin() as connection:
            owner = connection.execute(
                text("SELECT id, name, email, phone FROM owners WHERE email = :email"),
                {"email": email},
            ).mappings().first()

            if owner:
                owner_id = owner["id"]
            else:
                hashed = payload.get("password_hash") or password_hash.hash("MagicLink@123")
                res = connection.execute(
                    text("""
                        INSERT INTO owners (name, email, phone, password_hash)
                        VALUES (:name, :email, :phone, :password_hash)
                        RETURNING id
                    """),
                    {
                        "name": payload.get("name") or "Library Owner",
                        "email": email,
                        "phone": payload.get("phone") or "",
                        "password_hash": hashed,
                    },
                ).mappings().first()
                owner_id = res["id"]

        access_token = create_access_token(
            {"sub": str(owner_id), "type": "owner"},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        send_login_notification_email(
            to_email=email,
            name=(owner["name"] if owner else payload.get("name")) or "",
            method="Magic Link",
        )
        frontend_url = os.getenv("FRONTEND_URL", "https://library-hub-w3villa.vercel.app").rstrip("/")
        return RedirectResponse(
            url=f"{frontend_url}/create-library?access_token={access_token}",
            status_code=302,
        )
    except Exception as e:
        frontend_url = os.getenv("FRONTEND_URL", "https://library-hub-w3villa.vercel.app").rstrip("/")
        return RedirectResponse(
            url=f"{frontend_url}/login?error={quote(str(e))}",
            status_code=302,
        )


@router.post("/createaccount")
def create_account(owner: Owner):
    with engine.begin() as connection:
        existing_owner = connection.execute(
            text("SELECT id FROM owners WHERE email = :email"),
            {"email": owner.email},
        ).first()

        if existing_owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists. Please sign in instead.",
            )

        hashed_password = password_hash.hash(owner.password)

        result = connection.execute(
            text("""
                INSERT INTO owners (name, email, phone, password_hash)
                VALUES (:name, :email, :phone, :password_hash)
                RETURNING id
            """),
            {
                "name": owner.name,
                "email": owner.email,
                "phone": owner.phone,
                "password_hash": hashed_password,
            },
        )
        owner_id = result.scalar_one()

    access_token = create_access_token(
        {"sub": str(owner_id), "type": "owner"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    send_login_notification_email(
        to_email=owner.email,
        name=owner.name or "",
        method="Email & Password",
    )

    return {
        "message": f"Account created successfully for {owner.name}",
        "access_token": access_token,
        "token_type": "bearer",
        "owner": {
            "id": owner_id,
            "name": owner.name,
            "email": owner.email,
            "phone": owner.phone,
        },
    }


@router.post("/login")
def login(owner_credentials: LoginRequest):
    with engine.connect() as connection:
        owner = connection.execute(
            text("""
                SELECT id, name, email, phone, password_hash, avatar_url, address, latitude, longitude, userlocation
                FROM owners
                WHERE email = :email
            """),
            {"email": owner_credentials.email},
        ).mappings().first()

        if owner is None or not password_hash.verify(
            owner_credentials.password,
            owner["password_hash"],
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        libraries = connection.execute(
            text("""
                SELECT id, name
                FROM libraries
                WHERE owner_id = :owner_id
                ORDER BY id
            """),
            {"owner_id": owner["id"]},
        ).mappings().all()

    access_token = create_access_token(
        {"sub": str(owner["id"]), "type": "owner"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    send_login_notification_email(
        to_email=owner["email"],
        name=owner.get("name", ""),
        method="Email & Password",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "owner": {
            "id": owner["id"],
            "name": owner["name"],
            "email": owner["email"],
            "phone": owner["phone"],
            "avatar_url": owner.get("avatar_url"),
            "address": owner.get("address"),
            "latitude": owner.get("latitude"),
            "longitude": owner.get("longitude"),
            "userlocation": owner.get("userlocation"),
        },
        "libraries": [{"id": library["id"], "name": library["name"]} for library in libraries],
    }


@router.get("/getallowners")
def get_all_owners():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id, name, email, phone FROM owners")
        )
        return result.mappings().all()


@router.get("/getownerdata")
def get_owner_data(
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id, name, email, phone, created_at, avatar_url, address, latitude, longitude, userlocation FROM owners WHERE id = :owner_id"),
            {"owner_id": owner_id},
        )
        owner_data = result.mappings().first()
        if not owner_data:
            raise HTTPException(status_code=404, detail="Owner not found")

    return dict(owner_data)


@router.put("/updateownerdata")
@router.patch("/updateownerdata")
def update_owner_data(
    data: OwnerProfileUpdate,
    current_owner: dict = Depends(get_current_owner),
):
    owner_id = current_owner["owner_id"]
    updates = []
    params = {"owner_id": owner_id}

    if data.name is not None and data.name.strip():
        updates.append("name = :name")
        params["name"] = data.name.strip()

    if data.phone is not None:
        updates.append("phone = :phone")
        params["phone"] = data.phone.strip()

    if data.email is not None and data.email.strip():
        updates.append("email = :email")
        params["email"] = data.email.strip().lower()

    if data.avatar_url is not None:
        updates.append("avatar_url = :avatar_url")
        params["avatar_url"] = data.avatar_url.strip()

    resolved_address = data.address or data.userlocation
    if resolved_address is not None:
        updates.append("address = :address")
        updates.append("userlocation = :address")
        params["address"] = resolved_address.strip()

    if data.latitude is not None:
        updates.append("latitude = :latitude")
        params["latitude"] = data.latitude

    if data.longitude is not None:
        updates.append("longitude = :longitude")
        params["longitude"] = data.longitude

    with engine.begin() as connection:
        if "email" in params:
            existing = connection.execute(
                text("SELECT id FROM owners WHERE email = :email AND id != :owner_id"),
                params,
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This email is already in use by another account",
                )

        if updates:
            query = f"UPDATE owners SET {', '.join(updates)} WHERE id = :owner_id RETURNING id, name, email, phone, created_at, avatar_url, address, latitude, longitude, userlocation"
            result = connection.execute(text(query), params).mappings().first()
        else:
            result = connection.execute(
                text("SELECT id, name, email, phone, created_at, avatar_url, address, latitude, longitude, userlocation FROM owners WHERE id = :owner_id"),
                {"owner_id": owner_id},
            ).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail="Owner not found")

        # Optionally update address & coordinates for current library
        if resolved_address is not None:
            lib_updates = ["address = :lib_address"]
            lib_params = {"lib_address": resolved_address.strip(), "owner_id": owner_id}
            if data.latitude is not None and data.longitude is not None:
                lib_updates.append("latitude = :lib_lat")
                lib_updates.append("longitude = :lib_lng")
                lib_params["lib_lat"] = data.latitude
                lib_params["lib_lng"] = data.longitude

            lib_id = data.library_id
            if lib_id:
                lib_params["lib_id"] = lib_id
                connection.execute(
                    text(f"UPDATE libraries SET {', '.join(lib_updates)} WHERE id = :lib_id AND owner_id = :owner_id"),
                    lib_params,
                )
            else:
                connection.execute(
                    text(f"UPDATE libraries SET {', '.join(lib_updates)} WHERE owner_id = :owner_id"),
                    lib_params,
                )

    return {
        "message": "Profile updated successfully",
        "owner": dict(result),
    }


@router.post("/update-profile-pic")
async def update_profile_pic(
    file: UploadFile = File(...),
    current_owner: dict = Depends(get_current_owner),
    owner_id: int | None = None,
):
    oid = current_owner["owner_id"] if current_owner else owner_id
    try:
        contents = await file.read()

        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Maximum file size is 2 MB"
            )

        image = Image.open(BytesIO(contents))
        image.verify()

        # Generate unique object key
        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        object_key = f"profiles/{uuid4()}.{ext}"

        # Upload image to Storj
        content_type = file.content_type or f"image/{ext}"
        storj.upload_image(contents, object_key, content_type=content_type)
        url = storj.get_image_url(object_key)

        # Update owner's avatar_url in database
        owner_dict = None
        if oid:
            with engine.begin() as connection:
                res = connection.execute(
                    text("UPDATE owners SET avatar_url = :url WHERE id = :owner_id RETURNING id, name, email, phone, created_at, avatar_url"),
                    {"url": url, "owner_id": oid},
                ).mappings().first()
                if res:
                    owner_dict = dict(res)

        return {
            "message": "Profile picture uploaded successfully",
            "object_key": object_key,
            "url": url,
            "owner": owner_dict,
            "filename": file.filename,
            "size": len(contents),
            "content_type": content_type
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Image upload failed: {str(e)}"
        )

    finally:
        await file.close()


@router.get("/profile-pic-url")
def get_profile_pic_url(object_key: str):
    url = storj.get_image_url(object_key)
    return {"object_key": object_key, "url": url}
