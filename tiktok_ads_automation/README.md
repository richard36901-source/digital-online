# אוטומציית ניהול קמפיינים - TikTok Ads

סקריפט Python שרץ פעם ביום, בודק את חשבון/י המפרסם שלכם ב-TikTok Ads, ומבצע אוטומטית:
- השהיית מודעות עם ROAS מתחת לסף (או הוצאה בלי המרות כשאין נתוני ROAS)
- רוטציית וידאו + קופי למודעות שרצות כמה ימים
- רישום כל החלטה ופעולה ללוג (`logs/automation_log.jsonl`)

**הכל רץ אוטומטית ללא אישור בזמן אמת** - זו הסיבה שקריטי להריץ קודם במצב `DRY_RUN` (ראו למטה).

מבנה הקוד מקביל בכוונה ל-`meta_ads_automation/` הקיים בריפו, כדי שיהיה קל לתחזק את שניהם
באותה שיטה.

## חשוב: זה נפרד לגמרי מ-tiktok_automation

יש בריפו הזה גם `tiktok_automation/` - זה מפרסם **תוכן אורגני** (סרטונים חינמיים) דרך
TikTok Content Posting API כדי לקדם את קהילת הדיסקורד. המודול הזה (`tiktok_ads_automation`)
מנהל **קמפיינים ממומנים בפועל** (כסף אמיתי) דרך TikTok **Marketing API**, ומשתמש
באפליקציית מפתחים נפרדת לגמרי (מ-business-api.tiktok.com/portal, לא developers.tiktok.com).

## למה זה רץ אצלכם ולא אצל Claude?

הסביבה שבה Claude מריץ קוד חסומה מגישה ל-`business-api.tiktok.com` (בדיוק כמו ש-
`meta_ads_automation` חסום מגישה ל-`graph.facebook.com`). הסקריפט צריך לרוץ על מחשב/שרת
עם גישה רגילה לאינטרנט - המחשב שלכם, VPS, או שירות כמו PythonAnywhere.

## הגדרה (חובה לפני הרצה ראשונה)

### 1. רישום אפליקציית TikTok Marketing API (חד-פעמי, חינמי)

1. היכנסו ל-https://business-api.tiktok.com/portal עם חשבון ה-TikTok Business שלכם
   (אותו חשבון שכבר מפרסם - `aadvid=7662260864170328082` שכבר מולא ב-`config.py`
   תחת "עיקרי").
2. צרו אפליקציית Marketing API חדשה, והוסיפו לה את ה-scopes הנדרשים (לפחות: קריאת
   דוחות, ניהול קמפיינים/מודעות, העלאת קבצי מדיה).
3. ב-Redirect URI הגדירו כתובת שאתם שולטים בה, למשל `http://localhost:8788/callback`
   (אותה כתובת חייבת להיות זהה גם ב-`config.py`).
4. העתיקו את ה-`App ID` וה-`Secret`.

### 2. משתני סביבה

```bash
export TIKTOK_ADS_APP_ID="הקוד שלכם"
export TIKTOK_ADS_APP_SECRET="הסוד שלכם"
export TIKTOK_ADS_REDIRECT_URI="http://localhost:8788/callback"   # אם שיניתם מברירת המחדל
```

### 3. התקנה

```bash
cd tiktok_ads_automation
python3 -m venv venv
source venv/bin/activate   # ב-Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. הרשאה חד-פעמית (authorize)

```bash
python main.py authorize
```

יודפס קישור - פתחו אותו בדפדפן, אשרו גישה לחשבון המפרסם שלכם (בחרו את חשבון
`7662260864170328082`), ותועברו ל-Redirect URI שהגדרתם עם `?auth_code=...` בכתובת.
הדביקו את הקוד בטרמינל. הטוקן יישמר ב-`tiktok_ads_tokens.json` (לא ב-git) - העתיקו
אותו למשתנה הסביבה:

```bash
export TIKTOK_ADS_ACCESS_TOKEN="הטוקן שהתקבל"
```

בשונה מ-Content Posting API, הטוקן הזה ארוך-טווח ולא פג באופן שוטף - הוא נשאר תקף
עד שמבטלים אותו ידנית ב-Business Center.

### 5. ודאו את שם מדד ה-ROAS

`config.ROAS_METRIC_NAME` מוגדר כברירת מחדל ל-`complete_payment_roas`. זה תלוי באירוע
ההמרה שמוגדר בפיקסל/אירועי האפליקציה שלכם. הריצו פעם אחת עם `DRY_RUN=True` ובדקו
בלוג שהשדה `roas` אכן מקבל ערכים הגיוניים (לא כולם 0) - אם לא, בדקו מול תיעוד
`/report/integrated/get/` איזה מדד רלוונטי לחשבון שלכם ועדכנו את השם ב-`config.py`.

### 6. ספריית קריאטיבים

```
creative_bank/
  _common/
    videos/        # קבצי mp4
    copy.json       # [{"ad_text": "..."}, ...]
```

אפשר גם ליצור תת-תיקייה ייעודית per לקוח (בשם התואם למפתח ב-`ADVERTISER_ACCOUNTS`),
בדיוק כמו ב-`meta_ads_automation`.

## הרצה ראשונה - חובה במצב DRY RUN

ב-`config.py`, `DRY_RUN = True` הוא ברירת המחדל. במצב הזה הסקריפט **לא מבצע שום
שינוי אמיתי** בחשבון - הוא רק מדפיס ורושם ללוג מה הוא *היה* עושה.

```bash
python main.py
```

עברו על הלוג (`logs/automation_log.jsonl`) ווודאו שההחלטות הגיוניות - האם המודעות
שסומנו כ"לא רווחיות" באמת כאלה, האם הרוטציה בוחרת קריאטיבים נכונים וכו'.

**רק אחרי שבדקתם ואתם בטוחים** - שנו ב-`config.py`:
```python
DRY_RUN = False
```

## הרצה אוטומטית יומית (cron)

```bash
crontab -e
```
```
0 8 * * * cd /path/to/tiktok_ads_automation && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

## מבנה הקבצים

- `config.py` - כל ההגדרות (טוקן, חשבון מפרסם, ספים)
- `auth.py` - זרימת OAuth החד-פעמית מול TikTok Marketing API
- `insights.py` - משיכת נתוני ביצועים מה-API (ברמת מודעה)
- `rules.py` - מנוע הכללים (מי להשהות / למי לרענן קריאטיב)
- `actions.py` - הפעולות בפועל מול ה-API (השהיה, העלאת וידאו, עדכון קריאטיב)
- `creative_rotation.py` - בחירת הווידאו/קופי הבא בתור מהבנק
- `logger.py` - רישום ללוג
- `main.py` - `authorize` (חד-פעמי) / הרצה רגילה (להריץ דרך cron כל יום)
- `rotation_state.json` - נוצר אוטומטית, זוכר איזה קריאטיב שימש אחרון לכל מודעה

## אזהרות חשובות

- **אין אישור בזמן אמת** - ברגע ש-`DRY_RUN=False`, הסקריפט משהה מודעות ומחליף
  קריאטיבים באופן עצמאי לגמרי, על כסף אמיתי. בדקו היטב לפני שמכבים DRY_RUN.
- **שם מדד ה-ROAS תלוי בחשבון** - ראו סעיף 5 למעלה. אם לא מתאים, כלל ה-ROAS לא
  יעבוד כמצופה.
- **מגבלת קצב** - כ-600 בקשות בדקה לכל endpoint, אבל גם מגבלות לפי אפליקציה/טוקן/
  חשבון מפרסם - אם יש הרבה מודעות, כדאי להוסיף השהיה קטנה בין קריאות.
