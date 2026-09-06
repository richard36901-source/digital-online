"""
משיכת נתוני ביצועים ברמת מודעה (ad) מ-TikTok Marketing API, לצורך מנוע הכללים.
"""

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
