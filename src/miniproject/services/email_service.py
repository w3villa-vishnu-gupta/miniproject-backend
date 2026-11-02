import os
from datetime import datetime, timezone
import httpx

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "support@apihub.digital")


def send_magic_link_email(to_email: str, magic_link: str, name: str = "") -> bool:
    """Send a magic login/signup link to the user via Resend."""
    if not to_email:
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    greeting = f"Hello {name}," if name else "Hello,"
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b0d0f; color: #ffffff; padding: 40px 20px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #14161b; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 32px; text-align: center;">
            <div style="display: inline-block; width: 44px; height: 44px; line-height: 44px; border-radius: 12px; background-color: #d5f477; color: #0b0d0f; font-weight: bold; font-size: 22px; margin-bottom: 20px;">L</div>
            <h2 style="color: #ffffff; margin: 0 0 12px 0; font-size: 22px; font-weight: 700;">Sign in to LibraryHub</h2>
            <p style="color: #9ca3af; font-size: 15px; line-height: 1.5; margin: 0 0 24px 0;">
                {greeting}<br/>
                Click the button below to complete your sign-in / registration and access your library workspace.
            </p>
            <a href="{magic_link}" style="display: inline-block; background-color: #d5f477; color: #0b0d0f; font-weight: 700; padding: 14px 28px; border-radius: 12px; text-decoration: none; font-size: 15px;">
                Log In &amp; Activate Account &rarr;
            </a>
            <p style="color: #6b7280; font-size: 12px; margin-top: 28px; line-height: 1.4;">
                This link will expire in 24 hours.<br/>
                If you did not request this email, you can safely ignore it.
            </p>
            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0;" />
            <p style="color: #4b5563; font-size: 11px; word-break: break-all; margin: 0;">
                If the button above does not work, copy and paste this link into your browser:<br/>
                <a href="{magic_link}" style="color: #d5f477;">{magic_link}</a>
            </p>
        </div>
    </div>
    """
    payload = {
        "from": f"LibraryHub <{RESEND_FROM_EMAIL}>",
        "to": [to_email],
        "subject": "Your LibraryHub Magic Login Link",
        "html": html_content,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, headers=headers, json=payload)
            if res.status_code >= 400:
                print(f"[Resend Warning] Status {res.status_code}: {res.text}")
                return False
            print(f"[Resend Success] Email sent to {to_email}: {res.json()}")
            return True
    except Exception as e:
        print(f"[Resend Error] Failed to send email: {e}")
        return False


def send_login_notification_email(to_email: str, name: str = "", method: str = "Password") -> bool:
    """Send a login security alert email via Resend whenever a user logs in."""
    if not to_email or "@facebook.user" in to_email:
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    greeting = f"Hello {name}," if name else "Hello,"
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b0d0f; color: #ffffff; padding: 40px 20px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #14161b; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 32px;">
            <div style="display: inline-block; width: 44px; height: 44px; line-height: 44px; border-radius: 12px; background-color: #d5f477; color: #0b0d0f; font-weight: bold; font-size: 22px; text-align: center; margin-bottom: 20px;">L</div>
            <h2 style="color: #ffffff; margin: 0 0 12px 0; font-size: 20px; font-weight: 700;">New Login to LibraryHub</h2>
            <p style="color: #9ca3af; font-size: 14px; line-height: 1.5; margin: 0 0 20px 0;">
                {greeting}<br/>
                We detected a successful sign-in to your LibraryHub account.
            </p>
            <div style="background-color: #1a1d24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: left;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #9ca3af;"><strong style="color: #ffffff;">Sign-in Method:</strong> {method}</p>
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #9ca3af;"><strong style="color: #ffffff;">Account Email:</strong> {to_email}</p>
                <p style="margin: 0; font-size: 13px; color: #9ca3af;"><strong style="color: #ffffff;">Time:</strong> {now_str}</p>
            </div>
            <p style="color: #9ca3af; font-size: 13px; line-height: 1.5; margin: 0 0 16px 0;">
                If this was you, you can safely disregard this message. If you did not sign in, please secure your account immediately.
            </p>
            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0;" />
            <p style="color: #6b7280; font-size: 11px; margin: 0; text-align: center;">
                © 2026 LibraryHub · Sent from support@apihub.digital
            </p>
        </div>
    </div>
    """
    payload = {
        "from": f"LibraryHub <{RESEND_FROM_EMAIL}>",
        "to": [to_email],
        "subject": f"Security Alert: New Sign-in to LibraryHub ({method})",
        "html": html_content,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, headers=headers, json=payload)
            if res.status_code >= 400:
                print(f"[Resend Warning] Login alert status {res.status_code}: {res.text}")
                return False
            print(f"[Resend Success] Login alert sent to {to_email} ({method})")
            return True
    except Exception as e:
        print(f"[Resend Error] Failed to send login alert: {e}")
        return False
