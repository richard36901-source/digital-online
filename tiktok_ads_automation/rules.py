"""
מנוע הכללים: מחליט אילו מודעות להשהות, ואילו מועמדות לרוטציית קריאטיב.
מבנה מקביל ל-rules.py באוטומציית Meta Ads.
"""

from datetime import datetime, timezone

import config
import insights


def evaluate_ad(advertiser_id: str, insight_row: dict) -> dict:
    """
    מחזיר dict עם החלטה עבור מודעה בודדת:
    {ad_id, ad_name, spend, roas, conversions, decision, reason}
    decision אחד מ: "pause" | "rotate_creative" | "ok"
    """
    ad_id = insight_row["ad_id"]
    ad_name = insight_row.get("ad_name", ad_id)
    spend = float(insight_row.get("spend", 0) or 0)
    roas = insight_row.get("roas")
    conversions = insight_row.get("conversions", 0)

    decision = "ok"
    reason = ""

    # כלל 1: רווחיות - אם יש נתוני ROAS ממשיים והם מתחת לסף -> להשהות
    if roas and roas > 0 and roas < config.ROAS_THRESHOLD:
        decision = "pause"
        reason = f"ROAS {roas:.2f} מתחת לסף {config.ROAS_THRESHOLD}"

    # כלל 2: אין נתוני ROAS (למשל קמפיין לידים/מודעות שלא ל-e-commerce) אבל הוצאה משמעותית בלי המרות
    elif not roas and spend > 20 and conversions == 0:
        decision = "pause"
        reason = f"הוצאה של {spend:.2f} ללא אף המרה (אין נתוני ROAS בחשבון זה)"

    else:
        # כלל 3: מודעה "בריאה" - בדוק אם היא מועמדת לרוטציית קריאטיב לפי גיל
        ad_details = insights.get_ad_details(advertiser_id, ad_id)
        create_time = ad_details.get("create_time")
        if create_time:
            created_dt = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
            if age_days >= config.CREATIVE_ROTATION_DAYS:
                decision = "rotate_creative"
                reason = f"המודעה רצה {age_days} ימים - מועמדת לרענון קריאטיב"

    return {
        "ad_id": ad_id,
        "ad_name": ad_name,
        "spend": spend,
        "roas": roas,
        "conversions": conversions,
        "decision": decision,
        "reason": reason,
    }


def evaluate_account(advertiser_id: str, insight_rows: list[dict]) -> list[dict]:
    """מריץ evaluate_ad על כל השורות של חשבון מפרסם אחד."""
    return [evaluate_ad(advertiser_id, row) for row in insight_rows]
