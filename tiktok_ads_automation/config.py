# -*- coding: utf-8 -*-
"""
תצורת אוטומציית ניהול הקמפיינים ב-TikTok Ads - ערוך את הקובץ הזה לפני ההרצה הראשונה.
"""

import json
import os
from pathlib import Path


def _load_saved_access_token() -> str | None:
    """קורא את הטוקן מתוך tiktok_ads_tokens.json (נשמר שם ע"י auth.py ב-authorize) -
    כדי שלא יהיה צורך להריץ 'set TIKTOK_ADS_ACCESS_TOKEN=...' בכל חלון טרמינל חדש."""
    token_file = Path(__file__).parent / "tiktok_ads_tokens.json"
    if not token_file.exists():
        return None
    try:
        return json.loads(token_file.read_text(encoding="utf-8")).get("access_token")
    except (json.JSONDecodeError, OSError):
        return None


# ==== גישה ל-TikTok Marketing API ====
# הטוקן מתקבל דרך אישור OAuth חד-פעמי (ראו auth.py / README.md), לא סטטי כמו מפתח API.
# סדר עדיפות: משתנה סביבה TIKTOK_ADS_ACCESS_TOKEN (אם הוגדר) -> tiktok_ads_tokens.json
# שנשמר אוטומטית ע"י authorize -> placeholder.
ACCESS_TOKEN = os.environ.get("TIKTOK_ADS_ACCESS_TOKEN") or _load_saved_access_token() or "PASTE_YOUR_TOKEN_HERE"

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

# ==== קמפיין השקה - קידום אינסטגרם (campaign_launch.py) ====
# יוצר קמפיין חדש מאפס: קבוצת מודעות (ad group) נפרדת לכל סרטון, כל אחת בתקציב יומי
# עצמאי, כדי שהשהיה/רוטציה של main.py יעבדו על כל סרטון בנפרד.

# יעד הקליקים - לאן המודעות מפנות.
DESTINATION_URL = "https://www.instagram.com/ben_nahum_1/"

# תקציב יומי לכל קבוצת מודעות (סרטון) בש"ח.
# אזהרה: TikTok אוכפת תקציב יומי מינימלי לכל ad group (בד"כ סביב $20/יום, ~74 ש"ח).
# תקציב של 10 ש"ח נמוך מהמינימום הזה וסביר שה-API יחזיר שגיאת ולידציה בעת יצירת קבוצת
# המודעות - הריצו קודם ב-DRY_RUN (שם רק נרשם מה היה קורה, בלי לבדוק מול TikTok בפועל),
# ואם תקבלו שגיאת "budget too low" בהרצה האמיתית, יש להעלות את הערך כאן.
DAILY_BUDGET_PER_VIDEO_ILS = 10

# שם הקמפיין המשותף לכל קבוצות המודעות שנוצרות דרך campaign_launch.py.
CAMPAIGN_NAME = "קידום אינסטגרם - ben_nahum_1"

# מיקומי טירגוט (location_id של TikTok, לא קוד מדינה רגיל). "294640" = ישראל ברמת מדינה
# (אומת מול python main.py lookup-locations "Israel" - level=COUNTRY, region_code=IL).
TARGETING_LOCATION_IDS: list[str] = ["294640"]

# זהות המפרסם (Identity) שהמודעה מוצגת תחתיה - חובה ע"פ TikTok. מוצאים ב-Ads Manager
# תחת Assets > Identities, או יוצרים "Custom identity" חדשה שם. יש למלא לפני הרצה אמיתית.
IDENTITY_ID = os.environ.get("TIKTOK_ADS_IDENTITY_ID", "PASTE_IDENTITY_ID_HERE")
IDENTITY_TYPE = "CUSTOMIZED_USER"  # לפי תיעוד TikTok - ערך אחר אפשרי אם ה-API מחזיר שגיאה

# ==== מצב בטיחות ====
# כשזה True, הסקריפט רק מדפיס/רושם מה הוא *היה* עושה, בלי לבצע שינויים אמיתיים.
# יש להריץ כמה ימים במצב הזה ולוודא שההחלטות הגיוניות, ואז לשנות ל-False.
DRY_RUN = True

# ==== לוגים ====
LOG_FILE = "./logs/automation_log.jsonl"

# ==== דשבורד ביצועים (dashboard.py) ====
# קובץ HTML קריאה-בלבד שנוצר מחדש בכל הרצת "python main.py dashboard" - משווה בין
# הסרטונים (חשיפות/קליקים/CTR) כדי לזהות אילו מודעות "מתבלטות" ואילו כדאי לזנוח.
PERFORMANCE_DASHBOARD_FILE = "./performance_dashboard.html"

# ==== לוח בקרה (webapp.py) - סיסמת כניסה ====
# חובה לשנות לפני שמריצים ברשת הביתית (0.0.0.0) - אחרת כל מכשיר ברשת (גם אורחים/
# מכשירי IoT) יוכל להיכנס וללחוץ על כפתורי כיבוי/הדלקה/תקציב. הריצו:
#   set TIKTOK_PANEL_PASSWORD=משהו-שרק-אני-יודע     (או export ב-Mac/Linux)
# או פשוט ערכו את השורה הבאה ישירות (הקובץ הזה לא ב-git עם הטוקן שלכם, אבל בכל
# זאת עדיף משתנה סביבה אם אפשר).
PANEL_PASSWORD = os.environ.get("TIKTOK_PANEL_PASSWORD", "שנה_את_הסיסמה")
