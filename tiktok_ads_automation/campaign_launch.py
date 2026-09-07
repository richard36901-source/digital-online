"""
השקת קמפיין ממומן חדש: קבוצת מודעות (ad group) נפרדת לכל סרטון בתקציב יומי עצמאי
(config.DAILY_BUDGET_PER_VIDEO_ILS), כולן תחת קמפיין משותף אחד (config.CAMPAIGN_NAME),
מפנות ל-config.DESTINATION_URL.

שימוש:
  python main.py launch

לפני הרצה אמיתית (DRY_RUN=False) יש למלא ב-config.py:
  - TARGETING_LOCATION_IDS (ראו locations.py / "python main.py lookup-locations")
  - IDENTITY_ID

מקור הסרטונים: creative_bank/instagram_promo/videos/ + מניפסט creative_bank/instagram_promo/videos.json
(רשימת {"file": "שם_קובץ.mov", "ad_text": "טקסט המודעה"}) - קובצי הווידאו עצמם לא ב-git
(כבדים מדי) - יש להוריד אותם ידנית מ-Google Drive לתיקייה הזו לפני ההרצה.
"""

import json
from pathlib import Path

import actions
import config
import insights
import logger

MANIFEST_PATH = Path(config.CREATIVE_BANK_PATH) / "instagram_promo" / "videos.json"
VIDEOS_DIR = Path(config.CREATIVE_BANK_PATH) / "instagram_promo" / "videos"


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"לא נמצא מניפסט: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def launch(advertiser_id: str) -> None:
    manifest = load_manifest()
    missing = [item["file"] for item in manifest if not (VIDEOS_DIR / item["file"]).exists()]
    if missing and not config.DRY_RUN:
        raise RuntimeError(
            f"חסרים קובצי וידאו ב-{VIDEOS_DIR}: {missing} - הורידו אותם מ-Google Drive לפני ההרצה."
        )

    # אידמפוטנטיות: אם קמפיין בשם הזה כבר קיים (למשל מהרצה קודמת שנכשלה באמצע) -
    # משתמשים בו במקום ליצור כפול. חשוב במיוחד אחרי כשל חלקי (ראו את הבאג שתוקן
    # ב-actions.create_adgroup - יצר קמפיין אמיתי, נכשל ביצירת ה-adgroup הראשון).
    existing_campaigns = insights.get_campaigns(advertiser_id) if not config.DRY_RUN else []
    existing_campaign = next((c for c in existing_campaigns if c.get("campaign_name") == config.CAMPAIGN_NAME), None)

    if existing_campaign:
        campaign_id = existing_campaign["campaign_id"]
        logger.print_and_log({
            "level": "info",
            "message": f"קמפיין '{config.CAMPAIGN_NAME}' כבר קיים - משתמשים בו במקום ליצור כפול",
            "campaign_id": campaign_id,
        })
    else:
        campaign_id = actions.create_campaign(advertiser_id, config.CAMPAIGN_NAME)
        logger.print_and_log({
            "level": "action",
            "action": "create_campaign",
            "campaign_id": campaign_id,
            "campaign_name": config.CAMPAIGN_NAME,
            "dry_run": config.DRY_RUN,
        })

    # שתי בדיקות אידמפוטנטיות נפרדות: אילו adgroup-ים כבר קיימים (לפי שם), ואילו
    # מהם כבר יש להם מודעה בפועל. ההבדל חשוב - אם ריצה קודמת נכשלה אחרי יצירת
    # ה-adgroup אבל לפני יצירת המודעה (בדיוק המצב שקרה בפועל), ה-adgroup קיים אבל
    # "יתום" (בלי מודעה) - צריך להשלים אותו (להעלות וידאו + ליצור מודעה), לא לדלג.
    existing_adgroups_by_name = {}
    adgroup_ids_with_ads = set()
    if not config.DRY_RUN:
        existing_adgroups_by_name = {ag["adgroup_name"]: ag["adgroup_id"] for ag in insights.get_adgroups(advertiser_id, campaign_id)}
        adgroup_ids_with_ads = insights.get_adgroup_ids_with_ads(advertiser_id, campaign_id)

    # שדות ה-budget ב-API הם מספרים גולמיים במטבע חשבון המפרסם, לא בהכרח ILS - אם
    # לא ממירים, "10" עלול להתפרש כ-10 דולר במקום 10 שקל (בדיוק מה שקרה בפועל).
    if config.DRY_RUN:
        currency = "ILS"
        daily_budget = config.DAILY_BUDGET_PER_VIDEO_ILS
    else:
        currency = actions.get_advertiser_currency(advertiser_id)
        daily_budget = actions.convert_ils_to_currency(currency, config.DAILY_BUDGET_PER_VIDEO_ILS)
        logger.print_and_log({
            "level": "info",
            "message": f"מטבע חשבון המפרסם: {currency}. תקציב יומי לכל סרטון: "
                        f"{config.DAILY_BUDGET_PER_VIDEO_ILS} ILS ~= {daily_budget} {currency}",
        })

    for item in manifest:
        video_path = VIDEOS_DIR / item["file"]
        adgroup_name = f"{config.CAMPAIGN_NAME} - {item['file']}"

        if not video_path.exists():
            logger.print_and_log({
                "level": "warning",
                "message": f"קובץ וידאו חסר (מדלג, DRY_RUN בלבד): {video_path}",
            })
            continue

        existing_adgroup_id = existing_adgroups_by_name.get(adgroup_name)

        if existing_adgroup_id and existing_adgroup_id in adgroup_ids_with_ads:
            logger.print_and_log({
                "level": "info",
                "message": f"'{adgroup_name}' כבר קיימת ויש לה מודעה - מדלגים (לא יוצרים כפול)",
            })
            continue

        if existing_adgroup_id:
            adgroup_id = existing_adgroup_id
            logger.print_and_log({
                "level": "info",
                "message": f"'{adgroup_name}' קיימת אבל בלי מודעה (מריצה קודמת שנכשלה) - משלימים אותה",
                "adgroup_id": adgroup_id,
            })
        else:
            adgroup_id = actions.create_adgroup(
                advertiser_id=advertiser_id,
                campaign_id=campaign_id,
                adgroup_name=adgroup_name,
                daily_budget=daily_budget,
            )

        video_id = actions.upload_video(advertiser_id, video_path)
        ad_id = actions.create_ad(
            advertiser_id=advertiser_id,
            adgroup_id=adgroup_id,
            ad_name=adgroup_name,
            video_id=video_id,
            ad_text=item["ad_text"],
        )

        logger.print_and_log({
            "level": "action",
            "action": "launch_video_ad",
            "file": item["file"],
            "adgroup_id": adgroup_id,
            "video_id": video_id,
            "ad_id": ad_id,
            "daily_budget": daily_budget,
            "currency": currency,
            "daily_budget_ils_intended": config.DAILY_BUDGET_PER_VIDEO_ILS,
            "destination_url": config.DESTINATION_URL,
            "dry_run": config.DRY_RUN,
        })

    print("\nהשקת הקמפיין הושלמה." + (" (DRY RUN - לא נוצר שום דבר אמיתי ב-TikTok)" if config.DRY_RUN else ""))


def fix_existing_budgets(advertiser_id: str) -> None:
    """
    תיקון חד-פעמי: קבוצות המודעות שכבר נוצרו קיבלו budget=10 גולמי, אבל חשבון
    המפרסם במטבע USD (לא ILS כפי שהונח) - אז בפועל הן מוגדרות ל-10 דולר ליום,
    לא 10 שקל. מוצא את כל קבוצות המודעות תחת הקמפיין ומעדכן את התקציב שלהן
    לערך הנכון (10 ש"ח מומר למטבע החשבון בשער חליפין עדכני).
    """
    if config.DRY_RUN:
        raise RuntimeError("fix_existing_budgets דורש DRY_RUN=False - זו פעולה על נתונים אמיתיים ב-TikTok.")

    existing_campaigns = insights.get_campaigns(advertiser_id)
    campaign = next((c for c in existing_campaigns if c.get("campaign_name") == config.CAMPAIGN_NAME), None)
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}' - אין מה לתקן.")
        return
    campaign_id = campaign["campaign_id"]

    currency = actions.get_advertiser_currency(advertiser_id)
    correct_budget = actions.convert_ils_to_currency(currency, config.DAILY_BUDGET_PER_VIDEO_ILS)
    logger.print_and_log({
        "level": "info",
        "message": f"מטבע חשבון המפרסם: {currency}. מתקנים את כל קבוצות המודעות ל-"
                    f"{correct_budget} {currency} ליום (= {config.DAILY_BUDGET_PER_VIDEO_ILS} ש\"ח).",
    })

    adgroups = insights.get_adgroups(advertiser_id, campaign_id)
    for ag in adgroups:
        result = actions.update_adgroup_budget(advertiser_id, ag["adgroup_id"], correct_budget)
        logger.print_and_log({
            "level": "action",
            "action": "fix_budget",
            "adgroup_id": ag["adgroup_id"],
            "adgroup_name": ag.get("adgroup_name"),
            "new_budget": correct_budget,
            "currency": currency,
            "result": result,
        })

    print(f"\nתוקנו {len(adgroups)} קבוצות מודעות לתקציב {correct_budget} {currency} ליום.")
