# -*- coding: utf-8 -*-
"""
מחפש תחומי עניין (interests) אמיתיים ב-Meta לפי מילות מפתח, לכל קטגוריית תוכן
שהוגדרה ב-config.INTEREST_IDS_BY_CATEGORY. לא ניתן לנחש interest ID - הוא חייב
להתקבל מה-API עצמו (GET /search?type=adinterest), אחרת create_ad_set ידחה אותו.

הרצה:
    python debug_search_interests.py

הפלט: לכל קטגוריה, רשימת (id, name, audience_size) - תעתיקו את ה-id-ים הרלוונטיים
ביותר בחזרה ל-Claude, שיעדכן את config.INTEREST_IDS_BY_CATEGORY בפועל.
"""

import json

import requests

import config

# מילות מפתח לחיפוש לכל קטגוריה - קצת יותר מדי, כדי שיהיה ממה לבחור.
KEYWORDS_BY_CATEGORY = {
    "finance_crypto": ["Bitcoin", "Cryptocurrency", "Stock market", "Real estate investing", "Investment"],
    "sales_business": ["Sales", "Entrepreneurship", "Small business", "Marketing", "Negotiation"],
    "personal_dev_psych": ["Personal development", "Psychology", "Motivation", "Self-help", "Mindfulness"],
    "community": ["Community", "Social network", "Networking"],
    "health_nutrition": ["Nutrition", "Sugar", "Healthy diet"],
}


def search_interest(keyword: str) -> list:
    url = f"{config.GRAPH_URL}/search"
    resp = requests.get(url, params={
        "type": "adinterest",
        "q": keyword,
        "limit": 10,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        print(f"  שגיאה עבור '{keyword}': {data['error']}")
        return []
    return data.get("data", [])


def main():
    for category, keywords in KEYWORDS_BY_CATEGORY.items():
        print(f"\n{'=' * 60}\nקטגוריה: {category}\n{'=' * 60}")
        for kw in keywords:
            results = search_interest(kw)
            print(f"\n--- חיפוש: '{kw}' ---")
            if not results:
                print("  (אין תוצאות)")
            for r in results:
                print(f"  id={r.get('id'):<15} name={r.get('name'):<40} "
                      f"audience_size={r.get('audience_size_lower_bound', '?')}-{r.get('audience_size_upper_bound', '?')}")


if __name__ == "__main__":
    main()
