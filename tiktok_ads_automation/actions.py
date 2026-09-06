"""
ביצוע פעולות אמיתיות מול TikTok Marketing API: השהיית מודעה, החלפת קריאטיב.
כל פעולה עוברת קודם דרך config.DRY_RUN - אם True, רק נרשם ללוג ולא מבוצע בפועל.
"""

import hashlib
from pathlib import Path

import requests

import config

HEADERS = {"Access-Token": config.ACCESS_TOKEN, "Content-Type": "application/json"}


def pause_ad(advertiser_id: str, ad_id: str) -> dict:
    """משהה מודעה (opt_status=DISABLE)."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "pause", "ad_id": ad_id}

    resp = requests.post(
        f"{config.API_BASE_URL}/ad/status/update/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "ad_ids": [ad_id],
            "opt_status": "DISABLE",
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהשהיית מודעה {ad_id}: {data}")
    return {"dry_run": False, "action": "pause", "ad_id": ad_id, "result": data}


def upload_video(advertiser_id: str, video_path: Path) -> str:
    """מעלה קובץ וידאו לספריית המדיה של חשבון המפרסם, מחזיר video_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_VIDEO_ID_{video_path.name}"

    video_bytes = video_path.read_bytes()
    video_signature = hashlib.md5(video_bytes).hexdigest()

    resp = requests.post(
        f"{config.API_BASE_URL}/file/video/ad/upload/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        data={
            "advertiser_id": advertiser_id,
            "upload_type": "UPLOAD_BY_FILE",
            "video_signature": video_signature,
        },
        files={"video_file": (video_path.name, video_bytes, "video/mp4")},
        timeout=120,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהעלאת וידאו {video_path}: {data}")
    return data["data"][0]["video_id"]


def update_ad_creative(advertiser_id: str, ad_id: str, video_id: str, ad_text: str) -> dict:
    """מעדכן קריאטיב (וידאו + טקסט) של מודעה קיימת."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "update_creative", "ad_id": ad_id, "video_id": video_id}

    resp = requests.post(
        f"{config.API_BASE_URL}/ad/update/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "ad_id": ad_id,
            "video_id": video_id,
            "ad_text": ad_text,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בעדכון קריאטיב למודעה {ad_id}: {data}")
    return {"dry_run": False, "action": "update_creative", "ad_id": ad_id, "result": data}
