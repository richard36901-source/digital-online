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

## השקת קמפיין חדש - קידום אינסטגרם (campaign_launch.py)

מיועד להעלות סרטונים כמודעות ממומנות חדשות (לא רק לנהל מודעות קיימות), כל סרטון
בקבוצת מודעות (ad group) נפרדת עם תקציב יומי עצמאי, כולן תחת קמפיין משותף אחד,
מפנות ל-`config.DESTINATION_URL` (כרגע: https://www.instagram.com/ben_nahum_1/).

### לפני הרצה אמיתית - שלושה דברים למלא

1. **הורדת הסרטונים** - הקבצים ב-Google Drive (5 סרטונים) לא נמצאים בגיט (כבדים
   מדי, וזה גם הכוונה - ראו `.gitignore`). הורידו אותם ידנית ל-
   `creative_bank/instagram_promo/videos/` כשהשם תואם למה שרשום ב-
   `creative_bank/instagram_promo/videos.json` (או ערכו את ה-JSON כך שיתאים לשמות
   שהורדתם).

2. **טירגוט (TARGETING_LOCATION_IDS)** - ריק כברירת מחדל. אחרי שיש `ACCESS_TOKEN`
   תקף:
   ```bash
   python main.py lookup-locations "ישראל"
   ```
   והעתיקו את ה-`location_id` שמתקבל ל-`config.TARGETING_LOCATION_IDS`.

3. **זהות מפרסם (IDENTITY_ID)** - חובה ע"פ TikTok לכל מודעה. ב-Ads Manager, תחת
   Assets → Identities, בחרו/צרו זהות (Custom identity או חשבון TikTok מאומת),
   והעתיקו את המזהה ל-`config.IDENTITY_ID` (או למשתנה סביבה `TIKTOK_ADS_IDENTITY_ID`).

### הרצה

```bash
python main.py launch
```

כרגיל, ב-`DRY_RUN=True` (ברירת מחדל) זה רק מדפיס/רושם מה היה קורה, בלי ליצור שום
דבר אמיתי ב-TikTok.

### אזהרת תקציב חשובה

**ביקשת ₪10 ליום לכל סרטון. TikTok אוכפת תקציב יומי מינימלי לכל ad group - בדרך כלל
סביב $20/יום (כ-₪74).** סביר מאוד שהקריאה ל-`/adgroup/create/` תיכשל עם שגיאת
ולידציה על תקציב נמוך מדי, כשתריצו בפועל (לא ב-DRY_RUN). זה בסדר ותקין - הריצו קודם
ב-DRY_RUN כדי לוודא שכל שאר הנתונים (וידאו, טקסט, טירגוט, זהות) תקינים, ואז נסו
הרצה אמיתית; אם תקבלו שגיאת "budget too low" (או דומה), הדביקו את השגיאה המדויקת
כאן ונעלה את `DAILY_BUDGET_PER_VIDEO_ILS` בהתאם למינימום שTikTok דורש בפועל.

### הערה על דיוק ה-API

`create_campaign` / `create_adgroup` / `create_ad` (ב-`actions.py`) ו-`search_locations`
(ב-`locations.py`) נכתבו לפי תיעוד TikTok Marketing API v1.3 הפומבי, **בלי אפשרות
לבדוק בפועל** - הסביבה שבה זה נכתב חסומה רשתית מ-TikTok. יכול להיות ששם שדה או ערך
enum ישתנה/יהיה שגוי. אם מתקבלת שגיאת ולידציה עם קוד/הודעה מ-TikTok - הדביקו אותה
בשיחה עם Claude ותתוקן בקוד בהתאם למה ש-TikTok בפועל מצפה.

## דשבורד ביצועים - אילו סרטונים מתבלטים (dashboard.py)

המטרה: להריץ את הקמפיין כמה ימים, ואז לראות לפי חשיפות/קליקים/CTR אילו סרטונים
"מתבלטים" (להמשיך ולהעלות להם תקציב/להשקיע בדומה) ואילו "כושלות" (להשהות - ראו
`main.py` הרגיל, שמשהה לפי `ROAS_THRESHOLD`; לצורך תנועה/מודעות בלבד, ה-CTR בדשבורד
הזה הוא האינדיקטור הרלוונטי, לא ROAS).

```bash
python main.py dashboard
```

יוצר/מרענן `performance_dashboard.html` (קריאה-בלבד, לא נוגע בשום מודעה) - פתחו
בדפדפן. מציג:
- סה"כ הוצאה/חשיפות/קליקים/CTR ממוצע
- דירוג כל הסרטונים לפי CTR, מהגבוה לנמוך, עם תיוג "🏆 מצטיינת" ל-CTR הכי גבוה
  ו-"⚠️ חלשה ביותר" לנמוך ביותר
- טבלה מלאה עם כל המדדים לכל סרטון (כולל עלות לקליק וסטטוס פעיל/מושהה)

הריצו את `python main.py dashboard` כמה שתרצו, כמה פעמים ביום - זו קריאה בלבד, לא
משפיעה על שום מודעה.

### מתעדכן אוטומטית (סטייל god_manager)

בדיוק כמו `god_manager.html` ב-`meta_ads_automation`, יש workflow ב-
`.github/workflows/update-tiktok-ads-dashboard.yml` שמריץ `python dashboard.py`
אוטומטית כל 15 דקות (ניתן לשנות את תדירות ה-cron בקובץ), מחליט אם `performance_dashboard.html`
השתנה, ואם כן - מבצע commit+push אוטומטי. הקובץ נשמר ב-git ומתפרסם עם שאר האתר
(GitHub Pages), כלומר **הוא ציבורי** - כל מי שיש לו את הקישור לאתר יכול לראות את
נתוני הביצועים (הוצאה, קליקים, CTR) של הקמפיין. אם זה לא רצוי, תגידו ונהפוך את זה
לפרטי (או נסיר את ה-workflow ונחזור להרצה ידנית בלבד).

**חובה כדי שזה יעבוד: secret בשם `TIKTOK_ADS_ACCESS_TOKEN` בהגדרות הריפו** -
Settings → Secrets and variables → Actions → New repository secret, עם הטוקן
שהתקבל מ-`python main.py authorize`. בלי זה ה-workflow ירוץ אבל ייכשל (אין טוקן
תקף). שימו לב: זהו secret נפרד מ-`META_ACCESS_TOKEN` הקיים כבר בריפו עבור
`meta_ads_automation`.

## לוח בקרה (webapp.py) - כיבוי/הדלקה/תקציב בלי CMD

דף בקרה מקומי עם כפתורים - לא צריך לזכור פקודות. מריץ שרת אמיתי מול TikTok, ולכן
**חייב לרוץ מקומית** עם הטוקן (בדיוק כמו כל שאר הפקודות) - לא ניתן לפרסם את זה
כדף ציבורי כמו `performance_dashboard.html`, כי כל מי שיפתח את הדף הזה יוכל
לכבות/להדליק מודעות ולשנות תקציבים בפועל.

```bash
py webapp.py
```

ואז פותחים בדפדפן: **http://localhost:5000**

הדף מציג טבלה של כל הסרטונים עם: סטטוס (פעיל/מושהה), כפתור השהה/הפעל, שדה תקציב
יומי + כפתור שמור, והוצאה/קליקים/CTR לצד כל שורה כדי שתדעו על סמך מה להחליט.
כל שינוי קורה מיד בלחיצה, בלי לרענן את הדף.

אם `DRY_RUN=True` ב-`config.py` (ברירת המחדל), יוצג באנר "מצב בדיקה" בראש הדף -
הלחיצות עדיין "עובדות" (מציגות שינוי בממשק) אבל לא שולחות שום דבר אמיתי ל-TikTok.
לפעולה אמיתית, שנו ל-`DRY_RUN=False`.

**הערה על דיוק ה-API:** `update_adgroup_budget` (עדכון תקציב) עדיין לא נבדק מול
TikTok בפועל - כמו כמה פונקציות קודמות בפרויקט הזה, יכול להיות שיחזור עם שגיאת
ולידציה בהרצה ראשונה. אם זה קורה, הדביקו את השגיאה המדויקת ותתוקן. `pause`/`enable`
כן אומתו (מבוססים על אותה קריאה שכבר עבדה ב-`main.py` הרגיל).

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
- `creative_rotation.py` - בחירת הווידאו/קופי הבא בתור מהבנק (לניהול מודעות קיימות)
- `webapp.py` - לוח בקרה מקומי עם כפתורים (`py webapp.py` -> http://localhost:5000)
- `campaign_launch.py` - השקת קמפיין חדש מאפס מ-`creative_bank/instagram_promo/`
- `locations.py` - חיפוש `location_id` לטירגוט גיאוגרפי
- `dashboard.py` - בונה `performance_dashboard.html` (דירוג סרטונים לפי CTR, קריאה-בלבד)
- `logger.py` - רישום ללוג
- `main.py` - `authorize` (חד-פעמי) / `lookup-locations` / `launch` / `dashboard` / הרצה רגילה (cron)
- `rotation_state.json` - נוצר אוטומטית, זוכר איזה קריאטיב שימש אחרון לכל מודעה

## אזהרות חשובות

- **אין אישור בזמן אמת** - ברגע ש-`DRY_RUN=False`, הסקריפט משהה מודעות ומחליף
  קריאטיבים באופן עצמאי לגמרי, על כסף אמיתי. בדקו היטב לפני שמכבים DRY_RUN.
- **שם מדד ה-ROAS תלוי בחשבון** - ראו סעיף 5 למעלה. אם לא מתאים, כלל ה-ROAS לא
  יעבוד כמצופה.
- **מגבלת קצב** - כ-600 בקשות בדקה לכל endpoint, אבל גם מגבלות לפי אפליקציה/טוקן/
  חשבון מפרסם - אם יש הרבה מודעות, כדאי להוסיף השהיה קטנה בין קריאות.
