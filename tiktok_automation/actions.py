"""
פרסום סרטון בפועל מול TikTok Content Posting API (Direct Post, source=FILE_UPLOAD).
כל פעולה עוברת קודם דרך config.DRY_RUN - אם True, רק נרשם ללוג ולא מבוצע בפועל.

זרימת ה-API (ראו https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post):
  1. creator_info/query  - שולפים אילו רמות פרטיות מותרות לחשבון הזה (חובה להציג לפני פרסום)
  2. video/init           - פותחים בקשת פרסום, מקבלים publish_id + upload_url
  3. PUT ל-upload_url      - מעלים את בייטי הווידאו (חתיכה אחת, עד 64MB - ראו הערה למטה)
  4. status/fetch          - בודקים מתי הפרסום הושלם (או נכשל)

הערה: מימוש זה מעלה את כל הקובץ ב-PUT יחיד (chunk_count=1), מה שנתמך רשמית עד 64MB.
לקבצים גדולים יותר יש לפצל ל-chunks נוספים - לא נדרש עבור סרטוני שיווק קצרים.
"""

import time
from pathlib import Path

import requests

import auth
import config


def query_creator_info() -> dict:
    """שולף מידע על היוצר: אילו privacy_level מותרים, אורך וידאו מקסימלי וכו'. חובה לפני פרסום."""
    if config.DRY_RUN:
        return {"dry_run": True, "privacy_level_options": [config.DEFAULT_PRIVACY_LEVEL]}

    token = auth.get_valid_access_token()
    resp = requests.post(
        f"{config.API_BASE_URL}/post/publish/creator_info/query/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"},
        timeout=30,
    )
    data = resp.json()
    if data.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"נכשל בשליפת מידע יוצר: {data}")
    return data["data"]


def post_video(video_path: str, caption: str, privacy_level: str = None) -> dict:
    """מפרסם סרטון אחד ל-TikTok (Direct Post). מחזיר dict עם publish_id וסטטוס."""
    privacy_level = privacy_level or config.DEFAULT_PRIVACY_LEVEL
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"קובץ הווידאו לא נמצא: {video_path}")
    video_size = path.stat().st_size

    if config.DRY_RUN:
        return {
            "dry_run": True,
            "action": "post_video",
            "video_path": str(path),
            "caption": caption,
            "privacy_level": privacy_level,
            "video_size": video_size,
        }

    token = auth.get_valid_access_token()

    init_resp = requests.post(
        f"{config.API_BASE_URL}/post/publish/video/init/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"},
        json={
            "post_info": {
                "title": caption,
                "privacy_level": privacy_level,
                "disable_duplicate_check": False,
                "disable_comment": False,
                "disable_stitch": False,
                "disable_duet": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_data = init_resp.json()
    if "data" not in init_data or "publish_id" not in init_data["data"]:
        raise RuntimeError(f"נכשל באתחול פרסום עבור {video_path}: {init_data}")

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]

    with open(path, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        data=video_bytes,
        timeout=120,
    )
    if upload_resp.status_code not in (200, 201, 206):
        raise RuntimeError(f"נכשל בהעלאת בייטי הווידאו (publish_id={publish_id}): {upload_resp.status_code} {upload_resp.text}")

    return {"dry_run": False, "action": "post_video", "publish_id": publish_id, "video_path": str(path)}


def fetch_status(publish_id: str) -> dict:
    """בודק את סטטוס בקשת הפרסום (PROCESSING_UPLOAD / PUBLISH_COMPLETE / FAILED וכו')."""
    if config.DRY_RUN:
        return {"dry_run": True, "publish_id": publish_id, "status": "PUBLISH_COMPLETE"}

    token = auth.get_valid_access_token()
    resp = requests.post(
        f"{config.API_BASE_URL}/post/publish/status/fetch/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"},
        json={"publish_id": publish_id},
        timeout=30,
    )
    data = resp.json()
    if "data" not in data:
        raise RuntimeError(f"נכשל בבדיקת סטטוס פרסום {publish_id}: {data}")
    return data["data"]


def wait_for_publish(publish_id: str, timeout_sec: int = 120, poll_interval_sec: int = 5) -> dict:
    """ממתין (polling) עד שהפרסום מסתיים (הצלחה/כישלון) או עד timeout."""
    if config.DRY_RUN:
        return fetch_status(publish_id)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status = fetch_status(publish_id)
        if status.get("status") in ("PUBLISH_COMPLETE", "FAILED"):
            return status
        time.sleep(poll_interval_sec)
    return {"status": "TIMEOUT", "publish_id": publish_id}
