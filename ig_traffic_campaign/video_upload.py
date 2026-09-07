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
CHUNK_SIZE_BYTES = 4 * 1024 * 1024  # 4MB - קטן מספיק שגם חיבור לא יציב יעמוד בזמן להעלות


def _post_with_retry(url: str, data: dict, files: dict = None, name: str = "") -> dict:
    """
    POST עם ניסיון חוזר (עד UPLOAD_MAX_ATTEMPTS) על תקלת רשת - כולל המקרה שהבקשה
    "הצליחה" ברמת החיבור אבל חזרה עם גוף תשובה ריק/לא-JSON (ראו את שתי הפעמים שזה
    קרה בפועל: write timeout, ואז 413 עם גוף ריק על אותה בקשה גדולה מדי).
    """
    last_error = None
    for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, data=data, files=files, timeout=120)
            if not resp.text.strip():
                raise RuntimeError(f"תשובה ריקה מה-API (status={resp.status_code})")
            result = resp.json()
            if "error" in result:
                raise RuntimeError(f"שגיאת API: {result['error']}")
            return result
        except (requests.exceptions.RequestException, RuntimeError, ValueError) as e:
            last_error = e
            print(f"  תקלת רשת ({name}, ניסיון {attempt}/{UPLOAD_MAX_ATTEMPTS}): {e}")
            if attempt < UPLOAD_MAX_ATTEMPTS:
                time.sleep(UPLOAD_RETRY_BACKOFF_SECONDS)
    raise RuntimeError(f"נכשל אחרי {UPLOAD_MAX_ATTEMPTS} ניסיונות ({name}): {last_error}")


def upload_video(local_path: Path, name: str) -> str:
    """
    מעלה קובץ וידאו ומחזיר video_id, בפרוטוקול ה-Resumable Upload של Meta (start ->
    transfer בחתיכות של CHUNK_SIZE_BYTES -> finish) במקום בקשה אחת גדולה - כי בקשה
    אחת נכשלה בפועל עם 413 (Payload Too Large) על קבצי הווידאו האלה. חתיכות קטנות
    גם עמידות יותר לניתוקי רשת - חתיכה שנכשלת מנוסה שוב בלי לאבד את כל ההעלאה.
    לא ממתין לסיום עיבוד (ראו wait_until_ready).
    """
    if config.DRY_RUN:
        return f"DRY_RUN_VIDEO_ID_{name}"

    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/advideos"
    file_size = local_path.stat().st_size

    start = _post_with_retry(url, data={
        "access_token": config.ACCESS_TOKEN,
        "upload_phase": "start",
        "file_size": file_size,
        "name": name,
    }, name=f"{name} - start")
    upload_session_id = start["upload_session_id"]
    video_id = start["video_id"]
    start_offset = int(start["start_offset"])
    end_offset = int(start["end_offset"])

    with open(local_path, "rb") as f:
        while start_offset < file_size:
            f.seek(start_offset)
            chunk = f.read(end_offset - start_offset)
            print(f"  מעלה חתיכה {start_offset:,}-{end_offset:,} מתוך {file_size:,} בייט "
                  f"({start_offset * 100 // file_size}%)...")
            transfer = _post_with_retry(url, data={
                "access_token": config.ACCESS_TOKEN,
                "upload_phase": "transfer",
                "upload_session_id": upload_session_id,
                "start_offset": start_offset,
            }, files={"video_file_chunk": chunk}, name=f"{name} - chunk {start_offset}")
            start_offset = int(transfer["start_offset"])
            end_offset = int(transfer["end_offset"])

    _post_with_retry(url, data={
        "access_token": config.ACCESS_TOKEN,
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
    }, name=f"{name} - finish")

    return video_id


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
