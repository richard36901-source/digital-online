@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo מתקין תלויות (בפעם הראשונה זה לוקח כמה שניות)...
py -m pip install -q -r requirements.txt

echo מפעיל את לוח הבקרה - הדפדפן ייפתח אוטומטית תוך רגע...
py webapp.py

echo.
echo לוח הבקרה נסגר. אפשר לסגור את החלון הזה.
pause
