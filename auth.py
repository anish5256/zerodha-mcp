#!/usr/bin/env python
# coding: utf-8
"""
Zerodha enctoken generator — adapted from Vicennial Technologies/enclogin_sinbad.py
Logs in via Zerodha API (no browser needed) using password + TOTP.
"""

import os
import requests
import pyotp
from pathlib import Path

# ── Credentials (from environment variables) ─────────────────────────────────
USER_ID  = os.environ.get("ZERODHA_USER_ID")
PASSWORD = os.environ.get("ZERODHA_PASSWORD")
TOTP_KEY = os.environ.get("ZERODHA_TOTP_KEY")

if not all([USER_ID, PASSWORD, TOTP_KEY]):
    raise ValueError(
        "Missing Zerodha credentials. Set environment variables:\n"
        "  ZERODHA_USER_ID, ZERODHA_PASSWORD, ZERODHA_TOTP_KEY"
    )

TOKEN_FILE = Path(__file__).parent / "zerodha_enctoken.txt"

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
}


def enc_verify(enctoken: str) -> bool:
    """Check if existing enctoken is still valid."""
    url = "https://kite.zerodha.com/oms/user/margins"
    r = requests.get(url, headers={"authorization": enctoken}, timeout=10).json()
    return r.get("status") == "success"


def generate_enctoken(user_id: str, password: str, totp_key: str) -> str:
    """
    Full Zerodha login flow → returns enctoken string.
    Adapted from enclogin_sinbad.py :: new_enc()
    """
    # Step 1: password login
    r = requests.post(
        "https://api.kite.trade/api/login",
        data={"user_id": user_id, "password": password},
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    resp = r.json()
    if resp.get("status") == "error":
        raise RuntimeError(f"Login failed: {resp.get('message')}")

    request_id = resp["data"]["request_id"]
    kf_session  = r.cookies.get_dict()["kf_session"]

    # Step 2: TOTP two-factor
    twofa_value = pyotp.TOTP(totp_key).now()
    headers2 = {
        **HEADERS,
        "cookie":        f"kf_session={kf_session}",
        "x-kite-userid": user_id,
        "x-kite-version": "2.9.3",
    }
    try:
        r2 = requests.post(
            "https://kite.zerodha.com/api/twofa",
            data={"user_id": user_id, "request_id": request_id, "twofa_value": twofa_value},
            headers=headers2,
            timeout=15,
        )
        cookies = r2.cookies.get_dict()
    except Exception:
        r2 = requests.post(
            "https://api.kite.trade/api/twofa",
            data={"user_id": user_id, "request_id": request_id, "twofa_value": twofa_value},
            headers=headers2,
            timeout=15,
        )
        cookies = r2.cookies.get_dict()

    raw_token = cookies["enctoken"]
    enctoken   = f"enctoken {raw_token}"
    return enctoken


def get_enctoken() -> str:
    """
    Return a valid enctoken — uses cached file if still valid,
    otherwise generates a fresh one.
    """
    # Check cached token
    if TOKEN_FILE.exists():
        cached = TOKEN_FILE.read_text().strip()
        if enc_verify(cached):
            print(f"Cached enctoken still valid: {cached[:40]}...")
            return cached

    # Generate new token
    print("Generating new Zerodha enctoken ...")
    token = generate_enctoken(USER_ID, PASSWORD, TOTP_KEY)
    TOKEN_FILE.write_text(token)
    print(f"New enctoken saved: {token[:40]}...")
    return token


CONSOLE_TOKEN_FILE = Path(__file__).parent / "zerodha_console_token.txt"


def get_public_token(user_id: str = None, password: str = None, pin: str = None):
    """
    Logs into Zerodha Console and returns (public_token, session).
    pin can be a 6-digit TOTP secret (will auto-generate OTP) or a plain 6-digit PIN.
    """
    user_id = user_id or USER_ID
    password = password or PASSWORD
    pin = pin or TOTP_KEY

    # Use a Session to properly persist cookies through redirects
    s = requests.Session()
    s.headers.update({"user-agent": HEADERS["user-agent"]})

    # Step 1: Go to console login to get session URL
    tp = s.get("https://console.zerodha.com/kite/login", allow_redirects=True)
    session_url = tp.url

    # Step 2: Login with password
    r = s.post(
        "https://kite.zerodha.com/api/login",
        data={"user_id": user_id, "password": password},
        headers={"x-kite-version": "2.9.3"},
    )
    resp = r.json()
    if resp.get("status") == "error":
        raise RuntimeError(f"Login failed: {resp.get('message')}")
    request_id = resp["data"]["request_id"]

    # Step 3: 2FA - Generate TOTP if pin is longer than 6 chars
    if len(str(pin)) > 6:
        pin = pyotp.TOTP(pin).now()

    s.post(
        "https://kite.zerodha.com/api/twofa",
        data={"user_id": user_id, "request_id": request_id, "twofa_value": pin},
        headers={
            "x-kite-userid": user_id,
            "x-kite-version": "2.9.3",
            "referer": session_url,
        },
    )

    # Step 4: Follow redirect to console to get session cookie
    s.get(session_url + "&skip_session=true", allow_redirects=True)

    # Extract tokens from session cookies
    public_token = s.cookies.get("public_token", "")
    session = s.cookies.get("session", domain="console.zerodha.com") or ""

    return public_token, session


def _verify_console_token(public_token: str, session: str) -> bool:
    """Check if console tokens are still valid by making a simple API call."""
    headers = {
        "user-agent": HEADERS["user-agent"],
        "cookie": f"public_token={public_token}; session={session};",
        "x-csrftoken": public_token,
    }
    try:
        # Use reports API for verification - it's one of the few that returns JSON
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        r = requests.get(
            f"https://console.zerodha.com/api/reports/pnl/summary?segment=FO&from_date={today}&to_date={today}",
            headers=headers,
            timeout=10
        )
        data = r.json()
        return data.get("status") == "success"
    except Exception:
        return False


def get_console_tokens() -> tuple[str, str]:
    """
    Return valid console tokens (public_token, session).
    Uses cached file if still valid, otherwise generates fresh ones.
    """
    # Check cached tokens
    if CONSOLE_TOKEN_FILE.exists():
        cached = CONSOLE_TOKEN_FILE.read_text().strip()
        if "," in cached:
            public_token, session = cached.split(",", 1)
            if _verify_console_token(public_token, session):
                print(f"Cached console token still valid: {public_token[:20]}...")
                return public_token, session

    # Generate new tokens
    print("Generating new Zerodha console tokens ...")
    public_token, session = get_public_token()
    CONSOLE_TOKEN_FILE.write_text(f"{public_token},{session}")
    print(f"New console tokens saved: {public_token[:20]}...")
    return public_token, session


if __name__ == "__main__":
    token = get_enctoken()
    print(f"\nEnctoken: {token}")

    print("\nConsole tokens:")
    public_token, session = get_console_tokens()
    print(f"public_token: {public_token}")
    print(f"session: {session}")
