"""
חיפוש location_id של TikTok (לא קוד מדינה רגיל) לצורך טירגוט גיאוגרפי ב-config.TARGETING_LOCATION_IDS.

הערה: שמות השדות בתגובת /tool/region/ (region_code/region_name) נכתבו לפי תיעוד TikTok
הפומבי בלי אפשרות לבדוק בפועל (הסביבה הזו חסומה רשתית מ-TikTok). אם ההרצה נכשלת עם
KeyError - הדביקו את ה-JSON שחזר בפועל ותתוקן המיפוי.
"""

import requests

import config


def search_locations(query: str) -> list[dict]:
    """מחפש מיקומים לפי שם (למשל 'ישראל' או 'Israel'), מחזיר [{"location_id", "name"}, ...]."""
    resp = requests.get(
        f"{config.API_BASE_URL}/tool/region/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        params={"advertiser_id": next(iter(config.ADVERTISER_ACCOUNTS.values()))},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת רשימת מיקומים: {data}")

    query_lower = query.strip().lower()
    matches = [
        {"location_id": region["region_code"], "name": region["region_name"]}
        for region in data["data"].get("region_info", [])
        if query_lower in region.get("region_name", "").lower()
    ]
    return matches
