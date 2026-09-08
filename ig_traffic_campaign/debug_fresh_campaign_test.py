# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: בודק אם הבעיה ב-optimization_goal קשורה ספציפית לקמפיין הישן
שכבר קיים (120250414422080697, נוצר לפני שבועות ע"י System User), או שהיא כללית
לכל קמפיין שנוצר דרך ה-API (System User) - בלי קשר לאיזה קמפיין.

יוצר קמפיין PAUSED חדש לגמרי (זהה בהגדרותיו לקמפיין האמיתי) ומיד מנסה ליצור עליו
Ad Set יחיד עם בדיוק אותם פרמטרים כמו campaign_launch.py. שום דבר לא רץ בפועל
(PAUSED) ואפשר למחוק את הקמפיין הזה מ-Ads Manager אחרי הבדיקה.

הרצה:
    python debug_fresh_campaign_test.py
"""

import json

import requests

import config


def main():
    print("--- יוצר קמפיין טסט חדש (PAUSED) ---")
    campaign_url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/campaigns"
    campaign_resp = requests.post(campaign_url, data={
        "name": "DEBUG - קמפיין טסט זמני - למחוק",
        "objective": config.CAMPAIGN_OBJECTIVE,
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
        "is_adset_budget_sharing_enabled": "false",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    campaign_data = campaign_resp.json()
    print(json.dumps(campaign_data, ensure_ascii=False, indent=2))

    if "error" in campaign_data:
        print("\n❌ אפילו יצירת הקמפיין נכשלה - הבעיה לא ספציפית ל-ad set.")
        return

    campaign_id = campaign_data["id"]
    print(f"\n✅ קמפיין טסט נוצר: {campaign_id}")

    print("\n--- מנסה ליצור Ad Set יחיד על הקמפיין הטסט (אותם פרמטרים בדיוק) ---")
    adset_url = f"{config.GRAPH_URL}/act_{config.AD_ACCOUNT_ID}/adsets"
    adset_resp = requests.post(adset_url, data={
        "name": "DEBUG - Ad Set טסט",
        "campaign_id": campaign_id,
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
    adset_data = adset_resp.json()
    print(json.dumps(adset_data, ensure_ascii=False, indent=2))

    if "error" in adset_data:
        print("\n❌ נכשל גם על קמפיין חדש לגמרי - זו לא בעיה ספציפית לקמפיין הישן "
              "שלנו. כנראה קשור ל-System User/Automation bot עצמו, לא לקמפיין.")
    else:
        print(f"\n✅ הצליח! Ad Set: {adset_data['id']} - זו כן היתה בעיה ספציפית "
              f"לקמפיין הישן (120250414422080697). צריך ליצור קמפיין חדש לגמרי "
              f"ב-campaign_launch.py במקום לעשות reuse לישן.")

    print(f"\nניתן למחוק את קמפיין הטסט ({campaign_id}) מ-Ads Manager אחרי הבדיקה.")


if __name__ == "__main__":
    main()
