# -*- coding: utf-8 -*-
"""
מעדכן Ad Sets ומודעות שכבר נוצרו (מהרצה קודמת) עם:
  1. טירגוט מדויק יותר לפי תוכן הסרטון (campaign_launch.build_targeting)
  2. קריאטיב חדש עם title/description (קריאטיבים ב-Meta הם immutable - לא ניתן
     לערוך קריאטיב קיים, אז יוצרים חדש ומעדכנים את המודעה להצביע עליו)

שומר על הטקסט האמיתי שכבר נקרא מהדרייב בהרצה המקורית (לא חוזר ל-message הגנרי
מ-config.VIDEOS) - שולף אותו מהקריאטיב הקיים לפני יצירת הקריאטיב החדש.

מיועד להרצה חד-פעמית אחרי שמילאנו IDs אמיתיים ב-config.INTEREST_IDS_BY_CATEGORY
(ראו debug_search_interests.py) - כדי לתקן Ad Sets שכבר נוצרו לפני התוספת הזו.

הרצה:
    python update_existing_ads.py
"""

import json

import requests

import campaign_launch
import config
import insights


def find_ad_for_adset(adset_id: str) -> str:
    url = f"{config.GRAPH_URL}/{adset_id}"
    resp = requests.get(url, params={
        "fields": "ads.limit(10){id}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת מודעות ל-Ad Set {adset_id}: {data['error']}")
    ads = data.get("ads", {}).get("data", [])
    if not ads:
        raise RuntimeError(f"לא נמצאה מודעה תחת Ad Set {adset_id}")
    return ads[0]["id"]


def get_existing_creative_data(ad_id: str) -> dict:
    """שולף video_id/thumbnail_url/message מהקריאטיב הקיים - כדי לשמר את הטקסט
    האמיתי שכבר נקרא מהדרייב, ולא לחזור ל-message הגנרי מ-config.VIDEOS."""
    url = f"{config.GRAPH_URL}/{ad_id}"
    resp = requests.get(url, params={
        "fields": "creative{object_story_spec}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בשליפת קריאטיב למודעה {ad_id}: {data['error']}")
    video_data = data.get("creative", {}).get("object_story_spec", {}).get("video_data", {})
    return {
        "video_id": video_data.get("video_id"),
        "thumbnail_url": video_data.get("image_url"),
        "message": video_data.get("message", ""),
    }


def update_targeting(adset_id: str, targeting: dict) -> None:
    url = f"{config.GRAPH_URL}/{adset_id}"
    resp = requests.post(url, data={
        "targeting": json.dumps(targeting),
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בעדכון טירגוט ל-Ad Set {adset_id}: {data['error']}")


def update_ad_creative(ad_id: str, creative_id: str) -> None:
    url = f"{config.GRAPH_URL}/{ad_id}"
    resp = requests.post(url, data={
        "creative": json.dumps({"creative_id": creative_id}),
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בעדכון קריאטיב למודעה {ad_id}: {data['error']}")


def main():
    campaign = insights.find_campaign()
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}'.")
        return
    campaign_id = campaign["id"]

    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){id,name}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה בשליפת Ad Sets: {data['error']}")
        return
    adsets_by_name = {a["name"]: a["id"] for a in data.get("adsets", {}).get("data", [])}

    for video in config.VIDEOS:
        name = video["ad_set_name"]
        adset_id = adsets_by_name.get(f"{name} - Ad Set")
        if not adset_id:
            print(f"[{name}] - לא נמצא Ad Set, מדלג (הרץ קודם campaign_launch.py).")
            continue

        print(f"\n[{name}]")
        try:
            ad_id = find_ad_for_adset(adset_id)
            existing = get_existing_creative_data(ad_id)
            if not existing["video_id"]:
                print("  לא נמצא video_id בקריאטיב הקיים - מדלג.")
                continue

            targeting = campaign_launch.build_targeting(video)
            print(f"  מעדכן טירגוט (קטגוריה: {video.get('category')})...")
            update_targeting(adset_id, targeting)

            print("  יוצר קריאטיב חדש עם כותרת/תיאור...")
            creative_id = campaign_launch.create_ad_creative(
                name=name,
                video_id=existing["video_id"],
                thumbnail_url=existing["thumbnail_url"],
                message=existing["message"] or video["message"],
                title=video.get("title", ""),
                description=video.get("description", ""),
            )

            print("  מעדכן את המודעה לקריאטיב החדש...")
            update_ad_creative(ad_id, creative_id)
            print("  ✅ עודכן.")
        except RuntimeError as e:
            print(f"  ❌ נכשל: {e}")


if __name__ == "__main__":
    main()
