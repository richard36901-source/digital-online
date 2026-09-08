# -*- coding: utf-8 -*-
"""
משיכת נתוני ביצועים (Insights) מ-Meta Marketing API ברמת המודעה, מסונן לקמפיין הזה בלבד
(config.CAMPAIGN_NAME) - לא כל מודעה אחרת שכבר קיימת בחשבון act_330184635273905.
מקביל בכוונה ל-tiktok_ads_automation/insights.py.
"""

import requests

import config


def find_campaign() -> dict | None:
    """מחפש את הקמפיין לפי שם (config.CAMPAIGN_NAME) בחשבון. מחזיר {'id','name','objective'} או None."""
    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}"
    resp = requests.get(url, params={
        "fields": "campaigns.limit(200){id,name,objective}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת קמפיינים עבור act_{config.AD_ACCOUNT_ID}: {data['error']}")

    campaigns = data.get("campaigns", {}).get("data", [])
    return next((c for c in campaigns if c.get("name") == config.CAMPAIGN_NAME), None)


def fetch_ad_insights(campaign_id: str) -> list[dict]:
    """מושך ביצועים ברמת מודעה עבור קמפיין נתון בלבד."""
    url = f"{config.GRAPH_URL}/{campaign_id}/insights"
    params = {
        "level": "ad",
        "date_preset": config.DATE_PRESET,
        "fields": "ad_id,ad_name,adset_id,spend,impressions,actions",
        "access_token": config.ACCESS_TOKEN,
        "limit": 200,
    }

    results = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        params = None  # paging url כבר כולל פרמטרים
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"נכשל בשליפת insights עבור קמפיין {campaign_id}: {data['error']}")
        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")

    return results


def extract_link_clicks(insight_row: dict) -> int:
    """סופר קליקים על הלינק (link_click) מתוך actions - זה המדד הרלוונטי לתנועה לפרופיל."""
    actions = insight_row.get("actions") or []
    for a in actions:
        if a.get("action_type") == "link_click":
            return int(float(a.get("value", 0)))
    return 0


def get_ads_status(campaign_id: str) -> dict:
    """מחזיר {ad_id: effective_status} לכל המודעות בקמפיין, בקריאה אחת."""
    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": "ads.limit(200){id,effective_status}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת סטטוס מודעות לקמפיין {campaign_id}: {data['error']}")
    return {ad["id"]: ad.get("effective_status", "UNKNOWN") for ad in data.get("ads", {}).get("data", [])}
