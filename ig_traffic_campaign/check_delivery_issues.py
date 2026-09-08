# -*- coding: utf-8 -*-
"""
כלי אבחון: בודק סיבות אפשריות לכך שמודעות ACTIVE לא מקבלות שום חשיפה -
מצב חשבון המודעות (account_status, disable_reason, אמצעי תשלום), ו-issues_info/
learning_stage_info בכל Ad Set - שדות שה-API חושף אבל לא תמיד מוצגים ברור ב-UI.

הרצה:
    python check_delivery_issues.py
"""

import json

import requests

import config
import insights


def main():
    print("=== מצב חשבון המודעות ===")
    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}"
    resp = requests.get(url, params={
        "fields": "name,account_status,disable_reason,spend_cap,amount_spent,"
                  "balance,funding_source_details",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה: {data['error']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))

    print("\n=== issues_info / learning_stage_info לכל Ad Set ===")
    campaign = insights.find_campaign()
    if not campaign:
        print(f"לא נמצא קמפיין בשם '{config.CAMPAIGN_NAME}'.")
        return

    url = f"{config.GRAPH_URL}/{campaign['id']}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){name,issues_info,learning_stage_info,"
                  "effective_status,daily_budget,bid_amount}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"שגיאה: {data['error']}")
        return

    for adset in data.get("adsets", {}).get("data", []):
        print(f"\n[{adset['name']}]")
        print(f"  effective_status: {adset.get('effective_status')}")
        print(f"  daily_budget: {adset.get('daily_budget')} | bid_amount: {adset.get('bid_amount')}")
        issues = adset.get("issues_info")
        print(f"  issues_info: {issues if issues else '(אין)'}")
        learning = adset.get("learning_stage_info")
        print(f"  learning_stage_info: {learning if learning else '(אין)'}")


if __name__ == "__main__":
    main()
