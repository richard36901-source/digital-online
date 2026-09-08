# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: בודק אם config.API_VERSION (v21.0) עדיין נתמכת ע"י Meta, ע"י
פנייה עם גרסה שגויה בכוונה (v999.0) - הודעת השגיאה של Meta לרוב מפרטת את טווח
הגרסאות הנתמכות כרגע, מה שנותן תשובה ישירה בלי לנחש.

הרצה:
    python debug_check_api_version.py
"""

import json

import requests

import config


def main():
    print(f"הגרסה הנוכחית בקוד: {config.API_VERSION}\n")

    print("--- בודק עם גרסה שגויה בכוונה (v999.0) - כדי לראות אם Meta מפרטת גרסאות נתמכות ---")
    resp = requests.get("https://graph.facebook.com/v999.0/me", params={
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

    print(f"\n--- בודק אם {config.API_VERSION} עצמה מחזירה שגיאת גרסה לא נתמכת ---")
    resp2 = requests.get(f"https://graph.facebook.com/{config.API_VERSION}/me", params={
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    print(json.dumps(resp2.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
