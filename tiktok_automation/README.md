# אוטומציית פרסום ל-TikTok - קידום קהילת הדיסקורד

סקריפט Python שמפרסם סרטונים לחשבון ה-TikTok שלכם דרך ה-API הרשמי והחינמי של
TikTok (Content Posting API), כדי לקדם את קהילת ה-Discord (`landing-pages/landing_discord.html`,
קישור הצטרפות: `https://discord.com/invite/45NUjhvBA`).

## למה זה בחינם, ולמה זה לא Composio/Higgsfield

בדקנו קודם חיבור דרך Composio - זה עבר דרך שירות חיצוני בשם **Higgsfield**, ששם עלות
לחיבור/פרסום. ה-API הרשמי של TikTok (Content Posting API) **חינמי לגמרי** - אין מנוי
ואין תשלום לפי קריאה. **אבל** יש תנאי חשוב:

> **כל עוד אפליקציית ה-TikTok Developer שלכם לא עברה audit (בדיקה) של TikTok, כל סרטון
> שמתפרסם דרך ה-API יוצא אוטומטית בפרטיות SELF_ONLY (פרטי - רק אתם רואים אותו)**, בלי
> קשר למה שמוגדר בקוד. כדי שסרטונים יתפרסמו בפועל לציבור (ויקדמו את הדיסקורד), צריך
> לשלוח את האפליקציה ל-audit של TikTok (חינמי, אבל לוקח זמן - ראו "הגשה ל-audit" למטה).

## למה זה רץ אצלכם ולא אצל Claude?

הסביבה שבה Claude מריץ קוד חסומה מגישה ל-`open.tiktokapis.com` ול-`developers.tiktok.com`
(בדיוק כמו ש-`meta_ads_automation` חסום מגישה ל-`graph.facebook.com`). הסקריפט צריך
לרוץ על מחשב/שרת עם גישה רגילה לאינטרנט - המחשב שלכם, VPS, או שירות כמו PythonAnywhere.

## הגדרה (חובה לפני הרצה ראשונה)

### 1. רישום אפליקציית TikTok Developer (חד-פעמי, חינמי)

1. היכנסו ל-https://developers.tiktok.com/ והתחברו עם חשבון ה-TikTok שלכם.
2. צרו אפליקציה חדשה (App).
3. הוסיפו לאפליקציה את המוצר **Content Posting API**.
4. ב-Redirect URI הגדירו כתובת שאתם שולטים בה, למשל `http://localhost:8787/callback`
   (אותה כתובת חייבת להיות זהה גם ב-`config.py`).
5. העתיקו את ה-`Client Key` וה-`Client Secret` שנוצרו.

### 2. משתני סביבה

מומלץ להגדיר כמשתני סביבה ולא לשים ב-`config.py` בטקסט גלוי:

```bash
export TIKTOK_CLIENT_KEY="הקוד שלכם"
export TIKTOK_CLIENT_SECRET="הסוד שלכם"
export TIKTOK_REDIRECT_URI="http://localhost:8787/callback"   # אם שיניתם מברירת המחדל
```

### 3. התקנה

```bash
cd tiktok_automation
python3 -m venv venv
source venv/bin/activate   # ב-Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. ספריית תוכן

```
content_bank/
  videos/          # קבצי mp4 קצרים (עד 64MB)
  captions.json     # [{"caption": "..."}, ...]
```

הסקריפט עובר על הסרטונים/הכיתובים בתור (round-robin) - כל הרצת `post` בלי פרמטרים
מפרסמת את הבא בתור.

## הרשאה חד-פעמית (authorize)

```bash
python main.py authorize
```

יודפס קישור - פתחו אותו בדפדפן, אשרו גישה לחשבון ה-TikTok שלכם, ותועברו ל-Redirect URI
שהגדרתם עם `?code=...` בכתובת. הדביקו את הקוד הזה בטרמינל. הטוקן (וטוקן הרענון) יישמרו
ב-`tiktok_tokens.json` - **אל תעלו את הקובץ הזה ל-git** (כבר ב-`.gitignore`).

## הרצה ראשונה - חובה במצב DRY RUN

ב-`config.py`, `DRY_RUN = True` הוא ברירת המחדל. במצב הזה הסקריפט **לא מבצע שום קריאת
API אמיתית** - הוא רק מדפיס ורושם ללוג מה הוא *היה* מפרסם.

```bash
python main.py post
```

עברו על הפלט/הלוג (`logs/automation_log.jsonl`) ווודאו שהסרטון והכיתוב נכונים.

**רק אחרי שבדקתם ואתם בטוחים** - שנו ב-`config.py`:
```python
DRY_RUN = False
```

## הגשה ל-audit (כדי שהסרטונים יהיו ציבוריים)

עד שהאפליקציה עוברת audit, כל סרטון יוצא פרטי (SELF_ONLY) - שימושי לבדיקה, לא לקידום
בפועל. בממשק https://developers.tiktok.com/ תחת האפליקציה שלכם, יש אפשרות "Submit for
review/audit" - ממלאים טופס קצר על אופן השימוש (כאן: פרסום אוטומטי של תוכן שיווקי
שהכנתם מראש כדי לקדם קהילה). זה חינמי, אבל לוקח זמן (בדרך כלל ימים עד שבועות).

## פרסום ידני של סרטון ספציפי

```bash
python main.py post path/to/video.mp4 "כיתוב מותאם אישית"
```

## הרצה אוטומטית (cron)

בלינוקס/מק:
```bash
crontab -e
```
```
0 10 * * * cd /path/to/tiktok_automation && /path/to/venv/bin/python main.py post >> logs/cron.log 2>&1
```

## מבנה הקבצים

- `config.py` - כל ההגדרות (client key/secret, כתובת הדיסקורד, ספים)
- `auth.py` - זרימת OAuth (הרשאה חד-פעמית + רענון טוקן אוטומטי)
- `actions.py` - הפעולות בפועל מול ה-API (init, העלאת בייטים, בדיקת סטטוס)
- `content_library.py` - בחירת הסרטון/כיתוב הבא בתור מ-`content_bank/`
- `logger.py` - רישום ללוג
- `main.py` - CLI: `authorize` / `post`
- `tiktok_tokens.json` - נוצר אוטומטית אחרי `authorize` (לא ב-git)
- `content_rotation_state.json` - נוצר אוטומטית, זוכר איזה סרטון פורסם אחרון (לא ב-git)

## אזהרות חשובות

- **אין אישור בזמן אמת** - ברגע ש-`DRY_RUN=False`, הסקריפט מפרסם סרטונים לחשבון TikTok
  האמיתי שלכם באופן עצמאי לגמרי. בדקו היטב לפני שמכבים DRY_RUN.
- **TikTok לא תומך בקישורים לחיצים בכיתוב** (אלא רק לחשבונות עסקיים מאומתים) - הכיתוב
  מפנה לקהילת הדיסקורד דרך "קישור בביו". ודאו שקישור ה-Discord מעודכן בביו של חשבון
  ה-TikTok עצמו.
- **הטוקן פג תוקף** - `access_token` תקף לזמן קצר, ו-`refresh_token` לתקופה ארוכה יותר.
  `auth.get_valid_access_token()` מרענן אוטומטית - אבל אם `refresh_token` עצמו פג (לרוב
  אחרי כמה חודשים של אי-שימוש), יהיה צורך להריץ שוב `python main.py authorize`.
- **מגבלת קצב** - עד 6 בקשות בדקה לכל access token (מגבלת TikTok).
