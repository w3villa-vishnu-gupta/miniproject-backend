
import os
import secrets
import hashlib
import base64

from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
import httpx
import jwt

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse

from pwdlib import PasswordHash
from sqlalchemy import text

from miniproject.auth.auth import ALGORITHM, SECRET_KEY
from miniproject.connections.db import engine
from miniproject.services.email_service import send_login_notification_email

password_hash = PasswordHash.recommended()
router = APIRouter(prefix="/auth/google", tags=["authentication"])


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
GOOGLE_AUTH_URL = os.environ.get("GOOGLE_AUTH_URL")


GOOGLE_CALLBACK_URL = os.getenv(
    "GOOGLE_CALLBACK_URL",
    "http://localhost:8001/auth/google/callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://library-hub-w3villa.vercel.app").rstrip("/")


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(
        verifier.encode("ascii")
    ).digest()

    return base64.urlsafe_b64encode(
        digest
    ).decode("ascii").rstrip("=")


@router.get("/login")
async def login(request: Request):
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)

    request.session["oauth_state"] = state
    request.session["oauth_nonce"] = nonce
    request.session["oauth_verifier"] = verifier

    challenge = generate_code_challenge(verifier)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }

    authorization_url = (
        f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    )

    return RedirectResponse(
        url=authorization_url,
        status_code=302
    )


@router.get("/callback")
async def callback(request: Request):

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    saved_state = request.session.get("oauth_state")
    verifier = request.session.get("oauth_verifier")
    nonce = request.session.get("oauth_nonce")

    print("Received state:", state)
    print("Saved state:", saved_state)
    print("Verifier exists:", bool(verifier))
    print("Nonce exists:", bool(nonce))

    if not saved_state or state != saved_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter"
        )

    if not code or not verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing authorization code or verifier"
        )

    async with httpx.AsyncClient() as client:

        # Exchange authorization code for tokens
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "code_verifier": verifier,
            },
        )

        print("Token response status:", token_response.status_code)

        if token_response.status_code != 200:
            print("Token error:", token_response.text)
            raise HTTPException(
                status_code=400,
                detail="Token exchange failed"
            )

        tokens = token_response.json()

        # Fetch Google user profile
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}"
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to fetch Google user profile"
            )

        user_info = user_response.json()

    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")
    google_id = user_info.get("id")

    print("Email:", email)
    print("Name:", name)
    print("Picture:", picture)
    print("Google ID:", google_id)

    print("Received token keys:", list(tokens.keys()))
    
         # Find existing library owner or register a new one
    with engine.begin() as conn:
        existing_owner = conn.execute(
            text("""
                SELECT id, name, email, google_id
                FROM owners
                WHERE google_id = :google_id OR email = :email
                LIMIT 1
            """),
            {
                "google_id": google_id,
                "email": email,
            },
        ).mappings().first()

        if existing_owner:
            owner_id = existing_owner["id"]
            # Link google_id if the owner was previously registered by email
            if not existing_owner.get("google_id"):
                conn.execute(
                    text("""
                        UPDATE owners
                        SET google_id = :google_id
                        WHERE id = :owner_id
                    """),
                    {
                        "google_id": google_id,
                        "owner_id": owner_id,
                    },
                )
        else:
            owner_id = conn.execute(
                text("""
                    INSERT INTO owners
                        (name, email, password_hash, google_id, phone)
                    VALUES
                        (:name, :email, :password_hash, :google_id, :phone)
                    RETURNING id
                """),
                {
                    "name": name,
                    "email": email,
                    "password_hash": password_hash.hash(secrets.token_urlsafe(32)),
                    "google_id": google_id,
                    "phone": "",
                },
            ).scalar_one()

    app_token = jwt.encode(
        {
            "sub": str(owner_id),
            "type": "owner",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    if email:
        send_login_notification_email(
            to_email=email,
            name=name or "",
            method="Google",
        )

    # Redirect to the frontend application with the session token
    redirect_params = {
        "access_token": app_token,
        "token_type": "bearer",
    }
    redirect_url = f"{FRONTEND_URL}/create-library?{urlencode(redirect_params)}"
    return RedirectResponse(redirect_url)