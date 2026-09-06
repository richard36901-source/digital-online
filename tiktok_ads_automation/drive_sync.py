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

# מיפוי קבוע של קבצים שכבר זוהו/נקראו ידנית (5 סרטונים עם שם תוכן + 8 ממוספרים) -
# כדי לא "לגלות" אותם מחדש בכל סנכרון ולתת להם שם אחר בטעות.
KNOWN_FILE_MAP = {
    "1CAoFNxQ3zpEwHO64-DIee6hoeSecgzju": "אפקט הסוכר.mov",
    "1MZGCf4GZTzyW4K4YRV-6YYQzE-i939Xv": "מה זה ביטקוין.mov",
    "1oL498LSgCYNqWQW7vHyRMK3mzH7BOfSH": "בסוף אנשים קונים מחקרים.mov",
    "1Zi5CvI9CI_cPIl0AJHO8oLcX4inL1hh2": "שוק ההון או נדלן.mov",
    "1PzlFs9qaIbiqWF7-oug2di7R-3FuWEF9": "למה קהילה זה כזה חשוב.mov",
    "1vd22L5n1GQZ5In6Fet5DeH4aLzbQWd6F": "1.mov",
    "1DFjPZhCE9SXwhx7A_mOnE7JCQ82EVQS_": "2.mov",
    "1psJ9zUgRXn83UmFUg_6wvVrjZVTlhyty": "3.mov",
    "1iYQ4ULMybBrQjMZ6XeLq5kj0Kxu0-PPT": "4.mov",
    "1cb92wcH47QziwuGefINqM261KwVgdSXJ": "5.mov",
    "1JvSaB7F61VHLlcsQcg0MFDs5hszdT2q9": "6.mov",
    "17WriEG6jwBb5m1epDwbQLNFwsWHhXeRT": "7.mov",
    "1dZ5j1KPywcQ9r_vE--wzsDOalQ_YiSmo": "8.mov",
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


def list_folder_files(service, folder_id: str) -> list[dict]:
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def _next_available_number() -> int:
    existing = [int(p.stem) for p in VIDEOS_DIR.glob("*") if p.stem.isdigit()]
    return max(existing, default=0) + 1


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
            ext = Path(drive_name).suffix or ".mov"
            local_name = f"{_next_available_number()}{ext.lower()}"
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
