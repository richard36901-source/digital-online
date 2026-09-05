"""
נקודת הכניסה ל-CLI של אוטומציית הפרסום ל-TikTok.

שימוש:
  python main.py authorize          - שלב חד-פעמי: מדפיס קישור הרשאה, מבקש להדביק את ה-code שחוזר
  python main.py post               - מפרסם את הסרטון הבא בתור מתוך content_bank/
  python main.py post <video.mp4> "כיתוב"   - מפרסם קובץ ספציפי עם כיתוב מפורש

מומלץ להריץ קודם עם config.DRY_RUN = True כדי לוודא שהכיתוב/הווידאו נכונים,
ורק אז לעבור ל-DRY_RUN = False (ראו README.md).
"""

import sys

import actions
import auth
import config
import content_library
import logger


def cmd_authorize():
    if config.CLIENT_KEY in ("PASTE_YOUR_CLIENT_KEY_HERE", "", None):
        print("שגיאה: לא הוגדר TIKTOK_CLIENT_KEY. ערוך/י את config.py או הגדר משתני סביבה.")
        sys.exit(1)

    url = auth.build_authorize_url()
    print("פתח/י את הקישור הבא בדפדפן, אשר/י גישה, והדביק/י כאן את ה-code שחוזר ב-URL של ה-redirect:\n")
    print(url)
    code = input("\ncode: ").strip()
    tokens = auth.exchange_code_for_token(code)
    logger.print_and_log({"level": "info", "message": "הרשאת TikTok הושלמה בהצלחה", "scope": tokens.get("scope")})
    print(f"\nהצלחה! הטוקן נשמר ב-{config.TOKEN_FILE}. אפשר עכשיו: python main.py post")


def cmd_post(video_path: str = None, caption: str = None):
    if video_path is None:
        item = content_library.pick_next_video()
        if item is None:
            print(f"אין סרטונים בתיקייה {config.CONTENT_BANK_PATH}/videos - יש להוסיף קובצי mp4.")
            sys.exit(1)
        video_path = str(item["video_path"])
        caption = item["caption"]
    elif caption is None:
        caption = ""

    logger.print_and_log({
        "level": "info",
        "message": "מתחיל פרסום סרטון",
        "video_path": video_path,
        "caption": caption,
        "dry_run": config.DRY_RUN,
    })

    try:
        creator_info = actions.query_creator_info()
        result = actions.post_video(video_path, caption)
        logger.print_and_log({"level": "action", "action": "post_video", "result": result})

        if not config.DRY_RUN:
            status = actions.wait_for_publish(result["publish_id"])
            logger.print_and_log({"level": "info", "message": "סטטוס פרסום", "status": status})
            if status.get("status") == "FAILED":
                print(f"\nהפרסום נכשל: {status}")
                sys.exit(1)

        print(f"\nהושלם.{' (DRY RUN - לא בוצע פרסום אמיתי)' if config.DRY_RUN else ''}")
    except Exception as e:
        logger.print_and_log({"level": "error", "message": f"נכשל פרסום סרטון: {e}"})
        raise


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "authorize":
        cmd_authorize()
    elif command == "post":
        video_path = sys.argv[2] if len(sys.argv) > 2 else None
        caption = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_post(video_path, caption)
    else:
        print(f"פקודה לא מוכרת: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
