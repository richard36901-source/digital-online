# -*- coding: utf-8 -*-
"""
כלי אבחון: מציג את הסטטוס המדויק (status + effective_status) של הקמפיין, כל
ה-Ad Sets וכל המודעות - effective_status הוא זה שמראה אם מודעה עדיין בבדיקה
(PENDING_REVIEW), נדחתה (DISAPPROVED), או פעילה בפועל (ACTIVE) - בניגוד ל-status
הרגיל שרק מראה מה *אנחנו* הגדרנו (ACTIVE/PAUSED), לא מה Meta בפועל מאשרת.

הרצה:
    python check_campaign_status.py
"""

import json

import requests

import config
import insights


def main():
    campaign = insights.find_campaign()
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}'.")
        return

    url = f"{config.GRAPH_URL}/{campaign['id']}"
    resp = requests.get(url, params={
        "fields": "name,status,effective_status,"
                  "adsets.limit(200){name,status,effective_status,"
                  "ads.limit(5){name,status,effective_status}}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה: {data['error']}")
        return

    print(f"קמפיין: {data.get('name')} | status={data.get('status')} "
          f"effective_status={data.get('effective_status')}\n")

    for adset in data.get("adsets", {}).get("data", []):
        print(f"[{adset['name']}] status={adset.get('status')} "
              f"effective_status={adset.get('effective_status')}")
        for ad in adset.get("ads", {}).get("data", []):
            print(f"    מודעה: status={ad.get('status')} "
                  f"effective_status={ad.get('effective_status')}")


if __name__ == "__main__":
    main()
