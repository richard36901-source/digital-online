# -*- coding: utf-8 -*-
"""
בדיקת הרשאות ופרטים לפני יצירת הקמפיין - להרצה ידנית שלך, לא של Claude.

הסביבה שבה Claude מריץ קוד חסומה מגישה ל-graph.facebook.com (בדיוק כמו שמוסבר ב-
meta_ads_automation/README.md), ולכן קובץ זה חייב לרוץ אצלך (מחשב אישי / שרת / VPS)
עם גישה רגילה לאינטרנט - לא בסביבת Claude.

מה זה בודק:
  1. שהטוקן תקף ואילו הרשאות (scopes) יש לו בפועל - GET /me/permissions
  2. שיש גישה לחשבון המודעות act_330184635273905
  3. אילו דפי פייסבוק זמינים לטוקן, ולכל דף - איזה חשבון אינסטגרם עסקי מחובר אליו
     (זה כדי לזהות איזה page_id / IG actor ID שייכים בפועל ל-ben_nahum_1 - אל תנחש,
     תעתיק את הערכים הנכונים ל-config.py רק אחרי שראית את שם המשתמש המתאים בפלט).

הרצה:
    python check_permissions.py
"""

import sys

import requests

import config


def check_token_permissions() -> list:
    url = f"{config.GRAPH_URL}/me/permissions"
    resp = requests.get(url, params={"access_token": config.ACCESS_TOKEN}, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"❌ שגיאה בבדיקת הטוקן: {data['error']}")
        sys.exit(1)

    granted = [p["permission"] for p in data.get("data", []) if p.get("status") == "granted"]
    declined = [p["permission"] for p in data.get("data", []) if p.get("status") != "granted"]
    print(f"✅ הטוקן תקף. הרשאות מאושרות: {granted}")
    if declined:
        print(f"⚠️  הרשאות לא מאושרות/נדחו: {declined}")

    required = ["ads_management", "business_management"]
    missing = [p for p in required if p not in granted]
    if missing:
        print(f"❌ חסרות הרשאות קריטיות ליצירת קמפיין: {missing}")
        print("   יש להוסיף אותן ל-System User ב-Business Settings ולהנפיק טוקן חדש.")
    return granted


def check_ad_account_access() -> None:
    url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}"
    resp = requests.get(url, params={
        "fields": "name,account_status,currency",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"❌ אין גישה לחשבון act_{config.AD_ACCOUNT_ID}: {data['error']}")
        sys.exit(1)
    print(f"✅ גישה לחשבון המודעות אושרה: {data}")


def list_pages_and_instagram_accounts() -> None:
    """
    מציג כל דף פייסבוק שהטוקן יכול לנהל, וה-Instagram Business Account המחובר אליו (אם יש).
    חפש בפלט את השורה שבה username == "ben_nahum_1", והעתק את ה-page id וה-instagram id
    שלה ל-PAGE_ID ו-IG_ACTOR_ID ב-config.py.

    לנוחותך, שני ה-page_id הבאים כבר נראו בקמפיינים קיימים בחשבון act_330184635273905
    ונבדקים כאן ראשונים כמועמדים - אבל עדיין יש לוודא לפי ה-username בפלט, לא לנחש:
      - 464521926734949
      - 1067237409815794
    """
    candidate_page_ids = ["464521926734949", "1067237409815794"]

    print("\n--- דפים ידועים מקמפיינים קיימים בחשבון (מועמדים) ---")
    for page_id in candidate_page_ids:
        _print_page_ig_info(page_id)

    print("\n--- כל הדפים הזמינים לטוקן (GET /me/accounts) ---")
    url = f"{config.GRAPH_URL}/me/accounts"
    resp = requests.get(url, params={
        "fields": "id,name,instagram_business_account{id,username}",
        "access_token": config.ACCESS_TOKEN,
        "limit": 200,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"⚠️  לא ניתן היה לשלוף /me/accounts (ייתכן שזה תקין ל-System User, "
              f"ואז יש להסתמך על הרשימה הידועה למעלה): {data['error']}")
        return

    for page in data.get("data", []):
        ig = page.get("instagram_business_account")
        ig_str = f'{ig["username"]} (ig_actor_id={ig["id"]})' if ig else "אין חשבון אינסטגרם מחובר"
        print(f'  page_id={page["id"]}  name="{page["name"]}"  instagram: {ig_str}')


def _print_page_ig_info(page_id: str) -> None:
    url = f"{config.GRAPH_URL}/{page_id}"
    resp = requests.get(url, params={
        "fields": "name,instagram_business_account{id,username}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"  page_id={page_id}: ❌ {data['error']}")
        return
    ig = data.get("instagram_business_account")
    ig_str = f'{ig["username"]} (ig_actor_id={ig["id"]})' if ig else "אין חשבון אינסטגרם מחובר"
    print(f'  page_id={page_id}  name="{data.get("name")}"  instagram: {ig_str}')


def main():
    if config.ACCESS_TOKEN in ("PASTE_YOUR_TOKEN_HERE", "", None):
        print("שגיאה: לא הוגדר META_ACCESS_TOKEN. הגדר משתנה סביבה או ערוך את config.py.")
        sys.exit(1)

    print("=== 1. הרשאות הטוקן ===")
    check_token_permissions()

    print("\n=== 2. גישה לחשבון המודעות ===")
    check_ad_account_access()

    print("\n=== 3. דפים + חשבונות אינסטגרם מחוברים ===")
    list_pages_and_instagram_accounts()

    print("\nסיימת? עדכן את PAGE_ID ו-IG_ACTOR_ID ב-config.py לפני הרצת campaign_launch.py.")


if __name__ == "__main__":
    main()
