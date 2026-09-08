# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: בודק אם יצירת Ad Set עם optimization_goal=PROFILE_AND_PAGE_ENGAGEMENT
מצליחה עם טוקן משתמש אישי (לא System User/Automation bot) - כדי לבודד אם הבעיה
היא הרשאה/גישה ל-feature ספציפית ל-System User, בניגוד למשתמש אנושי (בדיוק כמו
שהצליח ב-Ads Manager בדפדפן).

לא נוגע ב-config.ACCESS_TOKEN הרגיל בכלל - קורא טוקן נפרד ממשתנה סביבה USER_ACCESS_TOKEN
כדי לא לבלבל בין השניים.

איך משיגים טוקן משתמש אישי לבדיקה חד-פעמית:
  1. גשו ל-https://developers.facebook.com/tools/explorer/
  2. בתפריט "Meta App" למעלה - בחרו את האפליקציה שדרכה הוקם ה-System User (אם לא
     בטוחים איזו, בדקו ב-Business Settings -> Apps).
  3. ודאו שנבחר "User Token" (לא Page Token).
  4. לחצו על "Permissions", הוסיפו: ads_management, business_management.
  5. לחצו "Generate Access Token" ואשרו את ההתחברות בחלון שנפתח (עם המשתמש שלכם -
     yahavmor77@gmail.com - זה שבאמת בנה את הטיוטה ב-Ads Manager).
  6. העתיקו את הטוקן שנוצר (תקף לשעה-שעתיים בלבד - זה בסדר, זו בדיקה חד-פעמית).

הרצה (בלי לשים את הטוקן כאן בקוד, ובלי להדביק אותו בצ'אט):
    set USER_ACCESS_TOKEN=הטוקן_האישי_שהעתקת
    python debug_test_with_user_token.py
"""

import json
import os
import sys

import requests

import config

TEST_CAMPAIGN_ID = "120250423680850697"  # מ-debug_fresh_campaign_test.py - קמפיין טסט PAUSED זמני


def main():
    user_token = os.environ.get("USER_ACCESS_TOKEN")
    if not user_token:
        print("שגיאה: לא הוגדר USER_ACCESS_TOKEN. ראו הוראות בראש הקובץ.")
        sys.exit(1)

    print(f"--- מנסה ליצור Ad Set על קמפיין הטסט ({TEST_CAMPAIGN_ID}) עם טוקן משתמש אישי ---")
    adset_url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/adsets"
    resp = requests.post(adset_url, data={
        "name": "DEBUG - Ad Set טסט (טוקן אישי)",
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
        "access_token": user_token,
    }, timeout=30)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    if "error" in data:
        print("\n❌ נכשל גם עם טוקן אישי - זו כנראה לא בעיית System User. צריך "
              "לחשוב הלאה.")
    else:
        print(f"\n✅ הצליח! Ad Set: {data['id']} - זו בהחלט בעיית הרשאה/feature-gating "
              f"ספציפית ל-System User (Automation bot), לא לחשבון המודעות עצמו. "
              f"צריך למצוא איך לתת ל-System User גישה לאותו feature, או לבדוק אם "
              f"יש דרך אחרת ל-optimization_goal שכן עובדת דרך System User.")


if __name__ == "__main__":
    main()
