"""
רשימת Identities זמינות לחשבון המפרסם - נדרש עבור actions.create_ad (config.IDENTITY_ID).

לא נמצא ב-TikTok Business Center עמוד UI ברור לניהול Identities (נבדק בפועל - Assets
מכיל רק Pixels/Catalogs/Audiences/Leads/Forms/Minis, בלי Identities) - לכן שואלים
ישירות את ה-API במקום להמשיך לחפש בממשק.
"""

import requests

import config
from locations import _find_list


def fetch_identities() -> list[dict]:
    """מחזיר את כל ה-Identities הזמינות לחשבון המפרסם (advertiser_id הראשון ב-config)."""
    resp = requests.get(
        f"{config.API_BASE_URL}/identity/get/",
        headers={"Access-Token": config.ACCESS_TOKEN},
        params={
            "advertiser_id": next(iter(config.ADVERTISER_ACCOUNTS.values())),
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת Identities: {data}")
    return _find_list(data["data"])
