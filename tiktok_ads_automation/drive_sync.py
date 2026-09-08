# -*- coding: utf-8 -*-
"""
סנכרון אוטומטי של סרטוני קמפיין מ-Google Drive - מחליף הורדה ידנית בדפדפן.

שימוש:
  python drive_sync.py authorize   - שלב חד-פעמי: פותח דפדפן לאישור גישה לחשבון Google
  python drive_sync.py sync        - מוריד כל סרטון חדש מהתיקייה שעדיין לא קיים מקומית,
                                       ומעדכן את videos.json אוטומטית עבור סרטונים חדשים

לפני השימוש הראשון - ראו README.md להגדרת אפליקציית OAuth ב-Google Cloud Console
(חובה: הפעלת Google Drive API + יצירת OAuth Client ID מסוג "Desktop app" + הורדת
הקובץ כ-client_secret.json לתיקייה הזו).

הרצה חוזרת של sync בטוחה - מדלגת על קבצים שכבר קיימים מקומית, לא מורידה שוב.
"""

import json
import sys
from pathlib import Path

import config

VIDEOS_DIR = Path(config.CREATIVE_BANK_PATH) / "instagram_promo" / "videos"
MANIFEST_PATH = Path(config.CREATIVE_BANK_PATH) / "instagram_promo" / "videos.json"

# מיפוי קבוע של קבצים שכבר זוהו/נקראו ידנית - כדי לא "לגלות" אותם מחדש בכל סנכרון
# ולתת להם שם אחר בטעות. 8 מהם היו במקור ממוספרים (1.mov-8.mov) כי כשסונכרנו
# לראשונה לא היה שם תוכן ידוע ב-Drive - מאז אורגנו ב-Drive בתיקיות-בת עם שמות
# תוכן אמיתיים (ראו list_folder_files), ועודכנו כאן בהתאם (ראו גם
# campaign_launch.rename_numbered_videos - משנה גם את השם בפועל ב-TikTok).
KNOWN_FILE_MAP = {
    "1CAoFNxQ3zpEwHO64-DIee6hoeSecgzju": "אפקט הסוכר.mov",
    "1MZGCf4GZTzyW4K4YRV-6YYQzE-i939Xv": "מה זה ביטקוין.mov",
    "1oL498LSgCYNqWQW7vHyRMK3mzH7BOfSH": "בסוף אנשים קונים מחקרים.mov",
    "1Zi5CvI9CI_cPIl0AJHO8oLcX4inL1hh2": "שוק ההון או נדלן.mov",
    "1PzlFs9qaIbiqWF7-oug2di7R-3FuWEF9": "למה קהילה זה כזה חשוב.mov",
    "1vd22L5n1GQZ5In6Fet5DeH4aLzbQWd6F": "3 שאלות משמעות.mov",
    "1DFjPZhCE9SXwhx7A_mOnE7JCQ82EVQS_": "תודעה הישרדותית תודעת הפסיכולוג תודעת מאסטר.mov",
    "1psJ9zUgRXn83UmFUg_6wvVrjZVTlhyty": "לבטל את ההתנגדות עוד לפני שהיא צפה.mov",
    "1iYQ4ULMybBrQjMZ6XeLq5kj0Kxu0-PPT": "שיחת מכירה זה לא חוקר ונחקר.mov",
    "1cb92wcH47QziwuGefINqM261KwVgdSXJ": "יהיו רק 21 מיליון.mov",
    "1JvSaB7F61VHLlcsQcg0MFDs5hszdT2q9": "גישת התלמיד.mov",
    "17WriEG6jwBb5m1epDwbQLNFwsWHhXeRT": "החלטות ממקום רגשי - אישיות מקדמת.mov",
    "1dZ5j1KPywcQ9r_vE--wzsDOalQ_YiSmo": "פחד זה פיקציה.mov",
}

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DEFAULT_CAPTION = "עוד תוכן שווה - עקבו אחרינו באינסטגרם"


def get_drive_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    token_file = Path(config.DRIVE_TOKEN_FILE)
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_file = Path(config.DRIVE_CLIENT_SECRET_FILE)
            if not secret_file.exists():
                raise RuntimeError(
                    f"לא נמצא {secret_file} - הורידו קובץ OAuth Client ID מ-Google Cloud Console "
                    "לפי ההוראות ב-README.md, ואז הריצו: python drive_sync.py authorize"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def _list_children(service, folder_id: str, extra_query: str = "") -> list[dict]:
    files = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false" + extra_query
    while True:
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def list_folder_files(service, folder_id: str) -> list[dict]:
    """
    מחזיר את קובצי הווידאו בתיקייה - כולל תמיכה במבנה "תיקיית-משנה לכל סרטון",
    שהתגלה בפועל: המשתמש מארגן כל סרטון בתיקייה עם שם התוכן האמיתי (למשל
    "יהיו רק 21 מיליון"), כשקובץ הווידאו עצמו בפנים בשם גנרי חסר משמעות (כמו
    "copy_A78D3CA2....mov", ככה ש-Drive/האייפון שומר קבצים משותפים). במקרה כזה
    שם התיקייה הוא שם התצוגה של הסרטון, לא שם הקובץ הפנימי.
    """
    entries = []
    for item in _list_children(service, folder_id):
        if item["mimeType"] == FOLDER_MIME_TYPE:
            for video in _list_children(service, item["id"], " and mimeType contains 'video/'"):
                entries.append({"id": video["id"], "name": item["name"].strip(), "mimeType": video["mimeType"]})
        else:
            entries.append(item)
    return entries


def _unique_local_name(candidate: str) -> str:
    """אם השם כבר תפוס ע"י קובץ אחר (למשל שתי תיקיות-משנה עם אותו שם תוכן בטעות) -
    מוסיף מספר סידורי כדי למנוע התנגשות בין שני סרטונים שונים."""
    used_names = set(KNOWN_FILE_MAP.values())
    if candidate not in used_names:
        return candidate
    stem, ext = Path(candidate).stem, Path(candidate).suffix
    n = 2
    while f"{stem} ({n}){ext}" in used_names:
        n += 1
    return f"{stem} ({n}){ext}"


def _load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def _save_manifest(manifest: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def sync() -> None:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    service = get_drive_service()
    drive_files = list_folder_files(service, config.DRIVE_FOLDER_ID)

    manifest = _load_manifest()
    manifest_files = {item["file"] for item in manifest}

    downloaded, skipped, new_entries = 0, 0, 0

    for f in drive_files:
        if not f.get("mimeType", "").startswith("video/"):
            continue

        file_id = f["id"]
        drive_name = f["name"]

        if file_id in KNOWN_FILE_MAP:
            local_name = KNOWN_FILE_MAP[file_id]
        else:
            # שם התצוגה האמיתי (שם התיקייה, אם מדובר במבנה תיקיית-משנה-לכל-סרטון -
            # ראו list_folder_files) - לא ממספרים יותר קבצים לא-מוכרים באופן גנרי,
            # כדי לא לחזור על הבאג שהתגלה בפועל (8 סרטונים שקיבלו שמות "1.mov"-"8.mov"
            # בלי שום קשר לתוכן שלהם, כי בזמנו לא היה מבנה תיקיות עם שם משמעותי).
            ext = Path(drive_name).suffix or ".mov"
            base_name = drive_name if drive_name.lower().endswith(ext.lower()) else f"{drive_name}{ext.lower()}"
            local_name = _unique_local_name(base_name)
            KNOWN_FILE_MAP[file_id] = local_name  # כדי לא להתנגש עם עצמו בתוך אותה ריצה

        local_path = VIDEOS_DIR / local_name
        if local_path.exists():
            skipped += 1
        else:
            print(f"מוריד: {drive_name} -> {local_name}")
            request = service.files().get_media(fileId=file_id)
            local_path.write_bytes(request.execute())
            downloaded += 1

        if local_name not in manifest_files:
            manifest.append({"file": local_name, "ad_text": DEFAULT_CAPTION})
            manifest_files.add(local_name)
            new_entries += 1

    if new_entries:
        _save_manifest(manifest)

    print(f"\nסיום: {downloaded} סרטונים הורדו, {skipped} כבר היו קיימים, {new_entries} נוספו ל-videos.json.")
    if new_entries:
        print("לסרטונים החדשים ניתן כיתוב גנרי כברירת מחדל - ערכו אותו ב-videos.json כשתדעו על מה כל אחד.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("authorize", "sync"):
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "authorize":
        get_drive_service()
        print(f"הרשאה הושלמה בהצלחה - הטוקן נשמר ב-{config.DRIVE_TOKEN_FILE}")
    elif sys.argv[1] == "sync":
        sync()
