"""
מנוע הכללים: מחליט אילו מודעות להשהות, ואילו מועמדות לרוטציית קריאטיב.
"""

from datetime import datetime, timezone
import config
import insights


def evaluate_ad(insight_row: dict) -> dict:
    """
    מחזיר dict עם החלטה עבור מודעה בודדת:
    {ad_id, ad_name, spend, roas, leads, decision, reason}
    decision אחד מ: "pause" | "rotate_creative" | "ok"
    """
    ad_id = insight_row["ad_id"]
    ad_name = insight_row.get("ad_name", ad_id)
    spend = float(insight_row.get("spend", 0))
    roas = insights.extract_roas(insight_row)
    leads = insights.extract_leads(insight_row)

    decision = "ok"
    reason = ""

    # כלל 1: רווחיות - אם יש נתוני ROAS ממשיים והם מתחת לסף -> להשהות
    if roas is not None and roas < config.ROAS_THRESHOLD:
        decision = "pause"
        reason = f"ROAS {roas:.2f} מתחת לסף {config.ROAS_THRESHOLD}"

    # כלל 2: אם אין נתוני ROAS (למשל קמפיין לידים) אבל יש הוצאה משמעותית וללא תוצאות
    elif roas is None and spend > 20 and leads == 0:
        decision = "pause"
        reason = f"הוצאה של {spend:.2f} ללא אף תוצאה (אין נתוני ROAS בחשבון זה)"

    else:
        # כלל 3: מודעה "בריאה" - בדוק אם היא מועמדת לרוטציית קריאטיב לפי גיל
        ad_details = insights.get_ad_status(ad_id)
        created_time = ad_details.get("created_time")
        if created_time:
            created_dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
            if age_days >= config.CREATIVE_ROTATION_DAYS:
                decision = "rotate_creative"
                reason = f"המודעה רצה {age_days} ימים - מועמדת לרענון קריאטיב"

    return {
        "ad_id": ad_id,
        "ad_name": ad_name,
        "spend": spend,
        "roas": roas,
        "leads": leads,
        "decision": decision,
        "reason": reason,
    }


def evaluate_account(insight_rows: list[dict]) -> list[dict]:
    """מריץ evaluate_ad על כל השורות של חשבון מודעות אחד."""
    return [evaluate_ad(row) for row in insight_rows]
