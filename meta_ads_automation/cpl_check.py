"""
בדיקה תלת-יומית לפי עלות לליד (CPL): לכל מודעה בכל חשבון מודעות (config.AD_ACCOUNTS),
אם עלות הליד מעל config.CPL_THRESHOLD - משהים את המודעה ומעלים מודעה חדשה נפרדת עם
קריאטיב מהבנק (creative_bank, כולל fallback לבנק המשותף _common).
מודעות עם עלות לליד מתחת לסף לא נוגעים בהן - הן נחשבות רווחיות.

נפרד מ-main.py (שמריץ מדי יום את מנוע הכללים המבוסס-ROAS) - זו בדיקה משלימה, ממוקדת
עלות-לליד בלבד, שרצה בקצב איטי יותר (כל 3 ימים).

הרצה: python cpl_check.py
מומלץ להריץ כל 3 ימים דרך GitHub Actions (ראו .github/workflows/cpl-rotation-check.yml).
"""

import sys

import actions
import config
import creative_rotation
import insights
import logger
import rules


def process_account(client_name: str, ad_account_id: str) -> None:
    logger.print_and_log({
        "level": "info",
        "client": client_name,
        "ad_account_id": ad_account_id,
        "message": "בדיקת עלות-לליד תלת-יומית מתחילה",
        "dry_run": config.DRY_RUN,
        "threshold": config.CPL_THRESHOLD,
    })

    try:
        insight_rows = insights.fetch_ad_insights(ad_account_id)
    except Exception as e:
        logger.print_and_log({
            "level": "error",
            "client": client_name,
            "ad_account_id": ad_account_id,
            "message": f"נכשל במשיכת נתונים: {e}",
        })
        return

    evaluations = rules.evaluate_account_cpl(insight_rows)

    for ev in evaluations:
        logger.print_and_log({
            "level": "decision",
            "client": client_name,
            "ad_id": ev["ad_id"],
            "ad_name": ev["ad_name"],
            "spend": ev["spend"],
            "leads": ev["leads"],
            "cost_per_lead": ev["cost_per_lead"],
            "decision": ev["decision"],
            "reason": ev["reason"],
        })

        if ev["decision"] != "rotate_and_pause":
            continue

        # מוצאים adset_id של המודעה מתוך שורת ה-insight המקורית (נשלף יחד עם spend/leads)
        row = next((r for r in insight_rows if r.get("ad_id") == ev["ad_id"]), None)
        adset_id = row.get("adset_id") if row else None
        if not adset_id:
            logger.print_and_log({
                "level": "warning",
                "client": client_name,
                "ad_id": ev["ad_id"],
                "message": "לא נמצא adset_id למודעה - מדלגים על רוטציה",
            })
            continue

        creative = creative_rotation.pick_next_creative(client_name, ev["ad_id"])
        if creative is None:
            logger.print_and_log({
                "level": "warning",
                "client": client_name,
                "ad_id": ev["ad_id"],
                "message": "אין קריאטיבים בבנק (לא ללקוח ולא ב-_common המשותף) - יש להוסיף קבצים ל-creative_bank",
            })
            continue

        image_hash = creative_rotation.upload_image(ad_account_id, creative["image_path"])
        new_creative_id = actions.create_ad_creative(
            ad_account_id=ad_account_id,
            name=f"cpl-rotate-{ev['ad_id']}",
            page_id=config.PAGE_IDS.get(client_name, ""),
            image_hash=image_hash,
            message=creative["message"],
            headline=creative["headline"],
            link=creative["link"],
        )
        new_ad_result = actions.create_ad(
            ad_account_id=ad_account_id,
            adset_id=adset_id,
            name=f"cpl-rotate-of-{ev['ad_id']}",
            creative_id=new_creative_id,
            status="ACTIVE",
        )
        pause_result = actions.pause_ad(ev["ad_id"])

        logger.print_and_log({
            "level": "action",
            "client": client_name,
            "old_ad_id": ev["ad_id"],
            "action": "rotate_and_pause",
            "cost_per_lead": ev["cost_per_lead"],
            "new_ad": new_ad_result,
            "pause_old": pause_result,
            "new_image": str(creative["image_path"]),
            "dry_run": config.DRY_RUN,
        })


def main():
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר META_ACCESS_TOKEN. ערוך את config.py או הגדר משתנה סביבה.")
        sys.exit(1)

    for client_name, ad_account_id in config.AD_ACCOUNTS.items():
        process_account(client_name, ad_account_id)

    print("\nבדיקת CPL תלת-יומית הושלמה." + (" (DRY RUN - לא בוצעו שינויים אמיתיים)" if config.DRY_RUN else ""))


if __name__ == "__main__":
    main()
