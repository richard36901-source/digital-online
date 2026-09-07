# -*- coding: utf-8 -*-
"""
תצורת קמפיין הזרמת תנועה לפרופיל האינסטגרם ben_nahum_1.
ערוך את הקובץ הזה לפני ההרצה הראשונה - במיוחד את IG_ACTOR_ID ו-PAGE_ID (ראו check_permissions.py).
"""

import os

# ==== System User Access Token ====
# אותו טוקן כמו ב-meta_ads_automation (System User, ads_management + business_management).
# עדיף כמשתנה סביבה, לא בקוד.
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# גרסת ה-API
API_VERSION = "v21.0"
GRAPH_URL = f"https://graph.facebook.com/{API_VERSION}"

# ==== חשבון המודעות ====
# "יהב" - act_330184635273905. בכוונה לא נוסף ל-AD_ACCOUNTS של meta_ads_automation
# (שם זה קריאה-בלבד בכוונה) - זה מודול נפרד ועצמאי שכן מבצע פעולות כתיבה על החשבון הזה.
AD_ACCOUNT_ID = "330184635273905"

# ==== דף הפייסבוק + פרופיל האינסטגרם ====
# PAGE_ID: דף הפייסבוק המחובר לחשבון המודעות (נדרש לכל object_story_spec).
# IG_ACTOR_ID: המזהה המספרי (לא שם המשתמש!) של פרופיל האינסטגרם ben_nahum_1,
#              כפי שמחובר לדף הפייסבוק דרך Instagram Business/Creator Account.
# שניהם לא ידועים מראש - הרץ python check_permissions.py כדי לגלות אותם ולמלא כאן.
# PAGE_ID לא ידוע/לא נדרש - חשבון האינסטגרם מוקצה ישירות ל-Business Portfolio
# (naan1930store) בלי דף פייסבוק מקושר. campaign_launch.py כבר יודע להתמודד עם זה.
PAGE_ID = "PASTE_PAGE_ID_HERE"
# ה-ID שהופיע ב-URL של Business Settings (selected_asset_id=105029402244816) התברר
# כלא-תקין ל-promoted_object[instagram_actor_id] (שגיאת API: "must be a valid
# instagram actor id"). ה-ID הנכון נמצא בתוך עמוד הפרטים של ben_nahum_1 עצמו
# (Business Settings -> Accounts -> Instagram accounts -> ben_nahum_1 -> מזהה),
# ומאושש גם כי הוא כבר בשימוש בפועל בקמפיין קיים אחר על אותו act_330184635273905.
IG_ACTOR_ID = "17841446812678634"
IG_USERNAME = "ben_nahum_1"  # לתיעוד/ולידציה בלבד - ה-API עובד לפי IG_ACTOR_ID

# ==== הקמפיין ====
CAMPAIGN_NAME = "תנועה לאינסטגרם - ben_nahum_1 - סדרת סרטונים"

# Objective ברמת הקמפיין (ODAX). "ביקורים בפרופיל אינסטגרם" הוא conversion location
# תחת Engagement. אם ה-API ידחה את זה, השגיאה תפרט את כל ה-objectives התקינים הקיימים כרגע.
# *** לוודא לפני הרצה אמיתית (DRY_RUN=False) - ראו הערה ב-README ***
CAMPAIGN_OBJECTIVE = "OUTCOME_ENGAGEMENT"

# ==== הגדרות ברמת ה-Ad Set (זהות לכל הסטים, אחד לכל סרטון) ====
# ילד "ביקורים בפרופיל אינסטגרם": destination_type + optimization_goal הבאים הם
# ההשערה הכי טובה שלי נכון להיום (Ads Manager: "מיקום ההמרה" = "פרופיל אינסטגרם").
# *** אם optimization_goal שגוי, ה-API יחזיר שגיאה עם רשימת הערכים התקינים - עדכן כאן ***
# ניסיון ראשון "PROFILE_VISIT" נדחה בפועל ע"י ה-API (error_subcode 2490408,
# "יעד הביצועים לא זמין עם מטרת הקמפיין") בלי לפרט את הערכים התקינים בהודעה עצמה.
# בדקנו בפועל (debug_list_adsets.py) שאין בחשבון הזה שום קמפיין קיים שמכוון
# לביקורים בפרופיל אינסטגרם להעתיק ממנו - אין דוגמה אמיתית לאמת מולה.
# "VISIT_INSTAGRAM_PROFILE" הוא הניחוש הבא הכי סביר (תואם את דפוס השמות
# action+object של שאר הערכים כמו PAGE_LIKES/LANDING_PAGE_VIEWS).
# *** אם גם זה נדחה, ה-API אמור לפרט ערכים תקינים - עדכן כאן בהתאם ***
DESTINATION_TYPE = "INSTAGRAM_PROFILE"
OPTIMIZATION_GOAL = "VISIT_INSTAGRAM_PROFILE"
BILLING_EVENT = "IMPRESSIONS"
BID_STRATEGY = "LOWEST_COST_WITHOUT_CAP"

# תקציב יומי לכל Ad Set בנפרד (לא לקמפיין!), באגורות. 10 ש"ח = 1000 אגורות.
DAILY_BUDGET_AGOROT_PER_ADSET = 1000

# כפתור קריאה לפעולה על המודעה. לא בטוח שנדרש בכלל למודעות "ביקור בפרופיל" - לוודא
# בהרצה הראשונה; אם ה-API דוחה את זה, אפשר לנסות בלי call_to_action כלל.
CTA_TYPE = "LEARN_MORE"

# טירגוט: ישראל, קהל רחב, בלי הגבלת גיל/מגדר (18-65 זה טווח ברירת המחדל הרחב ביותר ב-API).
TARGETING = {
    "geo_locations": {"countries": ["IL"]},
    "age_min": 18,
    "age_max": 65,
    "targeting_automation": {"advantage_audience": 1},
}

# ==== סטטוס בעת יצירה ====
# הכל נוצר PAUSED בכוונה - גם ב-DRY_RUN=False - כדי שתעבור ידנית על כל סט/מודעה
# ב-Ads Manager ותפעיל ידנית, במקום שהקמפיין ירוץ מייד אוטומטית על כסף אמיתי.
CREATED_STATUS = "PAUSED"

# ==== מקור הסרטונים - Google Drive ====
DRIVE_FOLDER_ID = "1SWAcj6fAOcLn2y4NMI8O_HQWJFBozmMV"  # בבעלות benk9922@gmail.com
# תיקייה מקומית שאליה יורדו הסרטונים לפני העלאה ל-Meta
LOCAL_VIDEO_DIR = "./downloaded_videos"

# קובצי אישור OAuth ל-Drive API (ראו README - שלב "הגדרת גישה ל-Google Drive")
GOOGLE_OAUTH_CREDENTIALS_FILE = "./credentials.json"  # מ-Google Cloud Console
GOOGLE_OAUTH_TOKEN_CACHE = "./token.json"             # נוצר אוטומטית אחרי אישור ידני ראשון
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ==== רשימת הסרטונים ====
# "match" = מחרוזת לזיהוי הקובץ בתיקיית הדרייב (חיפוש case-insensitive, substring).
# השמות המקוריים שניחשנו לא תאמו את הקבצים האמיתיים בתיקייה - התיקון הזה מבוסס על
# הרשימה האמיתית שה-API החזיר בהרצה הראשונה (ראו שיחה). "1.mov".."8.mov" גם הם לא
# היו קיימים בפועל בשם הזה - יש 8 סרטונים נוספים עם שמות תוכן אמיתיים, לא מספור.
# אם "match" לא ימצא קובץ יחיד וברור - הסקריפט יעצור בשגיאה במקום לנחש.
VIDEOS = [
    {"match": "אנשים קונים מחקרים", "ad_set_name": "בסוף אנשים קונים מחקרים",
     "message": "בסוף אנשים קונים מחקרים, לא דעות. עוד תוכן כזה - עקבו באינסטגרם"},
    {"match": "שוק ההוק או נלדן", "ad_set_name": "שוק ההון או נדל\"ן",
     "message": "שוק ההון או נדל\"ן - מה באמת משתלם? התשובה באינסטגרם שלנו"},
    {"match": "מה זה ביטקוין", "ad_set_name": "מה זה ביטקוין",
     "message": "מה זה בכלל ביטקוין? מסבירים פשוט - עקבו לעוד תוכן"},
    {"match": "למה קהילה זה דבר חשוב", "ad_set_name": "למה קהילה זה כזה חשוב",
     "message": "למה קהילה זה כזה חשוב להצלחה שלכם - הצטרפו אלינו"},
    {"match": "אפקט הסוכר", "ad_set_name": "אפקט הסוכר",
     "message": "אפקט הסוכר - איך זה משפיע עליכם בלי שתשימו לב"},
] + [
    {"match": name, "ad_set_name": name.strip(),
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם"}
    for name in [
        "גישת התלמיד",
        "3 שאלות משמעות",
        "לבטל את ההתנגדות עוד לפני שהיא צפה",
        "שיחת מכירה זה לא חוקר ונחקר",
        "יהיו רק 21 מיליון",
        "תודעה הישרדותית תודעת הפסיכולוג תודעת מאסטר",
        "החלטות ממקום רגשי - אישיות מקדמת",
        "פחד זה פיקציה",
    ]
]

# ==== מצב בטיחות ====
# כשזה True, הסקריפט רק מדפיס/רושם מה הוא *היה* עושה - בלי הורדת קבצים אמיתית,
# בלי העלאה ל-Meta, בלי יצירת קמפיין/סטים/מודעות. יש להריץ במצב הזה קודם ולעבור על הפלט.
# נשלט ע"י משתנה סביבה DRY_RUN (כמו META_ACCESS_TOKEN) ולא בעריכה ידנית של הקובץ -
# כדי שלא תצטרך לערוך את config.py כל הרצה, מה שגרם בעבר להתנגשויות חוזרות ב-git pull.
# ברירת המחדל True (בטוח) - צריך DRY_RUN=false במפורש כדי לבצע פעולות אמיתיות.
DRY_RUN = os.environ.get("DRY_RUN", "true").strip().lower() != "false"

# ==== לוגים ====
LOG_FILE = "./logs/campaign_launch_log.jsonl"

# ==== דשבורד ביצועים (performance_dashboard.html) ====
# מקביל בכוונה ל-tiktok_ads_automation/dashboard.py - קריאה-בלבד, לא נוגע בשום מודעה.
# מציג רק מודעות מתוך הקמפיין הזה (CAMPAIGN_NAME) - לא כל מודעה אחרת בחשבון act_330184635273905.
# חלון הנתונים - חייב להיות אחד מהערכים שה-API של Meta תומך בהם (לא מספר ימים חופשי):
# today / yesterday / last_7d / last_14d / last_28d / last_30d / last_90d / this_month / last_month / this_quarter
DATE_PRESET = "last_7d"
PERFORMANCE_DASHBOARD_FILE = "./performance_dashboard.html"
DESTINATION_URL = f"instagram.com/{IG_USERNAME}"
