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

    campaign_id = actions.create_campaign(advertiser_id, config.CAMPAIGN_NAME)
    logger.print_and_log({
        "level": "action",
        "action": "create_campaign",
        "campaign_id": campaign_id,
        "campaign_name": config.CAMPAIGN_NAME,
        "dry_run": config.DRY_RUN,
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

        adgroup_id = actions.create_adgroup(
            advertiser_id=advertiser_id,
            campaign_id=campaign_id,
            adgroup_name=adgroup_name,
            daily_budget=config.DAILY_BUDGET_PER_VIDEO_ILS,
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
            "daily_budget_ils": config.DAILY_BUDGET_PER_VIDEO_ILS,
            "destination_url": config.DESTINATION_URL,
            "dry_run": config.DRY_RUN,
        })

    print("\nהשקת הקמפיין הושלמה." + (" (DRY RUN - לא נוצר שום דבר אמיתי ב-TikTok)" if config.DRY_RUN else ""))
