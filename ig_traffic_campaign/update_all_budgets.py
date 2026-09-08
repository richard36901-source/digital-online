# -*- coding: utf-8 -*-
"""
מעדכן את התקציב היומי של כל ה-Ad Sets הקיימים בקמפיין (config.CAMPAIGN_NAME) לערך
הנוכחי ב-config.DAILY_BUDGET_AGOROT_PER_ADSET. משמש אחרי שינוי תקציב ב-config.py,
כדי להחיל אותו גם על סטים שכבר נוצרו (שינוי ב-config.py משפיע רק על סטים חדשים).

הרצה:
    python update_all_budgets.py
"""

import sys

import requests

import actions
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

    url = f"{config.GRAPH_URL}/{campaign['id']}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){id,name,daily_budget}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה בשליפת הסטים: {data['error']}")
        sys.exit(1)

    adsets = data.get("adsets", {}).get("data", [])
    new_budget_ils = config.DAILY_BUDGET_AGOROT_PER_ADSET / 100
    print(f"מעדכן {len(adsets)} Ad Sets לתקציב יומי חדש: {new_budget_ils:.2f} ש\"ח\n")

    for adset in adsets:
        current_ils = int(adset.get("daily_budget") or 0) / 100
        if current_ils == new_budget_ils:
            print(f"'{adset['name']}' - כבר בתקציב הנכון ({current_ils:.2f} ש\"ח), מדלג.")
            continue
        try:
            actions.update_adset_budget(adset["id"], new_budget_ils)
            print(f"✅ '{adset['name']}': {current_ils:.2f} -> {new_budget_ils:.2f} ש\"ח")
        except RuntimeError as e:
            print(f"❌ '{adset['name']}' נכשל: {e}")


if __name__ == "__main__":
    main()
