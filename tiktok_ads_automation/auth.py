"""
הרשאת OAuth מול TikTok Marketing API (נפרד לגמרי מ-auth.py של tiktok_automation -
זו אפליקציית Marketing API, לא Content Posting API).

זרימה חד-פעמית:
  1. python main.py authorize   -> מדפיס קישור, פותחים בדפדפן ומאשרים גישה לחשבון המפרסם
  2. TikTok מפנה ל-config.REDIRECT_URI עם ?auth_code=...  (מודבק ידנית בטרמינל)
  3. הקוד מוחלף בטוקן גישה (access_token) - נשמר בקובץ tiktok_ads_tokens.json.
     בשונה מ-Content Posting API, טוקן זה ארוך-טווח ואין בו refresh_token - הוא נשאר
     תקף עד שמבטלים אותו ידנית ב-Business Center.
"""

import json
import urllib.parse
from pathlib import Path

import requests

import config

AUTH_PORTAL_URL = "https://business-api.tiktok.com/portal/auth"
TOKEN_FILE = "./tiktok_ads_tokens.json"


def build_authorize_url(state: str = "tiktok_ads_automation") -> str:
    params = {
        "app_id": config.APP_ID,
        "state": state,
        "redirect_uri": config.REDIRECT_URI,
    }
    return f"{AUTH_PORTAL_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(auth_code: str) -> dict:
    """מחליף auth_code שהתקבל מ-TikTok בטוקן גישה, ושומר לקובץ."""
    resp = requests.post(
        f"{config.API_BASE_URL}/oauth2/access_token/",
        headers={"Content-Type": "application/json"},
        json={
            "app_id": config.APP_ID,
            "secret": config.APP_SECRET,
            "auth_code": auth_code,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהחלפת auth_code בטוקן: {data}")
    Path(TOKEN_FILE).write_text(json.dumps(data["data"], ensure_ascii=False, indent=2), encoding="utf-8")
    return data["data"]
