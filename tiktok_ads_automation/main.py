"""
נקודת הכניסה לאוטומציה.

שימוש:
  python main.py authorize          - שלב חד-פעמי: מדפיס קישור הרשאה, מבקש להדביק את ה-auth_code שחוזר
  python main.py lookup-locations "ישראל"  - מחפש location_id לטירגוט (למילוי TARGETING_LOCATION_IDS)
  python main.py launch             - יוצר קמפיין חדש מ-creative_bank/instagram_promo/ (ראו campaign_launch.py)
  python main.py dashboard          - מרענן דשבורד ביצועים (performance_dashboard.html) - אילו סרטונים מתבלטים
  python main.py                    - מריץ על כל חשבונות המפרסם ב-config.ADVERTISER_ACCOUNTS:
                                         1. מושך ביצועים (insights)
                                         2. מפעיל את מנוע הכללים (rules)
                                         3. מבצע פעולות (pause / rotate_creative) - או רק רושם, אם DRY_RUN=True
                                         4. רושם הכל ל-log

מומלץ להריץ קודם עם config.DRY_RUN=True, ורק אחרי בדיקה לעבור ל-DRY_RUN=False (ראו README.md).
מומלץ להריץ דרך cron פעם ביום.
"""

import json
import sys

import actions
import auth
import campaign_launch
import config
import creative_rotation
import dashboard
import insights
import locations
import logger
import rules


def cmd_lookup_locations(query: str):
    matches = locations.search_locations(query)
    if not matches:
        print(f"לא נמצאו מיקומים תואמים ל-'{query}'. הנה דגימה גולמית מהתגובה של TikTok, כדי שנראה את המבנה האמיתי:\n")
        print(locations.debug_dump())
        return
    for m in matches:
        if "location_id" in m and "name" in m:
            level = f" ({m['level']})" if "level" in m else ""
            print(f"{m['location_id']}\t{m['name']}{level}")
        else:
            print(json.dumps(m, ensure_ascii=False))
    print("\nהעתיקו את ה-location_id הרצוי (בד\"כ level=COUNTRY) ל-config.TARGETING_LOCATION_IDS.")


def cmd_launch():
    if not config.ADVERTISER_ACCOUNTS:
        print("שגיאה: אין חשבונות מפרסם ב-config.ADVERTISER_ACCOUNTS.")
        sys.exit(1)
    advertiser_id = next(iter(config.ADVERTISER_ACCOUNTS.values()))
    campaign_launch.launch(advertiser_id)


def cmd_dashboard():
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר TIKTOK_ADS_ACCESS_TOKEN. הריצו קודם: python main.py authorize")
        sys.exit(1)
    path = dashboard.generate_dashboard()
    print(f"הדשבורד עודכן: {path}\nפתחו את הקובץ בדפדפן כדי לראות אילו מודעות מתבלטות.")


def cmd_authorize():
    if config.APP_ID in ("PASTE_YOUR_APP_ID_HERE", "", None):
        print("שגיאה: לא הוגדר TIKTOK_ADS_APP_ID. ערוך/י את config.py או הגדר משתני סביבה.")
        sys.exit(1)

    url = auth.build_authorize_url()
    print("פתח/י את הקישור הבא בדפדפן, אשר/י גישה לחשבון המפרסם, והדביק/י כאן את ה-auth_code שחוזר ב-URL של ה-redirect:\n")
    print(url)
    auth_code = input("\nauth_code: ").strip()
    tokens = auth.exchange_code_for_token(auth_code)
    logger.print_and_log({"level": "info", "message": "הרשאת TikTok Ads הושלמה בהצלחה", "scope": tokens.get("scope")})
    print(f"\nהצלחה! הטוקן נשמר ב-{auth.TOKEN_FILE}. העתק/י אותו ל-TIKTOK_ADS_ACCESS_TOKEN ואפשר להריץ: python main.py")


def process_account(client_name: str, advertiser_id: str) -> None:
    logger.print_and_log({
        "level": "info",
        "client": client_name,
        "advertiser_id": advertiser_id,
        "message": "מתחיל בדיקה יומית",
        "dry_run": config.DRY_RUN,
    })

    try:
        insight_rows = insights.fetch_ad_insights(advertiser_id)
    except Exception as e:
        logger.print_and_log({
            "level": "error",
            "client": client_name,
            "advertiser_id": advertiser_id,
            "message": f"נכשל במשיכת נתונים: {e}",
        })
        return

    evaluations = rules.evaluate_account(advertiser_id, insight_rows)

    for ev in evaluations:
        logger.print_and_log({
            "level": "decision",
            "client": client_name,
            "ad_id": ev["ad_id"],
            "ad_name": ev["ad_name"],
            "spend": ev["spend"],
            "roas": ev["roas"],
            "conversions": ev["conversions"],
            "decision": ev["decision"],
            "reason": ev["reason"],
        })

        if ev["decision"] == "pause":
            result = actions.pause_ad(advertiser_id, ev["ad_id"])
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

            video_id = actions.upload_video(advertiser_id, creative["video_path"])
            result = actions.update_ad_creative(
                advertiser_id=advertiser_id,
                ad_id=ev["ad_id"],
                video_id=video_id,
                ad_text=creative["ad_text"],
            )
            logger.print_and_log({
                "level": "action",
                "client": client_name,
                "ad_id": ev["ad_id"],
                "action": "rotate_creative",
                "new_video": str(creative["video_path"]),
                "dry_run": config.DRY_RUN,
                "result": result,
            })


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "authorize":
        cmd_authorize()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "lookup-locations":
        if len(sys.argv) < 3:
            print('שימוש: python main.py lookup-locations "ישראל"')
            sys.exit(1)
        cmd_lookup_locations(sys.argv[2])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "launch":
        cmd_launch()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        cmd_dashboard()
        return

    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר TIKTOK_ADS_ACCESS_TOKEN. הריצו קודם: python main.py authorize")
        sys.exit(1)

    for client_name, advertiser_id in config.ADVERTISER_ACCOUNTS.items():
        process_account(client_name, advertiser_id)

    print("\nהרצה הושלמה." + (" (DRY RUN - לא בוצעו שינויים אמיתיים)" if config.DRY_RUN else ""))


if __name__ == "__main__":
    main()
