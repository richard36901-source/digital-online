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

# המינימום היומי האמיתי של TikTok לכל ad group, לפי מטבע - אומת בפועל מול ה-API
# (קוד 40002: "Your budget setting must not be less than $5.00." כשניסינו $3.32).
# המשתמש בחר במפורש להשתמש במינימום הזה בדיוק (לא יותר).
KNOWN_MIN_DAILY_BUDGET = {"USD": 5.0}


def _resolve_daily_budget(advertiser_id: str) -> tuple[str, float]:
    """
    קובע את מטבע חשבון המפרסם ואת התקציב היומי בפועל לכל סרטון: ממיר את הכוונה
    בש"ח (config.DAILY_BUDGET_PER_VIDEO_ILS) למטבע החשבון, ואז מוודא שלא נופל
    מתחת למינימום האמיתי של TikTok (KNOWN_MIN_DAILY_BUDGET) - אם כן, מעלים בדיוק
    למינימום (לא יותר).
    """
    currency = actions.get_advertiser_currency(advertiser_id)
    daily_budget = actions.convert_ils_to_currency(currency, config.DAILY_BUDGET_PER_VIDEO_ILS)

    minimum = KNOWN_MIN_DAILY_BUDGET.get(currency)
    if minimum and daily_budget < minimum:
        daily_budget = minimum

    return currency, daily_budget


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
        currency, daily_budget = _resolve_daily_budget(advertiser_id)
        logger.print_and_log({
            "level": "info",
            "message": f"מטבע חשבון המפרסם: {currency}. תקציב יומי לכל סרטון: {daily_budget} {currency} "
                        f"(כוונה מקורית: {config.DAILY_BUDGET_PER_VIDEO_ILS} ILS, הועלה למינימום האמיתי של TikTok אם היה נמוך ממנו)",
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

    currency, correct_budget = _resolve_daily_budget(advertiser_id)
    logger.print_and_log({
        "level": "info",
        "message": f"מטבע חשבון המפרסם: {currency}. מתקנים את כל קבוצות המודעות ל-"
                    f"{correct_budget} {currency} ליום (המינימום האמיתי של TikTok, לפי בחירת המשתמש).",
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


def set_deeplink_for_existing_ads(advertiser_id: str) -> None:
    """
    תיקון חד-פעמי: מוסיף deep link (config.DEEPLINK_URL) לכל המודעות הקיימות תחת
    הקמפיין, כדי שיפתחו את אפליקציית אינסטגרם ישירות במקום דף אינטרנט עם "קיר" חוסם
    בדפדפן הפנימי של טיקטוק - ראו actions.update_ad_deeplink ודיון על הפער בין קליקים
    בטיקטוק לביקורי פרופיל בפועל באינסטגרם.
    """
    if config.DRY_RUN:
        raise RuntimeError("set_deeplink_for_existing_ads דורש DRY_RUN=False - זו פעולה על נתונים אמיתיים ב-TikTok.")
    if not config.DEEPLINK_URL:
        print("DESTINATION_URL הנוכחי אינו קישור לפרופיל אינסטגרם - אין deep link לחשב, מדלגים.")
        return

    existing_campaigns = insights.get_campaigns(advertiser_id)
    campaign = next((c for c in existing_campaigns if c.get("campaign_name") == config.CAMPAIGN_NAME), None)
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}' - אין מה לעדכן.")
        return
    campaign_id = campaign["campaign_id"]

    ads = insights.get_ads_for_campaign(advertiser_id, campaign_id)
    for ad in ads:
        result = actions.update_ad_deeplink(advertiser_id, ad["ad_id"], config.DEEPLINK_URL)
        logger.print_and_log({
            "level": "action",
            "action": "set_deeplink",
            "ad_id": ad["ad_id"],
            "deeplink": config.DEEPLINK_URL,
            "result": result,
        })

    print(f"\nעודכנו {len(ads)} מודעות עם deep link: {config.DEEPLINK_URL}")


# תיקון חד-פעמי: 8 הסרטונים האלה סונכרנו בהתחלה עם שמות גנריים (1.mov-8.mov) כי
# עדיין לא היה שם תוכן ידוע ב-Drive - מאז המשתמש ארגן אותם ב-Drive בתיקיות-בת עם
# שמות תוכן אמיתיים (ראו drive_sync.KNOWN_FILE_MAP המעודכן), וביקש שהשמות המוצגים
# יתאמו. ממפה שם ישן (adgroup_name קיים ב-TikTok) לשם חדש.
NUMBERED_VIDEO_RENAME_MAP = {
    "1.mov": "3 שאלות משמעות.mov",
    "2.mov": "תודעה הישרדותית תודעת הפסיכולוג תודעת מאסטר.mov",
    "3.mov": "לבטל את ההתנגדות עוד לפני שהיא צפה.mov",
    "4.mov": "שיחת מכירה זה לא חוקר ונחקר.mov",
    "5.mov": "יהיו רק 21 מיליון.mov",
    "6.mov": "גישת התלמיד.mov",
    "7.mov": "החלטות ממקום רגשי - אישיות מקדמת.mov",
    "8.mov": "פחד זה פיקציה.mov",
}


def rename_numbered_videos(advertiser_id: str) -> None:
    """
    מבצע את התיקון שמתואר ב-NUMBERED_VIDEO_RENAME_MAP: משנה בפועל ב-TikTok את שם
    קבוצת המודעות והמודעה (adgroup_name/ad_name) מהשם הגנרי הישן לשם התוכן האמיתי,
    ומעביר גם את הקובץ המקומי (אם קיים) לשם החדש.
    """
    if config.DRY_RUN:
        raise RuntimeError("rename_numbered_videos דורש DRY_RUN=False - זו פעולה על נתונים אמיתיים ב-TikTok.")

    existing_campaigns = insights.get_campaigns(advertiser_id)
    campaign = next((c for c in existing_campaigns if c.get("campaign_name") == config.CAMPAIGN_NAME), None)
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}' - אין מה לשנות.")
        return
    campaign_id = campaign["campaign_id"]

    adgroups_by_name = {ag["adgroup_name"]: ag["adgroup_id"] for ag in insights.get_adgroups(advertiser_id, campaign_id)}
    ad_id_by_adgroup = {a["adgroup_id"]: a["ad_id"] for a in insights.get_ads_for_campaign(advertiser_id, campaign_id)}

    renamed = 0
    for old_file, new_file in NUMBERED_VIDEO_RENAME_MAP.items():
        old_name = f"{config.CAMPAIGN_NAME} - {old_file}"
        new_name = f"{config.CAMPAIGN_NAME} - {new_file}"

        adgroup_id = adgroups_by_name.get(old_name)
        if not adgroup_id:
            logger.print_and_log({
                "level": "warning",
                "message": f"לא נמצאה קבוצת מודעות בשם '{old_name}' - מדלגים (אולי כבר שונתה)",
            })
            continue

        result = actions.rename_adgroup(advertiser_id, adgroup_id, new_name)
        logger.print_and_log({
            "level": "action", "action": "rename_adgroup", "adgroup_id": adgroup_id,
            "old_name": old_name, "new_name": new_name, "result": result,
        })

        ad_id = ad_id_by_adgroup.get(adgroup_id)
        if ad_id:
            result = actions.rename_ad(advertiser_id, adgroup_id, ad_id, new_name)
            logger.print_and_log({
                "level": "action", "action": "rename_ad", "ad_id": ad_id,
                "old_name": old_name, "new_name": new_name, "result": result,
            })

        old_path = VIDEOS_DIR / old_file
        new_path = VIDEOS_DIR / new_file
        if old_path.exists() and not new_path.exists():
            old_path.rename(new_path)
            print(f"קובץ מקומי שונה: {old_file} -> {new_file}")

        renamed += 1

    print(f"\nשונו {renamed} שמות. רעננו את הדשבורד/הפאנל כדי לראות את השמות החדשים.")
