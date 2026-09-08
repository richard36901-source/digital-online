# -*- coding: utf-8 -*-
"""
פעולות כתיבה על Ad Sets קיימים - הפעלה/השהיה ועדכון תקציב יומי. משמש את webapp.py
(לוח הבקרה). מכבד את config.DRY_RUN בדיוק כמו campaign_launch.py - במצב DRY_RUN
שום קריאת API אמיתית לא נשלחת, רק מוחזר אישור מדומה.
"""

import requests

import config


def _post(adset_id: str, data: dict) -> dict:
    if config.DRY_RUN:
        return {"dry_run": True, "adset_id": adset_id, **data}

    url = f"{config.GRAPH_URL}/{adset_id}"
    resp = requests.post(url, data={**data, "access_token": config.ACCESS_TOKEN}, timeout=30)
    result = resp.json()
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    return result


def pause_adset(adset_id: str) -> dict:
    return _post(adset_id, {"status": "PAUSED"})


def enable_adset(adset_id: str) -> dict:
    return _post(adset_id, {"status": "ACTIVE"})


def update_adset_budget(adset_id: str, daily_budget_ils: float) -> dict:
    """daily_budget_ils בשקלים שלמים/עשרוניים - מומר לאגורות (השדה האמיתי ב-API)."""
    agorot = int(round(daily_budget_ils * 100))
    return _post(adset_id, {"daily_budget": agorot})


def update_adset_bid_amount(adset_id: str, bid_amount_ils: float) -> dict:
    """bid_amount_ils בשקלים - מומר לאגורות. ראו BID_AMOUNT_AGOROT ב-config.py."""
    agorot = int(round(bid_amount_ils * 100))
    return _post(adset_id, {"bid_amount": agorot})
