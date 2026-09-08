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
# אומת בפועל (7/9/2026): על אף שחשבון האינסטגרם ben_nahum_1 מוקצה ישירות ל-
# Business Portfolio בלי "דף פייסבוק מקושר" קלאסי, ה-promoted_object של ה-Ad Set
# (ברמת ה-optimization_goal=PROFILE_AND_PAGE_ENGAGEMENT) עדיין דורש page_id תקין -
# נמצא ע"י בניית טיוטת קמפיין ידנית ב-Ads Manager עם אותה מטרה/יעד ובדיקת השדות
# האמיתיים שהיא יצרה (ראו debug_list_adsets.py). זהו דף שכבר משמש קמפיינים אחרים
# באותו act_330184635273905 - כנראה "דף ברירת המחדל" של חשבון המודעות.
PAGE_ID = "1067237409815794"
# ה-ID שהופיע ב-URL של Business Settings (selected_asset_id=105029402244816) התברר
# כלא-תקין ל-promoted_object[instagram_actor_id] (שגיאת API: "must be a valid
# instagram actor id"). ה-ID הנכון נמצא בתוך עמוד הפרטים של ben_nahum_1 עצמו
# (Business Settings -> Accounts -> Instagram accounts -> ben_nahum_1 -> מזהה),
# ומאושש גם כי הוא כבר בשימוש בפועל בקמפיין קיים אחר על אותו act_330184635273905.
IG_ACTOR_ID = "17841446812678634"
IG_USERNAME = "ben_nahum_1"  # לתיעוד/ולידציה בלבד - ה-API עובד לפי IG_ACTOR_ID

# ==== הקמפיין ====
CAMPAIGN_NAME = "תנועה לאינסטגרם - ben_nahum_1 - סדרת סרטונים"

# אומת בפועל (8/9/2026) אחרי ניפוי ארוך: OUTCOME_ENGAGEMENT + destination_type=
# INSTAGRAM_PROFILE + optimization_goal=PROFILE_AND_PAGE_ENGAGEMENT (ה"ביקור בפרופיל
# אינסטגרם" הילידי) נכשל עקבית ב-create_ad_set עם שגיאה שהאשימה optimization_goal -
# גם עם כל שדה תואם בדיוק לדוגמה שהצליחה ידנית ב-Ads Manager (page_id, smart_pse_enabled,
# individual_setting וכו'), גם עם קמפיין חדש לגמרי, גם עם טוקן משתמש אישי (לא System
# User), וגם עם גרסת API חדשה (v25.0). כל המשתנים נשללו - כנראה שה-optimization_goal
# הזה ניתן ליצירה רק דרך זרימת ה"guided creation" הפנימית של Ads Manager, לא דרך ה-API
# הציבורי בשלושת השלבים (campaign->adset->creative). הוחלט לעבור ל-OUTCOME_TRAFFIC
# עם LINK_CLICKS - בדיוק אותו conceptual pattern שכבר עובד בפועל על החשבון הזה (קמפיין
# "הזרמת תנועה לדיסקורד"), רק עם לינק לפרופיל האינסטגרם במקום ל-Discord.
CAMPAIGN_OBJECTIVE = "OUTCOME_TRAFFIC"

# ==== הגדרות ברמת ה-Ad Set (זהות לכל הסטים, אחד לכל סרטון) ====
# LINK_CLICKS הוא optimization_goal סטנדרטי ומאומת (זהה לקמפיין הדיסקורד הפעיל
# בחשבון הזה) - בלי destination_type/promoted_object מיוחדים, כי היעד הוא לינק חיצוני
# רגיל (כתובת הפרופיל), לא "יעד" native כמו INSTAGRAM_PROFILE.
OPTIMIZATION_GOAL = "LINK_CLICKS"
BILLING_EVENT = "IMPRESSIONS"

# תקציב יומי לכל Ad Set בנפרד (לא לקמפיין!), באגורות. 10 ש"ח = 1000 אגורות.
DAILY_BUDGET_AGOROT_PER_ADSET = 1000

# אומת בפועל (8/9/2026): החשבון הזה דורש bid_strategy מפורש בכל מקרה - השמטתו
# מחזירה "נדרש סכום הצעת מחיר לאסטרטגיית הצעת מחיר" (error_subcode 2490487), בלי קשר
# ל-optimization_goal. LOWEST_COST_WITH_BID_CAP עם bid_amount שווה לתקציב היומי המלא
# הוא בפועל שקול ל"בלי תקציב אמיתי" (קליק בודד לא יעלה קרוב לתקציב יומי שלם).
BID_STRATEGY = "LOWEST_COST_WITH_BID_CAP"
BID_AMOUNT_AGOROT = DAILY_BUDGET_AGOROT_PER_ADSET

# כפתור קריאה לפעולה על המודעה - מוביל ל-DESTINATION_URL (כתובת הפרופיל).
CTA_TYPE = "LEARN_MORE"

# טירגוט: ישראל, קהל רחב, בלי הגבלת גיל/מגדר (18-65 זה טווח ברירת המחדל הרחב ביותר ב-API).
# individual_setting נוסף כדי להתאים בדיוק למבנה שה-Ad Set המאומת ב-Ads Manager
# יצר בפועל (debug_compare_campaigns.py) - עוד הבדל מבני אפשרי מול הפעם שנכשלה.
TARGETING = {
    "geo_locations": {"countries": ["IL"]},
    "age_min": 18,
    "age_max": 65,
    "targeting_automation": {
        "advantage_audience": 1,
        "individual_setting": {"age": 1, "gender": 1},
    },
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

# ==== קטגוריות תוכן -> תחומי עניין לטירגוט ====
# לכל וידאו יש "category" (למטה) שממופה כאן לרשימת interest IDs אמיתיים של Meta.
# ה-IDs האלה *חייבים* להיות אמיתיים - אי אפשר לנחש אותם (Meta דוחה ID לא קיים) -
# ריקים בכוונה עד שירוצו debug_search_interests.py ויוחזרו IDs אמיתיים מה-API.
# עד אז campaign_launch.py ייפול חזרה לטירגוט הרחב (TARGETING למטה, בלי flexible_spec).
INTEREST_IDS_BY_CATEGORY = {
    "finance_crypto": [],       # ביטקוין, קריפטו, שוק ההון, נדל"ן, השקעות
    "sales_business": [],       # מכירות, יזמות, שיווק, עסק קטן
    "personal_dev_psych": [],   # פיתוח אישי, פסיכולוגיה, מוטיבציה, מיינדפולנס
    "community": [],            # קהילה, נטוורקינג, רשתות חברתיות
    "health_nutrition": [],     # תזונה, בריאות, סוכר
}

# ==== רשימת הסרטונים ====
# "match" = מחרוזת לזיהוי הקובץ בתיקיית הדרייב (חיפוש case-insensitive, substring).
# השמות המקוריים שניחשנו לא תאמו את הקבצים האמיתיים בתיקייה - התיקון הזה מבוסס על
# הרשימה האמיתית שה-API החזיר בהרצה הראשונה (ראו שיחה). "1.mov".."8.mov" גם הם לא
# היו קיימים בפועל בשם הזה - יש 8 סרטונים נוספים עם שמות תוכן אמיתיים, לא מספור.
# אם "match" לא ימצא קובץ יחיד וברור - הסקריפט יעצור בשגיאה במקום לנחש.
# "message" הוא רק ברירת מחדל/גיבוי: כל תת-תיקייה בדרייב מכילה גם קובץ טקסט
# (Google Doc או .txt) לצד הווידאו - אם כזה נמצא, drive_videos.py קורא אותו
# ומשתמש בו בפועל כטקסט הראשי של המודעה במקום השדה הזה (כולל נירמול מקפים
# ארוכים/מיוחדים כמו — או – למקף קצר רגיל -).
# "title"/"description" - כותרת ותיאור קצר לקריאטיב (headline/link_description) -
# מותאמים לתוכן הספציפי של כל סרטון, כדי לדבר ישירות לקהל שהכי ירצה ללחוץ.
# "category" - קובע איזה תחומי עניין (INTEREST_IDS_BY_CATEGORY) ישמשו לטירגוט.
VIDEOS = [
    {"match": "אנשים קונים מחקרים", "ad_set_name": "בסוף אנשים קונים מחקרים",
     "message": "בסוף אנשים קונים מחקרים, לא דעות. עוד תוכן כזה - עקבו באינסטגרם",
     "title": "אנשים קונים מחקרים, לא דעות",
     "description": "למה שכנוע אמיתי מתחיל בעובדות",
     "category": "sales_business"},
    {"match": "שוק ההוק או נלדן", "ad_set_name": "שוק ההון או נדל\"ן",
     "message": "שוק ההון או נדל\"ן - מה באמת משתלם? התשובה באינסטגרם שלנו",
     "title": "שוק ההון או נדל\"ן?",
     "description": "ההשקעה שבאמת משתלמת",
     "category": "finance_crypto"},
    {"match": "מה זה ביטקוין", "ad_set_name": "מה זה ביטקוין",
     "message": "מה זה בכלל ביטקוין? מסבירים פשוט - עקבו לעוד תוכן",
     "title": "מה זה בכלל ביטקוין?",
     "description": "ההסבר הכי פשוט שתשמעו",
     "category": "finance_crypto"},
    {"match": "למה קהילה זה דבר חשוב", "ad_set_name": "למה קהילה זה כזה חשוב",
     "message": "למה קהילה זה כזה חשוב להצלחה שלכם - הצטרפו אלינו",
     "title": "קהילה = הצלחה",
     "description": "למה בלי קהילה קשה להתקדם",
     "category": "community"},
    {"match": "אפקט הסוכר", "ad_set_name": "אפקט הסוכר",
     "message": "אפקט הסוכר - איך זה משפיע עליכם בלי שתשימו לב",
     "title": "אפקט הסוכר",
     "description": "מה שסוכר עושה לכם בלי שתרגישו",
     "category": "health_nutrition"},
    {"match": "גישת התלמיד", "ad_set_name": "גישת התלמיד",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "גישת התלמיד",
     "description": "המפתח ללמידה שמביאה תוצאות",
     "category": "personal_dev_psych"},
    {"match": "3 שאלות משמעות", "ad_set_name": "3 שאלות משמעות",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "3 שאלות שמשנות הכל",
     "description": "השאלות שכל אחד צריך לשאול את עצמו",
     "category": "personal_dev_psych"},
    {"match": "לבטל את ההתנגדות עוד לפני שהיא צפה", "ad_set_name": "לבטל את ההתנגדות עוד לפני שהיא צפה",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "לבטל התנגדות לפני שהיא קמה",
     "description": "הטכניקה שכל איש מכירות חייב להכיר",
     "category": "sales_business"},
    {"match": "שיחת מכירה זה לא חוקר ונחקר", "ad_set_name": "שיחת מכירה זה לא חוקר ונחקר",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "מכירה זה לא חקירה",
     "description": "איך לנהל שיחת מכירה נכונה",
     "category": "sales_business"},
    {"match": "יהיו רק 21 מיליון", "ad_set_name": "יהיו רק 21 מיליון",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "יהיו רק 21 מיליון - לנצח",
     "description": "העובדה שמשנה הכל על ביטקוין",
     "category": "finance_crypto"},
    {"match": "תודעה הישרדותית תודעת הפסיכולוג תודעת מאסטר", "ad_set_name": "תודעה הישרדותית תודעת הפסיכולוג תודעת מאסטר",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "3 סוגי תודעה - איזו יש לך?",
     "description": "הישרדותית, פסיכולוג או מאסטר",
     "category": "personal_dev_psych"},
    {"match": "החלטות ממקום רגשי - אישיות מקדמת", "ad_set_name": "החלטות ממקום רגשי - אישיות מקדמת",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "החלטות ממקום רגשי",
     "description": "איך רגש משפיע על כל החלטה שלכם",
     "category": "personal_dev_psych"},
    {"match": "פחד זה פיקציה", "ad_set_name": "פחד זה פיקציה",
     "message": "עוד תוכן שווה - עקבו אחרינו באינסטגרם",
     "title": "פחד זה פיקציה",
     "description": "איך להפסיק לתת לפחד לנהל אתכם",
     "category": "personal_dev_psych"},
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
# כתובת מלאה עם scheme - נדרש ל-call_to_action.value.link בקריאטיב (LINK_CLICKS
# דורש URL תקין ומוחלט, לא רק דומיין+נתיב).
DESTINATION_URL = f"https://www.instagram.com/{IG_USERNAME}/"

# ==== לוח בקרה אינטראקטיבי (webapp.py) ====
# מקביל בכוונה ל-tiktok_ads_automation/webapp.py - שרת מקומי (Flask) עם כפתורי
# הפעלה/השהיה ותקציב, לא רק דיווח קריאה-בלבד. חייב סיסמה כי הוא זמין גם ברשת ה-WiFi
# המקומית (לא רק על המחשב עצמו) כדי לאפשר גישה מהטלפון. שינוי סיסמת ברירת המחדל הוא
# חובה לפני הרצה - ראו בדיקת ה-startup ב-webapp.py.
#   set IG_PANEL_PASSWORD=משהו-סודי-שלכם     (או export ב-Mac/Linux)
PANEL_PASSWORD = os.environ.get("IG_PANEL_PASSWORD", "שנה_את_הסיסמה")
