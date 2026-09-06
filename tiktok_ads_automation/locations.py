"""
חיפוש location_id של TikTok (לא קוד מדינה רגיל) לצורך טירגוט גיאוגרפי ב-config.TARGETING_LOCATION_IDS.

הערה: שמות השדות בתגובת /tool/region/ (region_code/region_name) נכתבו לפי תיעוד TikTok
הפומבי בלי אפשרות לבדוק בפועל (הסביבה הזו חסומה רשתית מ-TikTok). אם ההרצה נכשלת עם
KeyError - הדביקו את ה-JSON שחזר בפועל ותתוקן המיפוי.
"""

import json

import requests

import config


def fetch_raw_regions() -> dict:
    """קריאה גולמית ל-/tool/region/ - מוחזר כמו שהתקבל, בלי שום הנחה על שמות שדות."""
    resp = requests.get(
        f"{config.API_BASE_URL}/tool/region/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        params={
            "advertiser_id": next(iter(config.ADVERTISER_ACCOUNTS.values())),
            # שני הפרמטרים הבאים נדרשים ע"י ה-API (התגלה מריצות אמיתיות - קוד 40002
            # בלעדיהם). objective_type תואם לברירת המחדל ב-actions.create_campaign.
            "placements": '["PLACEMENT_TIKTOK"]',
            "objective_type": "TRAFFIC",
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת רשימת מיקומים: {data}")
    return data["data"]


def _find_list(node, depth: int = 0) -> list:
    """מוצא את הרשימה הראשונה של dict-ים בתוך התגובה (המבנה המדויק לא ידוע מראש)."""
    if depth > 4:
        return []
    if isinstance(node, list) and node and isinstance(node[0], dict):
        return node
    if isinstance(node, dict):
        for value in node.values():
            found = _find_list(value, depth + 1)
            if found:
                return found
    return []


def search_locations(query: str) -> list[dict]:
    """
    מחפש מיקומים לפי שם (למשל 'ישראל' או 'Israel'), מחזיר [{"location_id", "name"}, ...].
    לא מניח שם שדה קבוע ל-id/name - סורק את כל השדות בכל אובייקט ומחפש את המחרוזת בכל
    ערך טקסטואלי, כדי לעבוד גם אם שמות השדות שונים ממה שציפינו.
    """
    raw = fetch_raw_regions()
    items = _find_list(raw)

    query_lower = query.strip().lower()
    matches = []
    for item in items:
        text_values = {k: v for k, v in item.items() if isinstance(v, str)}
        if any(query_lower in v.lower() for v in text_values.values()):
            matches.append(item)
    return matches


def debug_dump(limit: int = 5) -> str:
    """מדפיס את התגובה הגולמית (מקוצרת) - לשימוש כשלא נמצאות תוצאות, כדי לראות את המבנה האמיתי."""
    raw = fetch_raw_regions()
    items = _find_list(raw)
    sample = items[:limit] if items else raw
    return json.dumps(sample, ensure_ascii=False, indent=2)
