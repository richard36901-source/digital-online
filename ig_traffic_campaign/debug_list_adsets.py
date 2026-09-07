# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי (לא חלק מהזרימה הרגילה): מדפיס את כל ה-Ad Sets הקיימים בחשבון
act_<AD_ACCOUNT_ID>, כולל campaign objective, optimization_goal, destination_type,
promoted_object - כדי למצוא דוגמה אמיתית ותקינה של קמפיין שכבר עובד עם ביקורים
בפרופיל אינסטגרם (או Engagement דומה), ולהעתיק ממנה את הערכים המדויקים ל-config.py.

הרצה:
    python debug_list_adsets.py
"""

import json

import requests

import config


def main():
    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/adsets"
    resp = requests.get(url, params={
        "fields": "id,name,status,optimization_goal,destination_type,billing_event,"
                  "promoted_object,campaign{id,name,objective}",
        "limit": 200,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה: {data['error']}")
        return

    for adset in data.get("data", []):
        campaign = adset.get("campaign", {})
        print(json.dumps({
            "adset_id": adset.get("id"),
            "adset_name": adset.get("name"),
            "status": adset.get("status"),
            "campaign_name": campaign.get("name"),
            "campaign_objective": campaign.get("objective"),
            "optimization_goal": adset.get("optimization_goal"),
            "destination_type": adset.get("destination_type"),
            "billing_event": adset.get("billing_event"),
            "promoted_object": adset.get("promoted_object"),
        }, ensure_ascii=False, indent=2))
        print("---")


if __name__ == "__main__":
    main()
