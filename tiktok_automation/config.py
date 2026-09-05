# -*- coding: utf-8 -*-
"""
תצורת אוטומציית הפרסום ל-TikTok - ערוך את הקובץ הזה (או הגדר משתני סביבה) לפני ההרצה הראשונה.
"""

import os

# ==== פרטי האפליקציה (מתוך TikTok for Developers) ====
# נוצרים כשנרשמים כמפתח בכתובת https://developers.tiktok.com/ ומוסיפים את המוצר
# "Content Posting API" לאפליקציה. עדיף להגדיר כמשתני סביבה ולא לשים כאן בטקסט גלוי.
CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "PASTE_YOUR_CLIENT_KEY_HERE")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "PASTE_YOUR_CLIENT_SECRET_HERE")

# ה-Redirect URI חייב להיות זהה בדיוק לזה שהוגדר בהגדרות האפליקציה ב-TikTok for Developers.
REDIRECT_URI = os.environ.get("TIKTOK_REDIRECT_URI", "http://localhost:8787/callback")

# הרשאות (scopes) נדרשות: user.info.basic - זיהוי בסיסי, video.publish - פרסום סרטונים.
SCOPES = "user.info.basic,video.publish"

# ==== כתובות ה-API ====
AUTH_BASE_URL = "https://www.tiktok.com/v2/auth/authorize/"
API_BASE_URL = "https://open.tiktokapis.com/v2"

# ==== קובץ טוקנים ====
# נשמר מקומית אחרי הרשאה ראשונית (authorize) - לא להעלות ל-git (ראה .gitignore).
TOKEN_FILE = "./tiktok_tokens.json"

# ==== קידום קהילת הדיסקורד ====
# TikTok לא מאפשר קישורים לחיצים בכיתוב הרגיל של סרטון (אלא רק לחשבונות עסקיים
# מאומתים עם תכונת "add link"), ולכן הכיתוב מפנה למשתמשים ל-Discord/לינק בביו
# במקום קישור ישיר. עדכן/י את הכיתוב בפועל לפי הצורך.
DISCORD_INVITE_URL = "https://discord.com/invite/45NUjhvBA"
DEFAULT_CAPTION_SUFFIX = "\n\nמצטרפים לקהילה שלנו בדיסקורד - קישור בביו 🔗"

# רמת פרטיות ברירת מחדל לפרסום. חשוב: כל עוד האפליקציה לא עברה audit ב-TikTok,
# TikTok כופה SELF_ONLY (פרטי) בפועל בלי קשר למה שמוגדר כאן - ראו README.md.
DEFAULT_PRIVACY_LEVEL = "PUBLIC_TO_EVERYONE"

# ==== ספריית תוכן ====
# תיקייה מקומית עם קובצי וידאו + captions.json לטקסטים (מבנה מקביל ל-creative_bank
# באוטומציית Meta Ads).
CONTENT_BANK_PATH = "./content_bank"

# ==== מצב בטיחות ====
# כשזה True, הסקריפט רק מדפיס/רושם מה הוא *היה* מפרסם, בלי לבצע קריאת API אמיתית.
# מומלץ להריץ כך פעם אחת ולוודא שהכיתוב/הווידאו נכונים, ואז לשנות ל-False.
DRY_RUN = True

# ==== לוגים ====
LOG_FILE = "./logs/automation_log.jsonl"
