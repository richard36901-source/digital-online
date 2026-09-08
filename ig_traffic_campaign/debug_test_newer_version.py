# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: בודק אם יצירת Ad Set עם optimization_goal=PROFILE_AND_PAGE_ENGAGEMENT
מצליחה מול גרסת API חדשה יותר (v25.0 - זו שה-Graph API Explorer של Meta עצמו בחר
כברירת מחדל) במקום v21.0 שבה כל הבדיקות עד עכשיו נכשלו. גם System User וגם טוקן
אישי נכשלו זהה על v21.0 - הגרסה היא המשתנה האחרון שלא נבדק.

הרצה:
    python debug_test_newer_version.py
"""

import json

import requests

import config

NEWER_VERSION = "v25.0"
TEST_CAMPAIGN_ID = "120250423680850697"  # מ-debug_fresh_campaign_test.py


def main():
    newer_url = f"https://graph.facebook.com/{NEWER_VERSION}"
    print(f"--- מנסה ליצור Ad Set על קמפיין הטסט ({TEST_CAMPAIGN_ID}) עם {NEWER_VERSION} ---")

    resp = requests.post(f"{newer_url}/act_{config.AD_ACCOUNT_ID}/adsets", data={
        "name": f"DEBUG - Ad Set טסט ({NEWER_VERSION})",
        "campaign_id": TEST_CAMPAIGN_ID,
        "daily_budget": config.DAILY_BUDGET_AGOROT_PER_ADSET,
        "billing_event": config.BILLING_EVENT,
        "bid_strategy": config.BID_STRATEGY,
        "bid_amount": config.BID_AMOUNT_AGOROT,
        "optimization_goal": config.OPTIMIZATION_GOAL,
        "destination_type": config.DESTINATION_TYPE,
        "promoted_object": json.dumps({"page_id": config.PAGE_ID, "smart_pse_enabled": False}),
        "targeting": json.dumps(config.TARGETING),
        "status": "PAUSED",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    if "error" in data:
        print(f"\n❌ נכשל גם עם {NEWER_VERSION} - הגרסה כנראה לא הבעיה.")
    else:
        print(f"\n✅ הצליח! Ad Set: {data['id']} - זו בהחלט היתה בעיית גרסת API "
              f"(v21.0 מיושנת מדי ל-optimization_goal הזה). צריך לעדכן את "
              f"config.API_VERSION ל-{NEWER_VERSION} (או קרוב לזה) בכל הפרויקט.")


if __name__ == "__main__":
    main()
