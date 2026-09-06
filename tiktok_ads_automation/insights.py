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
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"נכשל בשליפת סטטוס מודעות: {data}")
    return {item["ad_id"]: item.get("operation_status", "UNKNOWN") for item in data["data"].get("list", [])}
