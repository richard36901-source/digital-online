# קמפיין תנועה לאינסטגרם - ben_nahum_1

בונה קמפיין Meta Ads אחד עם Ad Set נפרד לכל סרטון (13 סרטונים = 13 סטים), תקציב יומי
של 10 ש"ח לכל סט בנפרד, מטרה: ביקורים בפרופיל האינסטגרם `ben_nahum_1`.

מודול נפרד מ-`meta_ads_automation/` בכוונה: משתמש באותו טוקן/חשבון API, אבל פועל על
חשבון המודעות "יהב" (act_330184635273905) שנשאר בכוונה מחוץ להיקף האוטומציה היומית
של רחל/טל/גל (ראה ההערה ב-`meta_ads_automation/config.py`).

## למה זה חייב לרוץ אצלך ולא אצל Claude?

בדיוק כמו ב-`meta_ads_automation` - הסביבה שבה Claude מריץ קוד חסומה מגישה הן ל-
graph.facebook.com והן ל-Google Drive/APIs חיצוניים באופן כללי. כל הקבצים כאן נכתבו
ע"י Claude אבל **לא הורצו** מול ה-API האמיתי - צריך להריץ אותם על מחשב/שרת עם גישה
רגילה לאינטרנט.

## התקנה

```bash
cd ig_traffic_campaign
python3 -m venv venv
source venv/bin/activate   # ב-Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## הגדרה (חובה לפני הרצה ראשונה)

### 1. הטוקן
אותו טוקן כמו ב-`meta_ads_automation` (System User עם `ads_management` + `business_management`).

```bash
export META_ACCESS_TOKEN="הטוקן_שלך_כאן"
```

### 2. בדיקת הרשאות + איתור PAGE_ID / IG_ACTOR_ID

```bash
python check_permissions.py
```

זה יבדוק שהטוקן תקף, שיש גישה לחשבון act_330184635273905, ויציג רשימת דפים + חשבונות
אינסטגרם מחוברים. **חפש את השורה שבה `username == "ben_nahum_1"`**, והעתק את ה-`page_id`
וה-`ig_actor_id` שלה ל-`config.py` (`PAGE_ID`, `IG_ACTOR_ID`). אל תנחש - אם ben_nahum_1
לא מופיע ברשימה, סימן שהטוקן/דף לא מחוברים נכון לפרופיל הזה, ויש לתקן בהגדרות הדף
בפייסבוק (Page → Instagram → Connect Account) לפני שממשיכים.

### 3. גישה ל-Google Drive

הסרטונים נמצאים בתיקייה בבעלות `benk9922@gmail.com`. כדי להוריד אותם דרך ה-API:

**לפני שיוצרים OAuth Client חדש - בדקו קודם אם כבר יש לכם אחד.** אם יש לכם פרויקט/
אוטומציה אחרת (למשל בצד ה-TikTok, אם היא ניגשת לאותה תיקיית דרייב) עם `client_secret*.json`
קיים שכבר מאושר לגשת לתיקייה `1SWAcj6fAOcLn2y4NMI8O_HQWJFBozmMV` - אפשר פשוט להעתיק
אותו לכאן ולשנות את שמו ל-`credentials.json`, ולדלג על שלבים 1-4. **חיפשתי בריפו הזה
(`digital-online-1`) ולא מצאתי שום `credentials.json`/`client_secret*.json`/`token.json`
או קוד קיים שמשתמש ב-Google Drive API** - אם יש לכם קובץ כזה, הוא חי במקום אחר (פרויקט/
מחשב נפרד) ולא משהו שאני יכול לאתר או להעביר מכאן.

אם אין קובץ קיים - זה תהליך חד-פעמי:

1. היכנסו ל-[Google Cloud Console](https://console.cloud.google.com/) עם המשתמש שלכם
   (`yahavmor77@gmail.com`), צרו פרויקט (או השתמשו בקיים).
2. הפעילו את **Google Drive API** (APIs & Services → Enable APIs → Google Drive API).
3. צרו **OAuth Client ID** מסוג **Desktop app** (APIs & Services → Credentials → Create
   Credentials → OAuth client ID).
4. הורידו את קובץ ה-JSON, שנו את שמו ל-`credentials.json`, ושימו אותו בתיקיית
   `ig_traffic_campaign/` (זהה למיקום שמוגדר ב-`config.GOOGLE_OAUTH_CREDENTIALS_FILE`).
5. ודאו שהתיקייה בדרייב (או הקבצים בתוכה) משותפת גם עם החשבון שלכם (`yahavmor77@gmail.com`)
   לפחות בהרשאת צפייה - אחרת ה-API יחזיר "File not found" גם עם אישור תקין.
6. בהרצה הראשונה של `campaign_launch.py` (או `drive_videos.py` ישירות), ייפתח דפדפן
   לאישור חד-פעמי. לאחר מכן נשמר `token.json` ולא תצטרכו לאשר שוב.

**אל תעלו את `credentials.json` או `token.json` ל-git** (הם לא ב-`.gitignore` כרגע - הוסיפו
אותם, בדיוק כמו שהטוקן של Meta לא נמצא ב-git).

### 4. בדיקת config.py

- ודאו ש-13 הסרטונים תואמים בפועל לקבצים בתיקיית הדרייב (השדה `match` בכל פריט ב-
  `config.VIDEOS`) - הרצה עם `DRY_RUN=False` תיכשל בבירור אם קובץ לא נמצא/נמצא כפול,
  במקום לנחש.
- **וודאו את `CAMPAIGN_OBJECTIVE` / `OPTIMIZATION_GOAL` / `DESTINATION_TYPE`** - אלה
  נכתבו לפי ההשערה הכי טובה של Claude נכון לתאריך הכתיבה (ללא אפשרות לבדוק מול ה-API
  בפועל, ראו הסבר למעלה). אם `create_ad_set` נכשל בשגיאה על `optimization_goal` לא
  תקין, **הודעת השגיאה מ-Meta עצמה תפרט את כל הערכים התקינים הקיימים כרגע** - עדכנו
  את `config.py` לפי זה ונסו שוב.

## הרצה ראשונה - חובה במצב DRY RUN

`DRY_RUN = True` הוא ברירת המחדל ב-`config.py`. במצב הזה:
- אין הורדת קבצים אמיתית מ-Drive
- אין העלאת וידאו ל-Meta
- אין יצירת קמפיין/סט/מודעה אמיתיים
- רק נדפס ונרשם ללוג (`logs/campaign_launch_log.jsonl`) מה *היה* קורה

```bash
python campaign_launch.py
```

עברו על הפלט וודאו שרשימת 13 הסרטונים/הסטים הגיונית, לפני שממשיכים.

## הרצה אמיתית

**רק אחרי** ש-DRY RUN עבר בסדר, `check_permissions.py` אישר הרשאות תקינות, ו-Drive
מוגדר:

`DRY_RUN` נשלט ע"י משתנה סביבה (כמו `META_ACCESS_TOKEN`) - **אין צורך לערוך את
`config.py`** בכל הרצה (זה בכוונה, כדי לא לגרום להתנגשויות חוזרות ב-`git pull` בגלל
עריכה מקומית לא-מחויבת):

```bash
# Windows cmd:
set DRY_RUN=false
# macOS/Linux:
export DRY_RUN=false
```

```bash
python campaign_launch.py
```

בלי `DRY_RUN=false` מוגדר, ברירת המחדל היא תמיד `True` (בטוח).

שימו לב: **גם בהרצה אמיתית, הקמפיין וכל הסטים/מודעות נוצרים במצב `PAUSED`** (לא
`ACTIVE`) - זו החלטת בטיחות מכוונת. שום דבר לא יתחיל להוציא כסף עד שתיכנסו ל-Ads
Manager, תעברו ידנית על כל אחד מ-13 הסטים (טירגוט, תקציב, קריאייטיב), ותפעילו ידנית
את מה שנראה תקין.

## דשבורד ביצועים (performance_dashboard.html)

מקביל בכוונה ל-`tiktok_ads_automation/performance_dashboard.html` - קריאה-בלבד, לא
נוגע בשום מודעה. מדרג את 13 הסרטונים לפי CTR (קליקים על הלינק מתוך חשיפות), כדי לזהות
אילו סרטונים "מתבלטים" ואילו "כושלים".

```bash
python dashboard.py
```

עובד רק אחרי שהקמפיין כבר קיים בפועל (אחרי `campaign_launch.py` עם `DRY_RUN=False`) -
לפני זה יציג "אין עדיין נתונים".

**פרסום אוטומטי:** יש GitHub Action (`.github/workflows/update-ig-traffic-dashboard.yml`,
מקביל ל-`update-tiktok-ads-dashboard.yml`) שמריץ את זה כל 5 דקות ודוחף אם השתנה - **אבל
זה רץ רק על branch `main`**, ולכן לא יתחיל לפעול עד שהברנץ' הזה ימוזג (ראו השיחה על
תזמון המיזוג - רק אחרי הרצה אמיתית מוצלחת). שימוש באותו secret קיים
(`META_ACCESS_TOKEN`) שכבר מוגדר ב-repo עבור `update-dashboard.yml` - אין צורך בהגדרה
נוספת. לאחר המיזוג, הדשבורד יהיה זמין ב-
`https://funnel.digitalonline.co.il/ig_traffic_campaign/performance_dashboard.html`
(אותו דפוס בדיוק כמו כתובת ה-TikTok).

**שים לב:** בכוונה לא בניתי כאן מקבילה ל-`tiktok_ads_automation/webapp.py` (לוח הבקרה
האינטראקטיבי עם כפתורי השהיה/תקציב) - רק את חלק הדיווח הקריא-בלבד, לפי מה שביקשת.
אם תרצה גם את זה בהמשך, תגיד.

## מבנה הקבצים

- `config.py` - כל ההגדרות (טוקן, חשבון, יעד, סרטונים, תקציב)
- `check_permissions.py` - בדיקת הרשאות + איתור PAGE_ID/IG_ACTOR_ID (הרצה ידנית חד-פעמית)
- `drive_videos.py` - הורדת הסרטונים מ-Google Drive
- `video_upload.py` - העלאת וידאו ל-Meta + המתנה לעיבוד + thumbnail
- `campaign_launch.py` - הלוגיקה המרכזית: קמפיין → (לכל סרטון) Ad Set → קריאטיב → מודעה
- `insights.py` - משיכת ביצועים (Insights) מסונן לקמפיין הזה בלבד
- `dashboard.py` - בונה את `performance_dashboard.html` (קריאה-בלבד)
- `logger.py` - רישום ללוג (JSON Lines)
- `logs/campaign_launch_log.jsonl` - נוצר אוטומטית בהרצה
- `performance_dashboard.html` - נוצר אוטומטית ע"י `dashboard.py`

## אזהרות חשובות

- **אין אישור בזמן אמת** בתוך הסקריפט עצמו - אבל בזכות `CREATED_STATUS = "PAUSED"`,
  יש לכם עדיין הזדמנות לאישור ידני ב-Ads Manager לפני שכסף אמיתי מתחיל לזוז.
- **הטוקן** - אל תשמרו אותו בקוד/git/צ'אט. משתנה סביבה בלבד.
- **13 קריאות להעלאת וידאו + polling** - כל וידאו יכול לקחת עד כמה דקות לעבד בצד Meta.
  ריצה מלאה של 13 סרטונים עלולה לקחת זמן - זה תקין, לא לעצור באמצע.
