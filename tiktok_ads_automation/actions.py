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
import json
import mimetypes
import time
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


def get_advertiser_currency(advertiser_id: str) -> str:
    """
    מחזיר את מטבע החיוב של חשבון המפרסם (למשל "USD", לא בהכרח "ILS") - קריטי כי
    כל השדות המספריים (budget וכו') ב-API הם מספרים גולמיים במטבע הזה, בלי יחידה.
    התגלה בפועל: קבוצות מודעות נוצרו עם budget=10 מתוך כוונה ל-10 ש"ח, אבל
    החשבון במטבע USD - אז בפועל חויבו/יחויבו 10 דולר ליום, לא 10 שקל.

    אם config.ADVERTISER_CURRENCY מוגדר, משתמשים בו ישירות בלי לפנות ל-API בכלל -
    נדרש כי הטוקן הנוכחי חסר את ה-scope ל-/advertiser/info/ (קוד 40001 שהתקבל
    בפועל: "Permission error... lacks the required scope"), ותיקון זה דורש
    re-authorization מלא מול TikTok.
    """
    if config.ADVERTISER_CURRENCY:
        return config.ADVERTISER_CURRENCY

    resp = requests.get(
        f"{config.API_BASE_URL}/advertiser/info/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        params={
            "advertiser_ids": json.dumps([advertiser_id]),
            "fields": json.dumps(["currency"]),
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת מטבע חשבון המפרסם {advertiser_id}: {data}")
    items = data["data"].get("list", [])
    if not items or "currency" not in items[0]:
        raise RuntimeError(f"לא נמצא שדה currency בתגובת /advertiser/info/ - תגובה מלאה: {data}")
    return items[0]["currency"]


def convert_ils_to_currency(currency: str, ils_amount: float) -> float:
    """
    ממיר סכום מש"ח למטבע חשבון המפרסם, לפי שער חליפין עדכני (Frankfurter API -
    ריבית יחוס של הבנק המרכזי האירופי, ללא צורך במפתח API). אם החשבון כבר ב-ILS,
    מחזיר את הסכום כמו שהוא בלי לפנות לשום API חיצוני.
    """
    if currency == "ILS":
        return ils_amount

    resp = requests.get(
        "https://api.frankfurter.app/latest",
        params={"from": "ILS", "to": currency},
        timeout=15,
    )
    data = resp.json()
    rate = data.get("rates", {}).get(currency)
    if not rate:
        raise RuntimeError(
            f"נכשל בהמרת מטבע מ-ILS ל-{currency} דרך Frankfurter API - תגובה: {data}. "
            "בלי המרה אמינה אסור להמשיך (עלול לגרום לחיוב בסכום שגוי)."
        )
    return round(ils_amount * rate, 2)


def find_video_id_by_filename(advertiser_id: str, filename: str) -> str | None:
    """
    מחפש בספריית הווידאו של חשבון המפרסם סרטון שכבר הועלה בשם קובץ נתון - לצורך
    התאוששות מ-code 40911 "Duplicated material name" (הועלה בהצלחה בהרצה קודמת,
    אבל יצירת המודעה נכשלה אחריו). לא בדוק במלואו מול המבנה האמיתי של /file/video/ad/search/
    (בלי אפשרות לבדוק בפועל) - סורק את כל השדות הטקסטואליים בכל פריט, לא מסתמך על
    שם שדה ספציפי (אותה גישה שעבדה ב-locations.py/identities.py).
    """
    from locations import _find_list

    # אין אפשרות לסנן לפי שם קובץ (filtering תומך רק ב-video_ids/material_ids/מידות),
    # אז סורקים את כל הספריה עם page_size מקסימלי (100) - חשוב לא להסתמך על ברירת
    # המחדל (20), כפי שהתגלה בפועל ב-get_video_cover_image_id כשהיו כבר סרטונים/
    # קמפיינים אחרים בחשבון.
    resp = requests.get(
        f"{config.API_BASE_URL}/file/video/ad/search/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        params={"advertiser_id": advertiser_id, "page": 1, "page_size": 100},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        return None

    items = _find_list(data["data"])
    for item in items:
        text_values = {k: v for k, v in item.items() if isinstance(v, str)}
        if any(v == filename for v in text_values.values()):
            return item.get("video_id")
    return None


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
        # קוד 40911 - הקובץ כבר הועלה בהרצה קודמת (נכשל אחרי ההעלאה, לפני יצירת
        # המודעה) - מחפשים את ה-video_id הקיים במקום לזרוק שגיאה.
        if data.get("code") == 40911:
            existing_video_id = find_video_id_by_filename(advertiser_id, video_path.name)
            if existing_video_id:
                return existing_video_id
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


def get_video_cover_image_id(advertiser_id: str, video_id: str) -> str:
    """
    מוצא את תמונת התצוגה (poster) שנוצרה אוטומטית לסרטון שכבר הועלה, ומעלה אותה
    כתמונה נפרדת לספריית התמונות - TikTok דורש image_ids בכל מודעת SINGLE_VIDEO
    בנוסף לוידאו עצמו (קוד 40002 "You must upload an image" בלעדיו, אומת בפועל).
    מחזיר image_id. שמות השדות ב-/file/video/ad/search/ לא אומתו במלואם - סורק
    באופן גמיש (אותה גישה שעבדה ב-locations.py).

    מסננים עם filtering.video_ids (במקום להסתמך על ברירת המחדל page=1/page_size=20
    ולקוות שהסרטון בעמוד הראשון) - קריטי כשבחשבון כבר יש קמפיינים/סרטונים אחרים
    (כפי שהתגלה בפועל אחרי שהסרטון הראשון הצליח אבל השני נכשל - הסרטון השני כנראה
    פשוט לא הופיע בעמוד הראשון של ספריית הווידאו).
    """
    from locations import _find_list

    poster_url = None
    last_data = None
    # ניסיונות חוזרים עם השהיה - יכול להיות שה-poster עוד לא נוצר מיד אחרי ההעלאה
    # (עיבוד אסינכרוני ב-TikTok).
    for attempt in range(5):
        resp = requests.get(
            f"{config.API_BASE_URL}/file/video/ad/search/",
            headers={"Access-Token": config.ACCESS_TOKEN},
            params={
                "advertiser_id": advertiser_id,
                "filtering": json.dumps({"video_ids": [video_id]}),
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"נכשל בחיפוש פרטי וידאו {video_id}: {data}")
        last_data = data

        for item in _find_list(data["data"]):
            if item.get("video_id") == video_id:
                poster_url = item.get("poster_url") or item.get("video_cover_url")
                break

        if poster_url:
            break
        time.sleep(3)

    if not poster_url:
        raise RuntimeError(
            f"לא נמצאה תמונת תצוגה (poster_url) לסרטון {video_id} ב-/file/video/ad/search/ "
            f"אחרי 5 ניסיונות - יכול להיות ששם השדה שונה בפועל. תגובה מלאה: {last_data}"
        )

    resp = requests.post(
        f"{config.API_BASE_URL}/file/image/ad/upload/",
        headers=HEADERS,
        json={
            "advertiser_id": advertiser_id,
            "upload_type": "UPLOAD_BY_URL",
            "image_url": poster_url,
        },
        timeout=60,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בהעלאת תמונת התצוגה לסרטון {video_id}: {data}")
    return data["data"]["image_id"]


def create_ad(advertiser_id: str, adgroup_id: str, ad_name: str, video_id: str, ad_text: str) -> str:
    """יוצר מודעה בודדת בתוך קבוצת מודעות קיימת, עם וידאו + טקסט + קישור יעד. מחזיר ad_id."""
    if config.DRY_RUN:
        return f"DRY_RUN_AD_ID_{ad_name}"

    image_id = get_video_cover_image_id(advertiser_id, video_id)

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
                "image_ids": [image_id],  # נדרש בפועל ע"פ ה-API - ראו get_video_cover_image_id
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
