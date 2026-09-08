"""
משיכת נתוני ביצועים ברמת מודעה (ad) מ-TikTok Marketing API, לצורך מנוע הכללים.
"""

import json
from datetime import date, timedelta

import requests

import config

HEADERS = {"Access-Token": config.ACCESS_TOKEN, "Content-Type": "application/json"}

METRICS = ["spend", "conversion", "cost_per_conversion", config.ROAS_METRIC_NAME]


def fetch_ad_insights(advertiser_id: str) -> list[dict]:
    """
    מושך נתוני ביצועים ברמת מודעה עבור חלון הימים האחרונים (config.REPORT_LOOKBACK_DAYS).
    מחזיר רשימת dict-ים: {"ad_id", "ad_name", "spend", "conversions", "cost_per_conversion", "roas"}.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=config.REPORT_LOOKBACK_DAYS)

    resp = requests.get(
        f"{config.API_BASE_URL}/report/integrated/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_AD",
            "dimensions": '["ad_id"]',
            "metrics": str(METRICS).replace("'", '"'),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל במשיכת נתוני ביצועים עבור advertiser_id={advertiser_id}: {data}")

    rows = []
    for item in data["data"].get("list", []):
        dims = item.get("dimensions", {})
        metrics = item.get("metrics", {})
        rows.append({
            "ad_id": dims.get("ad_id"),
            "ad_name": metrics.get("ad_name", dims.get("ad_id")),
            "spend": float(metrics.get("spend", 0) or 0),
            "conversions": float(metrics.get("conversion", 0) or 0),
            "cost_per_conversion": float(metrics.get("cost_per_conversion", 0) or 0),
            "roas": float(metrics.get(config.ROAS_METRIC_NAME, 0) or 0),
        })
    return rows


def get_ad_details(advertiser_id: str, ad_id: str) -> dict:
    """שולף פרטי מודעה בודדת (כולל create_time), לצורך בדיקת גיל המודעה ברוטציית קריאטיב."""
    resp = requests.get(
        f"{config.API_BASE_URL}/ad/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "filtering": '{"ad_ids": ["%s"]}' % ad_id,
            "fields": '["ad_id", "create_time", "adgroup_id"]',
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת פרטי מודעה {ad_id}: {data}")
    items = data["data"].get("list", [])
    return items[0] if items else {}


TRAFFIC_METRICS = ["spend", "impressions", "clicks", "ctr", "cpc"]


def fetch_traffic_performance(advertiser_id: str, lookback_days: int = None) -> list[dict]:
    """
    מושך נתוני ביצועי תנועה ברמת מודעה (חשיפות/הקלקות/CTR) - לצורך dashboard.py, לזהות
    אילו סרטונים "מתבלטים" (הכי הרבה קליקים/CTR גבוה) מול הכושלות.
    מחזיר רשימת dict-ים: {"ad_id", "ad_name", "spend", "impressions", "clicks", "ctr", "cpc"}.
    """
    lookback_days = lookback_days if lookback_days is not None else config.REPORT_LOOKBACK_DAYS
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    resp = requests.get(
        f"{config.API_BASE_URL}/report/integrated/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_AD",
            "dimensions": '["ad_id"]',
            "metrics": str(TRAFFIC_METRICS).replace("'", '"'),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל במשיכת נתוני תנועה עבור advertiser_id={advertiser_id}: {data}")

    rows = []
    for item in data["data"].get("list", []):
        dims = item.get("dimensions", {})
        metrics = item.get("metrics", {})
        spend = float(metrics.get("spend", 0) or 0)
        clicks = float(metrics.get("clicks", 0) or 0)
        impressions = float(metrics.get("impressions", 0) or 0)
        rows.append({
            "ad_id": dims.get("ad_id"),
            "ad_name": metrics.get("ad_name", dims.get("ad_id")),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            # מחושב מקומית (לא רק נסמכים על שדה ctr מה-API) כדי למנוע חוסר עקביות בעיגול.
            "ctr": (clicks / impressions * 100) if impressions else 0.0,
            "cpc": (spend / clicks) if clicks else 0.0,
        })
    return rows


def fetch_daily_traffic_performance(advertiser_id: str, lookback_days: int = 14) -> list[dict]:
    """
    מושך ביצועי תנועה ברמת מודעה, מפוצל ליום (dimension נוסף: stat_time_day) - לצורך
    גרף מגמה בדשבורד (איך CTR/חשיפות/הוצאה משתנים יום אחר יום לכל סרטון, לא רק
    תמונת מצב מצטברת). TikTok תומכת עד 30 יום כשמוסיפים stat_time_day לממדים
    (אומת מול תיעוד ה-API - לא נבדק בפועל).
    מחזיר רשימת dict-ים: {"ad_id", "date" ("YYYY-MM-DD"), "spend", "impressions", "clicks", "ctr"}.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    resp = requests.get(
        f"{config.API_BASE_URL}/report/integrated/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_AD",
            "dimensions": '["ad_id", "stat_time_day"]',
            "metrics": str(TRAFFIC_METRICS).replace("'", '"'),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל במשיכת נתוני מגמה יומית עבור advertiser_id={advertiser_id}: {data}")

    rows = []
    for item in data["data"].get("list", []):
        dims = item.get("dimensions", {})
        metrics = item.get("metrics", {})
        clicks = float(metrics.get("clicks", 0) or 0)
        impressions = float(metrics.get("impressions", 0) or 0)
        # "stat_time_day" חוזר כ-"YYYY-MM-DD HH:MM:SS" (אותו פורמט כמו create_time
        # במקומות אחרים ב-API) - חותכים לתאריך בלבד להצגה.
        raw_date = dims.get("stat_time_day", "") or ""
        rows.append({
            "ad_id": dims.get("ad_id"),
            "date": raw_date[:10],
            "spend": float(metrics.get("spend", 0) or 0),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": (clicks / impressions * 100) if impressions else 0.0,
        })
    return rows


def get_ads_status(advertiser_id: str, ad_ids: list[str]) -> dict:
    """מחזיר {ad_id: operation_status} עבור רשימת מודעות - לתצוגת "פעיל/מושהה" בדשבורד."""
    if not ad_ids:
        return {}
    resp = requests.get(
        f"{config.API_BASE_URL}/ad/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"ad_ids": ad_ids}),
            "fields": '["ad_id", "operation_status"]',
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת סטטוס מודעות: {data}")
    return {item["ad_id"]: item.get("operation_status", "UNKNOWN") for item in data["data"].get("list", [])}


def get_ads_meta(advertiser_id: str, ad_ids: list[str]) -> dict:
    """מחזיר {ad_id: {"adgroup_id", "operation_status", "secondary_status", "ad_name", "video_url"}} -
    לצורך webapp.py (לוח בקרה) ו-dashboard.py. שם המודעה (ad_name) נשלף כאן מ-/ad/get/ -
    שדה קבוע על אובייקט המודעה עצמו - ולא מ-metrics.ad_name בדוח (report/integrated/get/),
    ששם השדה בפועל לא הוחזר כי לא נכלל ב-METRICS/TRAFFIC_METRICS, מה שגרם לדשבורד להציג
    מספרי ad_id גולמיים במקום שמות סרטונים.
    video_url מנסה לבנות קישור לצפייה בסרטון עצמו בטיקטוק (לא רק ב-Ads Manager), לפי
    tiktok_item_id + display_name - שדות שטוחים תקינים ב-/ad/get/.
    כל השדות המבוקשים כאן (כולל secondary_status) אומתו בפועל מול רשימת השדות התקינים
    שחזרה בהודעת שגיאה אמיתית (קוד 40002) כששלחנו "creatives" בטעות - לקח מפורש מהתקלה
    הזו: לא מוסיפים שדה בלי לוודא שהוא ברשימה הזו."""
    if not ad_ids:
        return {}
    resp = requests.get(
        f"{config.API_BASE_URL}/ad/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"ad_ids": ad_ids}),
            "fields": '["ad_id", "adgroup_id", "operation_status", "secondary_status", "ad_name", "tiktok_item_id", "display_name"]',
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת פרטי מודעות: {data}")

    def _video_url(item: dict) -> str | None:
        item_id = item.get("tiktok_item_id")
        username = item.get("display_name")
        return f"https://www.tiktok.com/@{username}/video/{item_id}" if item_id and username else None

    return {
        item["ad_id"]: {
            "adgroup_id": item.get("adgroup_id"),
            "operation_status": item.get("operation_status", "UNKNOWN"),
            "secondary_status": item.get("secondary_status"),
            "ad_name": item.get("ad_name"),
            "video_url": _video_url(item),
        }
        for item in data["data"].get("list", [])
    }


def get_ads_full_creative(advertiser_id: str, ad_ids: list[str]) -> dict:
    """מחזיר {ad_id: {"ad_name", "ad_text", "video_id", "image_ids", "identity_type",
    "identity_id", "landing_page_url", "call_to_action"}} - כל השדות שצריך כדי לשחזר
    קריאטיב קיים בשלמותו לפני שליחת /ad/update/ עם deeplink, כי /ad/update/ (בלי
    patch_update, או עם patch_update אבל deeplink לא נתמך שם - ראו actions.
    update_ad_full_creative_with_deeplink) דורש את כל שדות הקריאטיב, לא רק את מה
    שמשתנה, אחרת מוחק את מה שלא נשלח. השדות כאן לא אומתו עדיין מול רשימת השדות
    התקינים האמיתית של /ad/get/ - אם מתקבלת שגיאת 40002, ההודעה עצמה תכיל את הרשימה
    התקינה המלאה (בדיוק כמו שקרה עם "creatives") ויש לתקן בהתאם."""
    if not ad_ids:
        return {}
    resp = requests.get(
        f"{config.API_BASE_URL}/ad/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"ad_ids": ad_ids}),
            "fields": json.dumps([
                "ad_id", "ad_name", "ad_text", "video_id", "image_ids",
                "identity_type", "identity_id", "landing_page_url", "call_to_action",
            ]),
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת פרטי קריאטיב מלאים: {data}")

    return {
        item["ad_id"]: {
            "ad_name": item.get("ad_name"),
            "ad_text": item.get("ad_text"),
            "video_id": item.get("video_id"),
            "image_ids": item.get("image_ids"),
            "identity_type": item.get("identity_type"),
            "identity_id": item.get("identity_id"),
            "landing_page_url": item.get("landing_page_url"),
            "call_to_action": item.get("call_to_action"),
        }
        for item in data["data"].get("list", [])
    }


def get_adgroup_budgets(advertiser_id: str, adgroup_ids: list[str]) -> dict:
    """מחזיר {adgroup_id: {"budget", "budget_mode"}} - לצורך webapp.py (לוח בקרה)."""
    if not adgroup_ids:
        return {}
    resp = requests.get(
        f"{config.API_BASE_URL}/adgroup/get/",
        headers=HEADERS,
        params={
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"adgroup_ids": adgroup_ids}),
            "fields": '["adgroup_id", "budget", "budget_mode"]',
            "page": 1,
            "page_size": 1000,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת תקציבי קבוצות מודעות: {data}")
    return {
        item["adgroup_id"]: {"budget": float(item.get("budget", 0) or 0), "budget_mode": item.get("budget_mode")}
        for item in data["data"].get("list", [])
    }


def _fetch_all_pages(url: str, params: dict) -> list[dict]:
    """
    שולף את כל הפריטים מ-endpoint מדופדף (page/page_info.total_page), לא מסתפקים
    ב-page_size גדול בודד - זו הפעם השנייה בפועל שברירת מחדל/הנחה על מספר עמודים
    גרמה לפספוס נתונים אמיתיים (קודם וידאו ב-/file/video/ad/search/, עכשיו
    קבוצות מודעות ב-/adgroup/get/ - fix-budgets תיקן רק 10 מתוך 13 בגלל זה).
    """
    all_items = []
    page = 1
    while True:
        resp = requests.get(url, headers=HEADERS, params={**params, "page": page, "page_size": 1000}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"נכשל בשליפת נתונים מ-{url}: {data}")
        page_data = data["data"]
        all_items.extend(page_data.get("list", []))
        total_page = page_data.get("page_info", {}).get("total_page", 1)
        if page >= total_page:
            break
        page += 1
    return all_items


def get_campaigns(advertiser_id: str) -> list[dict]:
    """מחזיר את כל הקמפיינים בחשבון: [{"campaign_id", "campaign_name"}, ...] - לצורך
    בדיקת אידמפוטנטיות ב-campaign_launch.py (לא ליצור קמפיין כפול בהרצה חוזרת)."""
    return _fetch_all_pages(
        f"{config.API_BASE_URL}/campaign/get/",
        {"advertiser_id": advertiser_id, "fields": '["campaign_id", "campaign_name"]'},
    )


def get_adgroups(advertiser_id: str, campaign_id: str) -> list[dict]:
    """מחזיר את כל קבוצות המודעות תחת קמפיין נתון: [{"adgroup_id", "adgroup_name"}, ...] -
    לצורך בדיקת אידמפוטנטיות (לא ליצור adgroup כפול לאותו סרטון בהרצה חוזרת)."""
    return _fetch_all_pages(
        f"{config.API_BASE_URL}/adgroup/get/",
        {
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"campaign_ids": [campaign_id]}),
            "fields": '["adgroup_id", "adgroup_name"]',
        },
    )


def get_adgroup_ids_with_ads(advertiser_id: str, campaign_id: str) -> set:
    """מחזיר את קבוצות ה-adgroup_id שכבר יש להן לפחות מודעה אחת תחת הקמפיין - לצורך
    השלמת קבוצות מודעות "יתומות" (נוצרו בהרצה קודמת שנכשלה לפני שהמודעה נוצרה)
    במקום לדלג עליהן לגמרי."""
    items = get_ads_for_campaign(advertiser_id, campaign_id)
    return {item["adgroup_id"] for item in items}


def get_ads_for_campaign(advertiser_id: str, campaign_id: str) -> list[dict]:
    """מחזיר את כל המודעות תחת קמפיין נתון: [{"ad_id", "adgroup_id"}, ...] - לצורך
    סינון הדשבורד (dashboard.py) כך שיציג רק את המודעות של הקמפיין הזה, לא את כל
    המודעות בחשבון (כולל קמפיינים ישנים/לא קשורים)."""
    return _fetch_all_pages(
        f"{config.API_BASE_URL}/ad/get/",
        {
            "advertiser_id": advertiser_id,
            "filtering": json.dumps({"campaign_ids": [campaign_id]}),
            "fields": '["ad_id", "adgroup_id"]',
        },
    )
