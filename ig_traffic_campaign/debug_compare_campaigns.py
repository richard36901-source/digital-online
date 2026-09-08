# -*- coding: utf-8 -*-
"""
כלי אבחון חד-פעמי: משווה בין הקמפיין/סט שלנו (שכושל) לבין קמפיין הטיוטה שנבנה
ידנית ב-Ads Manager (שהצליח) - עם שדות מורחבים יותר מ-debug_list_adsets.py (כולל
bid_strategy ברמת ה-Ad Set, וגם smart_promotion_type/buying_type/special_ad_categories
ברמת הקמפיין) - כדי לאתר איזה שדה נוסף שונה בין השניים וגורם לדחיית optimization_goal.

הרצה:
    python debug_compare_campaigns.py <our_campaign_id> <working_adset_id>

לדוגמה (עם ה-IDs מהשיחה):
    python debug_compare_campaigns.py 120250414422080697 120250416072230697
"""

import json
import sys

import requests

import config


CAMPAIGN_FIELDS = ("id,name,objective,status,smart_promotion_type,buying_type,"
                    "special_ad_categories,promoted_object,is_adset_budget_sharing_enabled")
ADSET_FIELDS = ("id,name,status,optimization_goal,destination_type,billing_event,"
                "bid_strategy,promoted_object,targeting,campaign{" + CAMPAIGN_FIELDS + "}")


def fetch(object_id: str) -> dict:
    url = f"{config.GRAPH_URL}/{object_id}"
    resp = requests.get(url, params={
        "fields": ADSET_FIELDS,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    return resp.json()


def fetch_campaign(campaign_id: str) -> dict:
    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": CAMPAIGN_FIELDS,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    return resp.json()


def main():
    if len(sys.argv) != 3:
        print("שימוש: python debug_compare_campaigns.py <our_campaign_id> <working_adset_id>")
        sys.exit(1)

    our_campaign_id, working_adset_id = sys.argv[1], sys.argv[2]

    print("=== הקמפיין שלנו (המשמש בcampaign_launch.py) ===")
    print(json.dumps(fetch_campaign(our_campaign_id), ensure_ascii=False, indent=2))

    print("\n=== ה-Ad Set שהצליח (נבנה ידנית ב-Ads Manager) + הקמפיין שלו ===")
    print(json.dumps(fetch(working_adset_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
