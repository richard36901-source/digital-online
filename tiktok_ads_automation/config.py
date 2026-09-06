# -*- coding: utf-8 -*-
"""
תצורת אוטומציית ניהול הקמפיינים ב-TikTok Ads - ערוך את הקובץ הזה לפני ההרצה הראשונה.
"""

import os

# ==== גישה ל-TikTok Marketing API ====
# הטוקן מתקבל דרך אישור OAuth חד-פעמי (ראו auth.py / README.md), לא סטטי כמו מפתח API.
# עדיף להגדיר כמשתנה סביבה ולא לשים כאן בטקסט גלוי.
ACCESS_TOKEN = os.environ.get("TIKTOK_ADS_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# פרטי אפליקציית ה-Marketing API (מ-https://business-api.tiktok.com/portal - נפרד
# מ-developers.tiktok.com ששימש את tiktok_automation לפרסום אורגני).
APP_ID = os.environ.get("TIKTOK_ADS_APP_ID", "PASTE_YOUR_APP_ID_HERE")
APP_SECRET = os.environ.get("TIKTOK_ADS_APP_SECRET", "PASTE_YOUR_APP_SECRET_HERE")
REDIRECT_URI = os.environ.get("TIKTOK_ADS_REDIRECT_URI", "http://localhost:8788/callback")

# גרסת ה-API
API_VERSION = "v1.3"
API_BASE_URL = f"https://business-api.tiktok.com/open_api/{API_VERSION}"

# ==== חשבונות המפרסם (Advertiser ID) ====
# מפתח = שם ידידותי לזיהוי בלוגים, ערך = ה-advertiser_id (aadvid בכתובת ה-Ads Manager).
# מולא אוטומטית מתוך הקישור ששיתפת מ-ads.tiktok.com/i18n/manage/campaign - שני/י שם
# ידידותי משלך אם יש כמה חשבונות.
ADVERTISER_ACCOUNTS = {
    "עיקרי": "7662260864170328082",
}

# ==== כללי האוטומציה ====
# סף רווחיות - מתחת לזה, המודעה מסומנת כלא רווחית ומושהית.
# שם המדד המדויק (complete_payment_roas) תלוי באירוע ההמרה שהוגדר בפיקסל/אירועי האפליקציה
# בחשבון שלכם - בדקו מול /report/integrated/get/ שהמדד הזה אכן מוחזר לפני שמכבים DRY_RUN.
ROAS_METRIC_NAME = "complete_payment_roas"
ROAS_THRESHOLD = 1.5

# כמה ימים מודעה צריכה לרוץ לפני שהיא מועמדת לרוטציית קריאטיב
CREATIVE_ROTATION_DAYS = 3

# חלון הנתונים לבדיקת ביצועים (כמות ימים אחורה מהיום)
REPORT_LOOKBACK_DAYS = 7

# ==== ספריית קריאטיבים ====
# תיקייה מקומית עם וידאו/תמונות + copy.json לטקסטים - מבנה מקביל ל-meta_ads_automation.
CREATIVE_BANK_PATH = "./creative_bank"

# ==== מצב בטיחות ====
# כשזה True, הסקריפט רק מדפיס/רושם מה הוא *היה* עושה, בלי לבצע שינויים אמיתיים.
# יש להריץ כמה ימים במצב הזה ולוודא שההחלטות הגיוניות, ואז לשנות ל-False.
DRY_RUN = True

# ==== לוגים ====
LOG_FILE = "./logs/automation_log.jsonl"
