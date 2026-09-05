"""
הרשאת OAuth מול TikTok for Developers (Content Posting API).

זרימה חד-פעמית:
  1. python main.py authorize   -> מדפיס קישור, פותחים בדפדפן ומאשרים
  2. TikTok מפנה ל-config.REDIRECT_URI עם ?code=...  (מודבק ידנית בטרמינל)
  3. הקוד מוחלף בטוקן גישה (access_token) + טוקן רענון (refresh_token), נשמרים
     בקובץ config.TOKEN_FILE

אחרי זה, get_valid_access_token() דואג לרענן אוטומטית טוקן שפג.
"""

import json
import time
import urllib.parse
from pathlib import Path

import requests

import config


def build_authorize_url(state: str = "tiktok_automation") -> str:
    params = {
        "client_key": config.CLIENT_KEY,
        "scope": config.SCOPES,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "state": state,
    }
    return f"{config.AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"


def _save_tokens(data: dict) -> None:
    data = {**data, "saved_at": int(time.time())}
    Path(config.TOKEN_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_tokens() -> dict:
    path = Path(config.TOKEN_FILE)
    if not path.exists():
        raise RuntimeError(
            "אין טוקן שמור. יש להריץ קודם: python main.py authorize"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def exchange_code_for_token(code: str) -> dict:
    """מחליף authorization code שהתקבל מ-TikTok בטוקן גישה, ושומר לקובץ."""
    resp = requests.post(
        f"{config.API_BASE_URL}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.CLIENT_KEY,
            "client_secret": config.CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config.REDIRECT_URI,
        },
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"נכשל בהחלפת קוד הרשאה בטוקן: {data}")
    _save_tokens(data)
    return data


def _refresh(refresh_token: str) -> dict:
    resp = requests.post(
        f"{config.API_BASE_URL}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.CLIENT_KEY,
            "client_secret": config.CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"נכשל ברענון טוקן: {data}")
    _save_tokens(data)
    return data


def get_valid_access_token() -> str:
    """מחזיר access_token תקף, ומרענן אותו אוטומטית אם פג (עם מרווח בטיחות של 60 שניות)."""
    tokens = _load_tokens()
    expires_at = tokens["saved_at"] + int(tokens.get("expires_in", 0))
    if time.time() >= expires_at - 60:
        tokens = _refresh(tokens["refresh_token"])
    return tokens["access_token"]
