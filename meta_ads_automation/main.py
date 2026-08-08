"""
נקודת הכניסה היומית לאוטומציה.
מריץ על כל חשבונות הלקוחות ב-config.AD_ACCOUNTS:
  1. מושך ביצועים (insights)
  2. מפעיל את מנוע הכללים (rules)
  3. מבצע פעולות (pause / rotate_creative) - או רק רושם, אם DRY_RUN=True
  4. רושם הכל ל-log
  5. מעדכן את דשבורד god_manager.html (כולל גם את החשבון האישי, קריאה-בלבד)

הרצה: python main.py
מומלץ להריץ דרך cron פעם ביום (ראו README.md).
"""

import sys

import actions
import config
import creative_rotation
import dashboard
import insights
import logger
import rules


def process_account(client_name: str, ad_account_id: str) -> None:
    logger.print_and_log({
        "level": "info",
        "client": client_name,
        "ad_account_id": ad_account_id,
        "message": "מתחיל בדיקה יומית",
        "dry_run": config.DRY_RUN,
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

    evaluations = rules.evaluate_account(insight_rows)

    for ev in evaluations:
        logger.print_and_log({
            "level": "decision",
            "client": client_name,
            "ad_id": ev["ad_id"],
            "ad_name": ev["ad_name"],
            "spend": ev["spend"],
            "roas": ev["roas"],
            "leads": ev["leads"],
            "decision": ev["decision"],
            "reason": ev["reason"],
        })

        if ev["decision"] == "pause":
            result = actions.pause_ad(ev["ad_id"])
            logger.print_and_log({
                "level": "action",
                "client": client_name,
                "ad_id": ev["ad_id"],
                "action": "pause",
                "dry_run": config.DRY_RUN,
                "result": result,
            })

        elif ev["decision"] == "rotate_creative":
            creative = creative_rotation.pick_next_creative(client_name, ev["ad_id"])
            if creative is None:
                logger.print_and_log({
                    "level": "warning",
                    "client": client_name,
                    "ad_id": ev["ad_id"],
                    "message": "אין קריאטיבים בספריית הבנק עבור לקוח זה - יש להוסיף קבצים ל-creative_bank",
                })
                continue

            image_hash = creative_rotation.upload_image(ad_account_id, creative["image_path"])
            new_creative_id = actions.create_ad_creative(
                ad_account_id=ad_account_id,
                name=f"auto-rotate-{ev['ad_id']}",
                page_id=config.PAGE_IDS[client_name],
                image_hash=image_hash,
                message=creative["message"],
                headline=creative["headline"],
                link=creative["link"],
            )
            result = actions.swap_ad_creative(ev["ad_id"], new_creative_id)
            logger.print_and_log({
                "level": "action",
                "client": client_name,
                "ad_id": ev["ad_id"],
                "action": "rotate_creative",
                "new_image": str(creative["image_path"]),
                "dry_run": config.DRY_RUN,
                "result": result,
            })


def main():
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר META_ACCESS_TOKEN. ערוך את config.py או הגדר משתנה סביבה.")
        sys.exit(1)

    for client_name, ad_account_id in config.AD_ACCOUNTS.items():
        process_account(client_name, ad_account_id)

    print("\nהרצה הושלמה." + (" (DRY RUN - לא בוצעו שינויים אמיתיים)" if config.DRY_RUN else ""))

    try:
        dashboard_path = dashboard.generate_dashboard()
        logger.print_and_log({
            "level": "info",
            "message": "god_manager עודכן",
            "path": dashboard_path,
        })
        print(f"\ngod_manager עודכן: {dashboard_path}")
    except Exception as e:
        logger.print_and_log({
            "level": "error",
            "message": f"נכשל עדכון god_manager: {e}",
        })


if __name__ == "__main__":
    main()
