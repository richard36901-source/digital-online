# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: בודק אם לטוקן שלנו (System User / Automation bot) יש בכלל גישה
לדף הפייסבוק PAGE_ID (1067237409815794) שאותו אנחנו שולחים ב-promoted_object.
אותה תבנית תקלה בדיוק חזרה על עצמה כבר פעם אחת בפרויקט הזה - לחשבון האינסטגרם
ben_nahum_1 היה צריך הקצאת גישה מפורשת ב-Business Settings לפני שה-API הצליח
לראות אותו, למרות שהיתה גישה לחשבון המודעות עצמו. ייתכן שאותו דבר קורה כאן עם הדף.

הרצה:
    python debug_check_page_access.py
"""

import json

import requests

import config


def main():
    print(f"בודק גישה לדף {config.PAGE_ID}...")
    url = f"{config.GRAPH_URL}/{config.PAGE_ID}"
    resp = requests.get(url, params={
        "fields": "id,name",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    if "error" in data:
        print("\n❌ אין גישה לדף הזה עם הטוקן הנוכחי - זה כנראה השורש של השגיאה "
              "ב-create_ad_set. יש להוסיף גישה לדף הזה ל-System User/Automation bot "
              "ב-Business Settings -> Users -> System Users -> [הבוט] -> Assign Assets "
              "-> Pages, ולוודא הרשאת 'Manage Page'/'Advertise'.")
    else:
        print("\n✅ יש גישה לדף. אם create_ad_set עדיין נכשל - הבעיה כנראה לא כאן.")


if __name__ == "__main__":
    main()
