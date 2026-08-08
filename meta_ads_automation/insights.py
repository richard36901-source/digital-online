"""
משיכת נתוני ביצועים (Insights) מ-Meta Marketing API ברמת המודעה.
"""

import requests
import config


def fetch_ad_insights(ad_account_id: str) -> list[dict]:
    """
    מושך ביצועים ברמת מודעה (ad) עבור חשבון מודעות נתון.
    מחזיר רשימת dict-ים, אחד לכל מודעה, עם: ad_id, ad_name, spend, purchase_roas, actions.
    """
    url = f"{config.GRAPH_URL}/act_{ad_account_id}/insights"
    params = {
        "level": "ad",
        "date_preset": config.DATE_PRESET,
        "fields": "ad_id,ad_name,spend,purchase_roas,actions,adset_id,campaign_id",
        "access_token": config.ACCESS_TOKEN,
        "limit": 500,
    }

    results = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        params = None  # paging url כבר כולל פרמטרים
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Meta API error for act_{ad_account_id}: {data['error']}")

        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")

    return results


def get_ad_status(ad_id: str) -> dict:
    """שולף מידע בסיסי + תאריך יצירה של מודעה, כדי לדעת כמה זמן היא רצה."""
    url = f"{config.GRAPH_URL}/{ad_id}"
    params = {
        "fields": "id,name,status,created_time,effective_status",
        "access_token": config.ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Meta API error for ad {ad_id}: {data['error']}")
    return data


def extract_roas(insight_row: dict) -> float | None:
    """
    Meta מחזירה purchase_roas כרשימה (בד"כ פריט אחד) עם 'value'.
    אם אין נתוני רכישה (למשל קמפיין לידים בלי ערך המרה), מחזיר None.
    """
    roas_data = insight_row.get("purchase_roas")
    if not roas_data:
        return None
    try:
        return float(roas_data[0]["value"])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def extract_leads(insight_row: dict) -> int:
    """סופר תוצאות מסוג ליד (lead) מתוך שדה actions, כגיבוי לחשבונות בלי ROAS."""
    actions = insight_row.get("actions") or []
    total = 0
    for a in actions:
        if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
            total += int(float(a.get("value", 0)))
    return total
