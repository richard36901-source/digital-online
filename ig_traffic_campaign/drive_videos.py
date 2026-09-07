# -*- coding: utf-8 -*-
"""
הורדת קובצי הווידאו מתיקיית Google Drive (config.DRIVE_FOLDER_ID) לתיקייה מקומית.

התיקייה בבעלות benk9922@gmail.com - כדי שזה יעבוד, המשתמש שמריץ את ההרשאה מול Google
(דרך check_google_drive_access.py / הרצה ראשונה של הסקריפט הזה) צריך גישת צפייה
לתיקייה הזו (שיתוף רגיל, לא בהכרח בעלות).

דורש הגדרה חד-פעמית - ראו README.md, סעיף "הגדרת גישה ל-Google Drive":
  1. פרויקט ב-Google Cloud Console + הפעלת Drive API
  2. יצירת OAuth Client ID (Desktop app) והורדת credentials.json לתיקייה הזו
  3. בהרצה הראשונה יפתח דפדפן לאישור ההתחברות - נוצר token.json ונשמר לפעמים הבאות
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import config


def _get_drive_service():
    creds = None
    token_path = Path(config.GOOGLE_OAUTH_TOKEN_CACHE)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), config.GOOGLE_DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_path = Path(config.GOOGLE_OAUTH_CREDENTIALS_FILE)
            if not creds_path.exists():
                raise RuntimeError(
                    f"חסר קובץ {creds_path} - ראו README.md, סעיף הגדרת גישה ל-Google Drive."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), config.GOOGLE_DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


SHORTCUT_MIME_TYPE = "application/vnd.google-apps.shortcut"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def list_folder_files(folder_id: str = None) -> list:
    """מחזיר [{'id', 'name', 'mimeType', 'shortcutDetails'?}] לכל הקבצים בתיקייה (לא בתתי-תיקיות)."""
    folder_id = folder_id or config.DRIVE_FOLDER_ID
    service = _get_drive_service()

    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, shortcutDetails)",
            pageSize=200,
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def resolve_downloadable_file(drive_file: dict) -> dict:
    """
    מחזיר את קובץ הווידאו האמיתי שאפשר להוריד, מטפל בשני מקרים לא-ישירים שהתגלו
    בפועל בתיקייה הזו:
      1. קיצור דרך (shortcut) - הקובץ האמיתי הוא shortcutDetails.targetId.
      2. תת-תיקייה (המקרה האמיתי כאן - כל "וידאו" הוא בפועל תיקייה, והקובץ עצמו
         נמצא בפנים) - יורדים רמה אחת ומאתרים את קובץ הווידאו שבתוכה.
    """
    if drive_file.get("mimeType") == SHORTCUT_MIME_TYPE:
        target_id = drive_file.get("shortcutDetails", {}).get("targetId")
        if not target_id:
            raise RuntimeError(f"'{drive_file['name']}' הוא קיצור דרך אבל אין לו targetId - "
                                f"בדוק אותו ידנית בדרייב.")
        service = _get_drive_service()
        return service.files().get(fileId=target_id, fields="id, name, mimeType").execute()

    if drive_file.get("mimeType") == FOLDER_MIME_TYPE:
        inner_files = list_folder_files(drive_file["id"])
        video_files = [f for f in inner_files if f.get("mimeType", "").startswith("video/")]
        candidates = video_files or inner_files  # fallback אם ל-Drive אין mimeType video/* מזוהה
        if len(candidates) == 0:
            raise RuntimeError(f"התיקייה '{drive_file['name']}' ריקה - אין בה קובץ להוריד.")
        if len(candidates) > 1:
            raise RuntimeError(f"נמצאו {len(candidates)} קבצים בתיקייה '{drive_file['name']}': "
                                f"{[f['name'] for f in candidates]} - לא ברור איזה להוריד.")
        return resolve_downloadable_file(candidates[0])  # רקורסיה - למקרה שגם הפנימי קיצור/תיקייה

    return drive_file


def find_file_by_hint(files: list, hint: str) -> dict:
    """מחפש קובץ יחיד שהשם שלו מכיל את hint (case-insensitive). זורק שגיאה אם 0 או 2+ תוצאות."""
    hint_lower = hint.lower()
    matches = [f for f in files if hint_lower in f["name"].lower()]
    if len(matches) == 0:
        raise RuntimeError(f"לא נמצא קובץ בתיקיית הדרייב שמכיל '{hint}'. קבצים זמינים: "
                            f"{[f['name'] for f in files]}")
    if len(matches) > 1:
        raise RuntimeError(f"נמצאו {len(matches)} קבצים שמתאימים ל-'{hint}': "
                            f"{[m['name'] for m in matches]} - חדד את ה-match ב-config.VIDEOS")
    return matches[0]


def download_file(file_id: str, dest_path: Path) -> Path:
    service = _get_drive_service()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  מוריד {dest_path.name}: {int(status.progress() * 100)}%")
    return dest_path


def ensure_videos_downloaded() -> dict:
    """
    עבור כל וידאו ב-config.VIDEOS, מוודא שהוא קיים מקומית (מוריד אם צריך).
    מחזיר dict: ad_set_name -> Path מקומי.
    """
    if config.DRY_RUN:
        return {v["ad_set_name"]: Path(config.LOCAL_VIDEO_DIR) / f"DRY_RUN_{v['match']}" for v in config.VIDEOS}

    files = list_folder_files()
    local_dir = Path(config.LOCAL_VIDEO_DIR)
    result = {}

    for video in config.VIDEOS:
        matched = find_file_by_hint(files, video["match"])
        real_file = resolve_downloadable_file(matched)  # פותר תיקיות/קיצורי דרך לקובץ האמיתי
        local_path = local_dir / real_file["name"]
        if not local_path.exists():
            print(f"מוריד '{real_file['name']}' מתוך '{matched['name']}' (drive id={real_file['id']})...")
            download_file(real_file["id"], local_path)
        else:
            print(f"'{local_path.name}' כבר קיים מקומית - מדלג על הורדה.")
        result[video["ad_set_name"]] = local_path

    return result
