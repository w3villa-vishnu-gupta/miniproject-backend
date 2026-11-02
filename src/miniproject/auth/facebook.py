import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from sqlalchemy import text

from miniproject.auth.auth import ALGORITHM, SECRET_KEY
from miniproject.connections.db import engine
from miniproject.services.email_service import send_login_notification_email

router = APIRouter(prefix="/auth/facebook", tags=["authentication"])

password_hash = PasswordHash.recommended()

FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")
FACEBOOK_CALLBACK_URL = os.getenv(
    "FACEBOOK_CALLBACK_URL",
    "http://localhost:8001/auth/facebook/callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173/").rstrip("/")

FACEBOOK_AUTHORIZE_URL = "https://www.facebook.com/v24.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v24.0/oauth/access_token"
FACEBOOK_PROFILE_URL = "https://graph.facebook.com/me"


@router.get("")
def login_with_facebook():
    """
    Step 1: Redirect the user to Facebook's OAuth consent screen.
    We sign a temporary JWT state token to protect against CSRF attacks.
    """
    state_token = jwt.encode(
        {
            "nonce": secrets.token_urlsafe(32),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    query_params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": FACEBOOK_CALLBACK_URL,
        "scope": "email,public_profile",
        "response_type": "code",
        "state": state_token,
    }

    login_url = f"{FACEBOOK_AUTHORIZE_URL}?{urlencode(query_params)}"
    return RedirectResponse(login_url)


@router.get("/callback")
async def facebook_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """
    Step 2: Facebook redirects back here with authorization code and state.
    We exchange the code for an access token, fetch profile details,
    find or create the corresponding library owner, and redirect to the frontend.
    """
    # If the user cancelled or Facebook returned an error, redirect to login page with message
    if error or not code or not state:
        redirect_err = f"{FRONTEND_URL}/login?error=facebook_cancelled"
        return RedirectResponse(redirect_err)

    # Validate state JWT to prevent CSRF attacks
    try:
        jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=invalid_state")

    # Exchange authorization code for Facebook access token
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.get(
            FACEBOOK_TOKEN_URL,
            params={
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "redirect_uri": FACEBOOK_CALLBACK_URL,
                "code": code,
            },
        )

        if token_response.is_error:
            return RedirectResponse(f"{FRONTEND_URL}/login?error=facebook_token_failed")

        access_token = token_response.json().get("access_token")
        if not access_token:
            return RedirectResponse(f"{FRONTEND_URL}/login?error=no_access_token")

        # Fetch basic profile details from Facebook Graph API
        profile_response = await client.get(
            FACEBOOK_PROFILE_URL,
            params={
                "fields": "id,name,email",
                "access_token": access_token,
            },
        )

        if profile_response.is_error:
            return RedirectResponse(f"{FRONTEND_URL}/login?error=facebook_profile_failed")

        profile = profile_response.json()

    facebook_id = str(profile.get("id"))
    name = profile.get("name") or "Facebook User"
    # Some Facebook accounts lack an email address (e.g. phone-number signups).
    # Provide a consistent fallback email in that scenario so the account can still be created.
    email = profile.get("email") or f"fb_{facebook_id}@facebook.user"

    # Find existing library owner or register a new one
    with engine.begin() as conn:
        existing_owner = conn.execute(
            text("""
                SELECT id, name, email, facebook_id
                FROM owners
                WHERE facebook_id = :facebook_id OR email = :email
                LIMIT 1
            """),
            {
                "facebook_id": facebook_id,
                "email": email,
            },
        ).mappings().first()

        if existing_owner:
            owner_id = existing_owner["id"]
            # Link facebook_id if it was previously registered via email
            if not existing_owner.get("facebook_id"):
                conn.execute(
                    text("""
                        UPDATE owners
                        SET facebook_id = :facebook_id
                        WHERE id = :owner_id
                    """),
                    {
                        "facebook_id": facebook_id,
                        "owner_id": owner_id,
                    },
                )
        else:
            # Create a brand new library owner account
            owner_id = conn.execute(
                text("""
                    INSERT INTO owners
                        (name, email, password_hash, facebook_id, phone)
                    VALUES
                        (:name, :email, :password_hash, :facebook_id, :phone)
                    RETURNING id
                """),
                {
                    "name": name,
                    "email": email,
                    "password_hash": password_hash.hash(secrets.token_urlsafe(32)),
                    "facebook_id": facebook_id,
                    "phone": "",
                },
            ).scalar_one()

    # Create our application's JWT session token for the library owner
    app_token = jwt.encode(
        {
            "sub": str(owner_id),
            "type": "owner",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    if email and "@facebook.user" not in email:
        send_login_notification_email(
            to_email=email,
            name=name or "",
            method="Facebook",
        )

    # Redirect to the frontend application with the session token
    redirect_params = {
        "access_token": app_token,
        "token_type": "bearer",
    }
    redirect_url = f"{FRONTEND_URL}/create-library?{urlencode(redirect_params)}"
    return RedirectResponse(redirect_url)






