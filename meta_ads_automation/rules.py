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


def evaluate_ad_cpl(insight_row: dict, threshold: float = None) -> dict:
    """
    בדיקה לפי עלות לליד (CPL) בלבד - משמשת את הריצה התלת-יומית (cpl_check.py),
    נפרדת ממנוע הכללים היומי (evaluate_ad) שמבוסס על ROAS.
    אם leads > 0 ו-CPL מעל הסף -> "rotate_and_pause" (להשהות את המודעה + להעלות מודעה
    חדשה נפרדת עם קריאטיב מהבנק). אם CPL מתחת/שווה לסף -> "ok", לא נוגעים (רווחית).
    אם אין בכלל לידים בטווח הנתונים -> "ok" (לא בטווח הכלל הזה).
    """
    if threshold is None:
        threshold = config.CPL_THRESHOLD

    ad_id = insight_row["ad_id"]
    ad_name = insight_row.get("ad_name", ad_id)
    spend = float(insight_row.get("spend", 0) or 0)
    leads = insights.extract_leads(insight_row)
    cpl = (spend / leads) if leads > 0 else None

    decision = "ok"
    if cpl is not None and cpl > threshold:
        decision = "rotate_and_pause"
        reason = f"עלות לליד {cpl:.2f}₪ מעל הסף של {threshold:.2f}₪"
    elif cpl is not None:
        reason = f"עלות לליד {cpl:.2f}₪ מתחת לסף - המודעה רווחית, לא נוגעים"
    else:
        reason = "אין לידים בטווח הנתונים - לא נכלל בבדיקת CPL"

    return {
        "ad_id": ad_id,
        "ad_name": ad_name,
        "spend": round(spend, 2),
        "leads": leads,
        "cost_per_lead": round(cpl, 2) if cpl is not None else None,
        "decision": decision,
        "reason": reason,
    }


def evaluate_account_cpl(insight_rows: list[dict], threshold: float = None) -> list[dict]:
    """מריץ evaluate_ad_cpl על כל השורות של חשבון מודעות אחד."""
    return [evaluate_ad_cpl(row, threshold) for row in insight_rows]
