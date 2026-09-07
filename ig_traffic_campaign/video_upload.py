# -*- coding: utf-8 -*-
"""
העלאת קובץ וידאו מקומי ל-Meta (POST /act_<id>/advideos), המתנה לסיום עיבוד,
ואיתור תמונת תצוגה (thumbnail) לשימוש בקריאטיב.
"""

import time
from pathlib import Path

import requests

import config

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 600  # 10 דקות - וידאו קצר אמור לעבור עיבוד הרבה יותר מהר
UPLOAD_MAX_ATTEMPTS = 3
UPLOAD_RETRY_BACKOFF_SECONDS = 10


def upload_video(local_path: Path, name: str) -> str:
    """
    מעלה קובץ וידאו ומחזיר video_id. לא ממתין לסיום עיבוד (ראו wait_until_ready).
    מנסה שוב עד UPLOAD_MAX_ATTEMPTS פעמים על תקלת רשת (timeout/ניתוק) - העלאת קובץ
    וידאו גדול על חיבור ביתי רגיש לזה, וזה לא אומר שיש בעיה אמיתית בקוד/בחשבון.
    """
    if config.DRY_RUN:
        return f"DRY_RUN_VIDEO_ID_{name}"

    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/advideos"
    last_error = None
    data = None
    for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
        try:
            with open(local_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"access_token": config.ACCESS_TOKEN, "name": name},
                    files={"source": f},
                    timeout=300,
                )
            # גם אם הבקשה "הצליחה" ברמת החיבור, גוף תשובה ריק/לא-JSON תקין הוא עדיין
            # תקלת רשת (חיבור שנקטע/פרוקסי שהתערב) - צריך ניסיון חוזר, לא קריסה מיידית.
            if not resp.text.strip():
                raise RuntimeError(f"תשובה ריקה מה-API (status={resp.status_code})")
            data = resp.json()
            break
        except (requests.exceptions.RequestException, RuntimeError, ValueError) as e:
            last_error = e
            print(f"  תקלת רשת בהעלאת '{name}' (ניסיון {attempt}/{UPLOAD_MAX_ATTEMPTS}): {e}")
            if attempt < UPLOAD_MAX_ATTEMPTS:
                time.sleep(UPLOAD_RETRY_BACKOFF_SECONDS)
    if data is None:
        raise RuntimeError(f"נכשל בהעלאת '{name}' אחרי {UPLOAD_MAX_ATTEMPTS} ניסיונות: {last_error}")
    if "error" in data:
        raise RuntimeError(f"נכשל בהעלאת וידאו '{local_path.name}': {data['error']}")
    return data["id"]


def wait_until_ready(video_id: str) -> None:
    """ממתין (polling) עד שהעיבוד של הווידאו מסתיים ('ready'), או זורק שגיאה בטיימאאוט/כשל."""
    if config.DRY_RUN:
        return

    url = f"{config.GRAPH_URL}/{video_id}"
    elapsed = 0
    while elapsed < POLL_TIMEOUT_SECONDS:
        resp = requests.get(url, params={
            "fields": "status",
            "access_token": config.ACCESS_TOKEN,
        }, timeout=30)
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"נכשל בבדיקת סטטוס וידאו {video_id}: {data['error']}")

        video_status = data.get("status", {}).get("video_status")
        print(f"  וידאו {video_id}: status={video_status} (חלפו {elapsed} שניות)")

        if video_status == "ready":
            return
        if video_status == "error":
            raise RuntimeError(f"עיבוד הווידאו {video_id} נכשל בצד Meta: {data['status']}")

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    raise RuntimeError(f"וידאו {video_id} לא הסתיים בעיבוד תוך {POLL_TIMEOUT_SECONDS} שניות")


def get_thumbnail_url(video_id: str) -> str:
    """מחזיר URL של תמונת תצוגה (thumbnail) שנוצרה אוטומטית ע\"י Meta לווידאו."""
    if config.DRY_RUN:
        return "DRY_RUN_THUMBNAIL_URL"

    url = f"{config.GRAPH_URL}/{video_id}/thumbnails"
    resp = requests.get(url, params={"access_token": config.ACCESS_TOKEN}, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת thumbnails לווידאו {video_id}: {data['error']}")

    thumbnails = data.get("data", [])
    if not thumbnails:
        raise RuntimeError(f"לא נמצאו thumbnails לווידאו {video_id} - נסה שוב עוד כמה שניות "
                            f"(ייתכן שהעיבוד עוד לא הפיק תצוגות מקדימות)")

    preferred = next((t for t in thumbnails if t.get("is_preferred")), thumbnails[0])
    return preferred["uri"]


def upload_and_prepare(local_path: Path, name: str) -> dict:
    """זרימה מלאה: העלאה -> המתנה ל-ready -> thumbnail. מחזיר {'video_id', 'thumbnail_url'}."""
    video_id = upload_video(local_path, name)
    wait_until_ready(video_id)
    thumbnail_url = get_thumbnail_url(video_id)
    return {"video_id": video_id, "thumbnail_url": thumbnail_url}
