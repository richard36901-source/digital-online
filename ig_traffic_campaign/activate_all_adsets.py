# -*- coding: utf-8 -*-
"""
מפעיל בבת אחת את כל 13 ה-Ad Sets בקמפיין (config.CAMPAIGN_NAME) ממצב PAUSED ל-ACTIVE.
מיועד להרצה חד-פעמית אחרי שעברת ידנית על כל הסטים ב-Ads Manager ואישרת שהם תקינים.

הרצה:
    python activate_all_adsets.py
"""

import sys

import requests

import config
import insights


def main():
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר META_ACCESS_TOKEN.")
        sys.exit(1)

    campaign = insights.find_campaign()
    if not campaign:
        print(f"שגיאה: לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}'.")
        sys.exit(1)

    campaign_id = campaign["id"]
    print(f"קמפיין: {campaign_id} ({campaign.get('objective')})")

    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){id,name,status}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה בשליפת הסטים: {data['error']}")
        sys.exit(1)

    adsets = data.get("adsets", {}).get("data", [])
    paused = [a for a in adsets if a.get("status") == "PAUSED"]
    print(f"נמצאו {len(adsets)} Ad Sets, מתוכם {len(paused)} במצב PAUSED.\n")

    if not paused:
        print("אין מה להפעיל - כל הסטים כבר לא PAUSED.")
        return

    # קודם מפעילים את הקמפיין עצמו (גם הוא PAUSED) - אחרת הפעלת הסטים לא תספיק.
    if campaign.get("status") != "ACTIVE" and campaign.get("objective"):
        camp_resp = requests.post(url, data={
            "status": "ACTIVE",
            "access_token": config.ACCESS_TOKEN,
        }, timeout=30)
        camp_data = camp_resp.json()
        if "error" in camp_data:
            print(f"שגיאה בהפעלת הקמפיין: {camp_data['error']}")
            sys.exit(1)
        print("הקמפיין הופעל (ACTIVE).")

    activated, failed = [], []
    for adset in paused:
        adset_url = f"{config.GRAPH_URL}/{adset['id']}"
        r = requests.post(adset_url, data={
            "status": "ACTIVE",
            "access_token": config.ACCESS_TOKEN,
        }, timeout=30)
        d = r.json()
        if "error" in d:
            print(f"❌ נכשל: '{adset['name']}' - {d['error']}")
            failed.append(adset["name"])
        else:
            print(f"✅ הופעל: '{adset['name']}'")
            activated.append(adset["name"])

    print(f"\n=== סיכום ===\nהופעלו: {len(activated)}/{len(paused)}")
    if failed:
        print(f"נכשלו: {failed}")


if __name__ == "__main__":
    main()
