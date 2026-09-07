"""
ביצוע פעולות אמיתיות מול TikTok Marketing API: יצירת קמפיין/קבוצת מודעות/מודעה,
השהיית מודעה, החלפת קריאטיב.
כל פעולה עוברת קודם דרך config.DRY_RUN - אם True, רק נרשם ללוג ולא מבוצע בפועל.

הערה: כל הפעולות כאן נכתבו לפי תיעוד TikTok Marketing API v1.3 הפומבי. pause_ad
ו-enable_ad (opt_status ENABLE/DISABLE) אומתו/דומות למבנה שכבר עבד בפועל (ad/status/update/).
update_adgroup_budget (adgroup/update/) עדיין לא נבדק מול TikTok בפועל - אם מתקבלת שגיאת
ולידציה, הדביקו אותה בשיחה ותתוקן בהתאם (בדיוק כמו שקרה עם /tool/region/).
"""

import hashlib
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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


def enable_ad(advertiser_id: str, ad_id: str) -> dict:
    """מפעיל מודעה מושהית (opt_status=ENABLE) - ההפך מ-pause_ad."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "enable", "ad_id": ad_id}

    resp = requests.post(
        f"{config.API_BASE_URL}/ad/status/update/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "ad_ids": [ad_id],
            "opt_status": "ENABLE",
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהפעלת מודעה {ad_id}: {data}")
    return {"dry_run": False, "action": "enable", "ad_id": ad_id, "result": data}


def update_adgroup_budget(advertiser_id: str, adgroup_id: str, new_budget: float) -> dict:
    """מעדכן את התקציב היומי של קבוצת מודעות קיימת."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "update_budget", "adgroup_id": adgroup_id, "budget": new_budget}

    resp = requests.post(
        f"{config.API_BASE_URL}/adgroup/update/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "adgroup_id": adgroup_id,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": new_budget,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בעדכון תקציב לקבוצת מודעות {adgroup_id}: {data}")
    return {"dry_run": False, "action": "update_budget", "adgroup_id": adgroup_id, "budget": new_budget, "result": data}


def upload_video(advertiser_id: str, video_path: Path) -> str:
    """מעלה קובץ וידאו לספריית המדיה של חשבון המפרסם, מחזיר video_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_VIDEO_ID_{video_path.name}"

    video_bytes = video_path.read_bytes()
    video_signature = hashlib.md5(video_bytes).hexdigest()
    content_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"

    resp = requests.post(
        f"{config.API_BASE_URL}/file/video/ad/upload/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        data={
            "advertiser_id": advertiser_id,
            "upload_type": "UPLOAD_BY_FILE",
            "video_signature": video_signature,
        },
        files={"video_file": (video_path.name, video_bytes, content_type)},
        timeout=300,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהעלאת וידאו {video_path}: {data}")
    return data["data"][0]["video_id"]


def create_campaign(advertiser_id: str, campaign_name: str, objective_type: str = "TRAFFIC") -> str:
    """יוצר קמפיין חדש (ברמה העליונה, ללא תקציב - התקציב נקבע ברמת ה-ad group). מחזיר campaign_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_CAMPAIGN_ID_{campaign_name}"

    resp = requests.post(
        f"{config.API_BASE_URL}/campaign/create/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "campaign_name": campaign_name,
            "objective_type": objective_type,
            "budget_mode": "BUDGET_MODE_INFINITE",
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל ביצירת קמפיין '{campaign_name}': {data}")
    return data["data"]["campaign_id"]


def create_adgroup(advertiser_id: str, campaign_id: str, adgroup_name: str, daily_budget: float) -> str:
    """יוצר קבוצת מודעות (ad group) עם תקציב יומי וטירגוט גיאוגרפי. מחזיר adgroup_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_ADGROUP_ID_{adgroup_name}"

    if not config.TARGETING_LOCATION_IDS:
        raise RuntimeError(
            "config.TARGETING_LOCATION_IDS ריק - יש להריץ קודם 'python main.py lookup-locations \"ישראל\"' ולמלא."
        )

    # נדרש בפועל ע"י ה-API גם עם schedule_type=SCHEDULE_FROM_NOW (קוד 40002 בלעדיו -
    # התגלה מריצה אמיתית). באזור הזמן של חשבון המפרסם (Asia/Jerusalem), עם רווח קטן
    # קדימה כדי להימנע מדחייה על "זמן עבר" בגלל פערי שעון.
    schedule_start_time = (datetime.now(ZoneInfo("Asia/Jerusalem")) + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    resp = requests.post(
        f"{config.API_BASE_URL}/adgroup/create/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "campaign_id": campaign_id,
            "adgroup_name": adgroup_name,
            "promotion_type": "WEBSITE",
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "location_ids": config.TARGETING_LOCATION_IDS,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": daily_budget,
            "schedule_type": "SCHEDULE_FROM_NOW",
            "schedule_start_time": schedule_start_time,
            "optimization_goal": "CLICK",
            "billing_event": "CPC",
            "bid_type": "BID_TYPE_NO_BID",
            "pacing": "PACING_MODE_SMOOTH",
            "operation_status": "ENABLE",
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל ביצירת קבוצת מודעות '{adgroup_name}': {data}")
    return data["data"]["adgroup_id"]


def create_ad(advertiser_id: str, adgroup_id: str, ad_name: str, video_id: str, ad_text: str) -> str:
    """יוצר מודעה בודדת בתוך קבוצת מודעות קיימת, עם וידאו + טקסט + קישור יעד. מחזיר ad_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_AD_ID_{ad_name}"

    resp = requests.post(
        f"{config.API_BASE_URL}/ad/create/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "adgroup_id": adgroup_id,
            "creatives": [{
                "ad_name": ad_name,
                "ad_format": "SINGLE_VIDEO",  # נדרש בפועל ע"פ ה-API (קוד 40002 בלעדיו)
                "ad_text": ad_text,
                "identity_type": config.IDENTITY_TYPE,
                "identity_id": config.IDENTITY_ID,
                "video_id": video_id,
                "landing_page_url": config.DESTINATION_URL,
                "call_to_action": "LEARN_MORE",
            }],
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל ביצירת מודעה '{ad_name}': {data}")
    return data["data"]["ad_ids"][0]


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
