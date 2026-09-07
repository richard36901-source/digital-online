# -*- coding: utf-8 -*-
"""
בונה קמפיין אחד להזרמת תנועה לפרופיל האינסטגרם (config.IG_ACTOR_ID), עם Ad Set נפרד
לכל סרטון ב-config.VIDEOS (תקציב יומי נפרד לכל סט), ומודעה אחת בכל סט.

לפני הרצה אמיתית (DRY_RUN=False):
  1. הרץ python check_permissions.py ומלא PAGE_ID / IG_ACTOR_ID ב-config.py
  2. ודא הגדרת גישה ל-Google Drive (ראו README.md)
  3. הרץ קודם עם DRY_RUN=True (ברירת המחדל) ועבור על הפלט/הלוג
  4. רק אז שנה ל-DRY_RUN=False - הכל נוצר PAUSED, אז שום דבר לא יתחיל לרוץ בפועל
     עד שתפעיל ידנית ב-Ads Manager.

הרצה:
    python campaign_launch.py
"""

import json
import sys
from pathlib import Path

import requests

import config
import drive_videos
import insights
import logger
import video_upload


def create_campaign() -> str:
    """
    יוצר את הקמפיין, אבל קודם בודק אם קמפיין בשם הזה כבר קיים (via insights.find_campaign)
    ומשתמש בו במקום ליצור כפילות - חשוב כי העלאת 13 סרטונים לוקחת זמן ורגישה לניתוקי
    רשת; בלי הבדיקה הזו, כל הרצה חוזרת אחרי כשל היתה יוצרת עוד קמפיין ריק.
    """
    if config.DRY_RUN:
        logger.print_and_log({"level": "dry_run", "action": "create_campaign", "name": config.CAMPAIGN_NAME})
        return "DRY_RUN_CAMPAIGN_ID"

    existing = insights.find_campaign()
    if existing:
        logger.print_and_log({"level": "info", "action": "reuse_campaign", "campaign_id": existing["id"]})
        return existing["id"]

    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/campaigns"
    resp = requests.post(url, data={
        "name": config.CAMPAIGN_NAME,
        "objective": config.CAMPAIGN_OBJECTIVE,
        "status": config.CREATED_STATUS,
        "special_ad_categories": json.dumps([]),
        # אין תקציב ברמת הקמפיין (Advantage Campaign Budget) בכוונה - כל תקציב הוא
        # ברמת ה-Ad Set (config.DAILY_BUDGET_AGOROT_PER_ADSET), כמו שביקשת. Meta
        # דורשת לציין את זה במפורש, אחרת מחזירה שגיאה (is_adset_budget_sharing_enabled).
        "is_adset_budget_sharing_enabled": "false",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל ביצירת הקמפיין: {data['error']}")
    campaign_id = data["id"]
    logger.print_and_log({"level": "action", "action": "create_campaign", "campaign_id": campaign_id})
    return campaign_id


def create_ad_set(campaign_id: str, name: str) -> str:
    if config.DRY_RUN:
        logger.print_and_log({"level": "dry_run", "action": "create_ad_set", "name": name, "campaign_id": campaign_id})
        return f"DRY_RUN_ADSET_ID_{name}"

    # promoted_object ברמת ה-Ad Set דורש page_id (לא instagram_actor_id!) עבור
    # optimization_goal=PROFILE_AND_PAGE_ENGAGEMENT - אומת בפועל מול טיוטת קמפיין
    # שנבנתה ידנית ב-Ads Manager (ראו ההערה ב-config.py). זיהוי הפרופיל הספציפי
    # (ben_nahum_1) נעשה ברמת הקריאטיב (object_story_spec.instagram_actor_id),
    # לא כאן.
    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/adsets"
    resp = requests.post(url, data={
        "name": f"{name} - Ad Set",
        "campaign_id": campaign_id,
        "daily_budget": config.DAILY_BUDGET_AGOROT_PER_ADSET,
        "billing_event": config.BILLING_EVENT,
        "bid_strategy": config.BID_STRATEGY,
        "optimization_goal": config.OPTIMIZATION_GOAL,
        "destination_type": config.DESTINATION_TYPE,
        "promoted_object": json.dumps({"page_id": config.PAGE_ID}),
        "targeting": json.dumps(config.TARGETING),
        "status": config.CREATED_STATUS,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(
            f"נכשל ביצירת Ad Set '{name}': {data['error']}\n"
            f"אם השגיאה נוגעת ל-optimization_goal/destination_type - הרשימה המלאה של "
            f"ערכים תקינים אמורה להופיע בהודעת השגיאה עצמה. עדכן את config.py בהתאם."
        )
    adset_id = data["id"]
    logger.print_and_log({"level": "action", "action": "create_ad_set", "name": name, "adset_id": adset_id})
    return adset_id


def create_ad_creative(name: str, video_id: str, thumbnail_url: str, message: str) -> str:
    if config.DRY_RUN:
        logger.print_and_log({"level": "dry_run", "action": "create_ad_creative", "name": name})
        return f"DRY_RUN_CREATIVE_ID_{name}"

    object_story_spec = {
        "instagram_actor_id": config.IG_ACTOR_ID,
        "video_data": {
            "video_id": video_id,
            "image_url": thumbnail_url,
            "message": message,
            "call_to_action": {"type": config.CTA_TYPE},
        },
    }
    # page_id: לא תמיד נדרש כשחשבון האינסטגרם מוקצה ישירות ל-Business Portfolio
    # (בניגוד לדף פייסבוק מקושר בדרך הישנה) - ראו check_permissions.py. כולל רק אם
    # יש ערך אמיתי ב-config; אם ה-API בכל זאת דורש אותו, השגיאה תבהיר את זה.
    if config.PAGE_ID and not config.PAGE_ID.startswith("PASTE_"):
        object_story_spec["page_id"] = config.PAGE_ID

    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/adcreatives"
    resp = requests.post(url, data={
        "name": name,
        "object_story_spec": json.dumps(object_story_spec),
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל ביצירת קריאטיב '{name}': {data['error']}")
    creative_id = data["id"]
    logger.print_and_log({"level": "action", "action": "create_ad_creative", "name": name, "creative_id": creative_id})
    return creative_id


def create_ad(adset_id: str, name: str, creative_id: str) -> str:
    if config.DRY_RUN:
        logger.print_and_log({"level": "dry_run", "action": "create_ad", "name": name, "adset_id": adset_id})
        return f"DRY_RUN_AD_ID_{name}"

    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/ads"
    resp = requests.post(url, data={
        "name": f"{name} - Ad",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": config.CREATED_STATUS,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל ביצירת מודעה '{name}': {data['error']}")
    ad_id = data["id"]
    logger.print_and_log({"level": "action", "action": "create_ad", "name": name, "ad_id": ad_id})
    return ad_id


def get_existing_adset_names(campaign_id: str) -> set:
    """שמות כל ה-Ad Sets שכבר קיימים תחת הקמפיין - כדי לדלג עליהם בהרצה חוזרת אחרי כשל."""
    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){name}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת סטים קיימים לקמפיין {campaign_id}: {data['error']}")
    return {a["name"] for a in data.get("adsets", {}).get("data", [])}


def preflight_checks() -> None:
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר META_ACCESS_TOKEN. ראה README.md.")
        sys.exit(1)
    if config.IG_ACTOR_ID.startswith("PASTE_"):
        print("שגיאה: IG_ACTOR_ID לא מולא ב-config.py. הרץ קודם: python check_permissions.py")
        sys.exit(1)
    if config.PAGE_ID.startswith("PASTE_"):
        print("אזהרה: PAGE_ID לא מולא - ממשיך בלעדיו (ייתכן שלא נדרש כשהאינסטגרם "
              "מוקצה ישירות ל-Business Portfolio). אם ה-API ידרוש אותו, תקבלו שגיאה ברורה.")


def main():
    preflight_checks()

    print(f"{'=== DRY RUN - לא יבוצע שום שינוי אמיתי ===' if config.DRY_RUN else '=== הרצה אמיתית ==='}")
    print(f"חשבון מודעות: act_{config.AD_ACCOUNT_ID} | פרופיל יעד: {config.IG_USERNAME} "
          f"(ig_actor_id={config.IG_ACTOR_ID})")
    print(f"מספר סרטונים/Ad Sets: {len(config.VIDEOS)} | תקציב יומי לכל סט: "
          f"{config.DAILY_BUDGET_AGOROT_PER_ADSET / 100:.2f} ש\"ח\n")

    print("--- שלב 1: הורדת סרטונים + טקסט מודעה מ-Google Drive ---")
    videos_data = drive_videos.ensure_videos_downloaded()

    print("\n--- שלב 2: יצירת הקמפיין ---")
    campaign_id = create_campaign()

    existing_adset_names = set() if config.DRY_RUN else get_existing_adset_names(campaign_id)

    print("\n--- שלב 3: לכל סרטון - Ad Set + קריאטיב + מודעה ---")
    created = []
    for video in config.VIDEOS:
        name = video["ad_set_name"]
        if f"{name} - Ad Set" in existing_adset_names:
            print(f"\n[{name}] - כבר קיים סט מודעות בשם הזה בקמפיין, מדלג (כנראה מהרצה קודמת).")
            continue

        print(f"\n[{name}]")
        local_path = videos_data[name]["path"]
        message = videos_data[name]["message"]

        print("  מעלה וידאו ל-Meta וממתין לעיבוד...")
        upload_result = video_upload.upload_and_prepare(local_path, name=name)

        print("  יוצר Ad Set...")
        adset_id = create_ad_set(campaign_id, name)

        print("  יוצר קריאטיב...")
        creative_id = create_ad_creative(
            name=name,
            video_id=upload_result["video_id"],
            thumbnail_url=upload_result["thumbnail_url"],
            message=message,
        )

        print("  יוצר מודעה...")
        ad_id = create_ad(adset_id, name, creative_id)

        created.append({"video": name, "adset_id": adset_id, "creative_id": creative_id, "ad_id": ad_id})

    print("\n=== סיכום ===")
    print(json.dumps({
        "dry_run": config.DRY_RUN,
        "campaign_id": campaign_id,
        "ad_sets_created": created,
    }, ensure_ascii=False, indent=2))

    if config.DRY_RUN:
        print("\nזו הייתה הרצת DRY RUN בלבד. עברו על הפלט/הלוג (config.LOG_FILE), "
              "ורק אז שנו DRY_RUN=False ב-config.py כדי ליצור בפועל.")
    else:
        print(f"\nהכל נוצר במצב {config.CREATED_STATUS} - כלום לא רץ אוטומטית. "
              "היכנסו ל-Ads Manager, עברו על כל סט/מודעה, ורק אז הפעילו ידנית את מה שנראה תקין.")


if __name__ == "__main__":
    main()
