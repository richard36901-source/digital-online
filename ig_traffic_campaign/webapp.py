# -*- coding: utf-8 -*-
"""
לוח בקרה - כיבוי/הדלקת Ad Sets ועדכון תקציב יומי בלחיצת כפתור, בלי CMD. מריץ שרת
אמיתי מול Meta Marketing API, ולכן חייב לרוץ מקומית עם הטוקן - לא ניתן לפרסם את זה
כדף ציבורי (בניגוד ל-performance_dashboard.html שהוא קריאה-בלבד).
מקביל בכוונה ל-tiktok_ads_automation/webapp.py.

זמין גם ברשת ה-WiFi המקומית (לא רק במחשב עצמו) כדי לאפשר גישה מהאייפון - ולכן מוגן
בסיסמה (config.PANEL_PASSWORD). שינוי סיסמת ברירת המחדל הוא חובה לפני הרצה - ראו
בדיקת ה-startup למטה.

הרצה:
  py webapp.py
במחשב עצמו: http://localhost:5001
מהטלפון (אותה רשת WiFi): הכתובת שתודפס בטרמינל, למשל http://192.168.1.50:5001
באייפון: Safari -> שיתוף -> "הוסף למסך הבית" כדי שיהיה כמו אפליקציה עם אייקון.

מכבד את config.DRY_RUN בדיוק כמו שאר האוטומציה - אם True, הלחיצות רק נרשמות
ולא באמת משנות כלום ב-Meta (יוצג באנר "מצב בדיקה" בראש הדף).

פורט 5001 (לא 5000) בכוונה - כדי שאפשר יהיה להריץ את זה במקביל ל-webapp.py
של tiktok_ads_automation על אותו מחשב בלי התנגשות פורטים.
"""

import contextlib
import io
import secrets
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import requests
from flask import Flask, jsonify, redirect, request, session, url_for

import actions
import campaign_launch
import config
import insights

app = Flask(__name__)

# ==== ג'ובים ברקע (launch) ====
# השקת סרטונים חדשים יכולה לקחת כמה דקות (הורדה מ-Drive + העלאת וידאו ל-Meta) - רצה
# ב-thread נפרד כדי שהבקשה מהדפדפן תחזור מיד, והדף עושה polling לסטטוס ולוג במקום
# לחכות לתגובה אחת.
_jobs = {}
_jobs_lock = threading.Lock()


def _run_job(job_id: str, fn) -> None:
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
        with _jobs_lock:
            _jobs[job_id]["status"] = "done"
    except Exception:
        buf.write("\n\n--- שגיאה ---\n" + traceback.format_exc())
        with _jobs_lock:
            _jobs[job_id]["status"] = "error"
    finally:
        with _jobs_lock:
            _jobs[job_id]["log"] = buf.getvalue()


def _start_job(name: str, fn) -> str:
    with _jobs_lock:
        for job in _jobs.values():
            if job["name"] == name and job["status"] == "running":
                raise RuntimeError(f"{name} כבר רץ - חכו שיסתיים.")
        job_id = f"{name}-{int(time.time() * 1000)}"
        _jobs[job_id] = {"name": name, "status": "running", "log": ""}
    thread = threading.Thread(target=_run_job, args=(job_id, fn), daemon=True)
    thread.start()
    return job_id


_SECRET_KEY_FILE = Path(__file__).parent / ".flask_secret_key"
if _SECRET_KEY_FILE.exists():
    app.secret_key = _SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
else:
    app.secret_key = secrets.token_hex(32)
    _SECRET_KEY_FILE.write_text(app.secret_key, encoding="utf-8")


@app.before_request
def require_login():
    if request.endpoint in ("login", "static"):
        return
    if not session.get("authed"):
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(url_for("login"))


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>כניסה - לוח בקרה אינסטגרם</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root { --bg: #0e1016; --card: #171a23; --ink: #e9ebf1; --muted: #8c93a4; --border: #262b38;
    --brand: #6366f1; --brand-2: #22d3ee; --red: #f87171; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: 'Heebo', 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--ink);
    min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
  }
  form {
    background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 32px;
    width: 100%; max-width: 320px; box-shadow: 0 8px 24px -12px rgba(0,0,0,.6);
  }
  h1 { font-size: 17px; margin: 0 0 20px; text-align: center; }
  input {
    width: 100%; background: #1b1f29; border: 1px solid var(--border); color: var(--ink);
    border-radius: 10px; padding: 12px 14px; font-family: inherit; font-size: 15px; margin-bottom: 14px;
  }
  button {
    width: 100%; border: none; border-radius: 10px; padding: 12px; font-family: inherit;
    font-size: 14px; font-weight: 700; cursor: pointer; color: white;
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
  }
  .error { color: var(--red); font-size: 13px; text-align: center; margin: 0 0 14px; }
</style>
</head>
<body>
<form method="POST">
  <h1>לוח בקרה - תנועה לאינסטגרם</h1>
  __ERROR__
  <input type="password" name="password" placeholder="סיסמה" autofocus>
  <button type="submit">כניסה</button>
</form>
</body>
</html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == config.PANEL_PASSWORD:
            session.permanent = True
            session["authed"] = True
            return redirect(url_for("index"))
        error = '<p class="error">סיסמה שגויה</p>'
    return LOGIN_PAGE.replace("__ERROR__", error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def get_lan_ip() -> str:
    """מזהה את כתובת ה-IP המקומית של המחשב ברשת (כדי להציג לחיבור מהאייפון)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def build_adsets_view(campaign_id: str) -> list:
    """
    שולף את כל ה-Ad Sets של הקמפיין (סטטוס + תקציב) ומצרף להם ביצועים (הוצאה/קליקים/CTR)
    מ-insights.fetch_ad_insights - בדיוק כמו tiktok_ads_automation/webapp.py's build_ads_view,
    רק ברמת Ad Set במקום Ad (אצלנו זה יחס 1:1 - סט אחד לכל סרטון).
    """
    url = f"{config.GRAPH_URL}/{campaign_id}"
    resp = requests.get(url, params={
        "fields": "adsets.limit(200){id,name,status,daily_budget}",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    adsets = data.get("adsets", {}).get("data", [])

    perf_by_adset = {}
    for row in insights.fetch_ad_insights(campaign_id):
        adset_id = row.get("adset_id")
        perf_by_adset[adset_id] = {
            "spend": float(row.get("spend", 0)),
            "impressions": int(row.get("impressions", 0)),
            "clicks": insights.extract_link_clicks(row),
        }

    rows = []
    for a in adsets:
        perf = perf_by_adset.get(a["id"], {"spend": 0, "impressions": 0, "clicks": 0})
        ctr = (perf["clicks"] / perf["impressions"] * 100) if perf["impressions"] else 0
        name = a.get("name", "")
        if name.endswith(" - Ad Set"):
            name = name[: -len(" - Ad Set")]
        rows.append({
            "adset_id": a["id"],
            "name": name,
            "status": a.get("status", "UNKNOWN"),
            "daily_budget_ils": int(a.get("daily_budget") or 0) / 100,
            "spend": perf["spend"],
            "clicks": perf["clicks"],
            "ctr": ctr,
        })
    rows.sort(key=lambda r: r["ctr"], reverse=True)
    return rows


@app.route("/api/adsets")
def api_adsets():
    try:
        campaign = insights.find_campaign()
        if not campaign:
            return jsonify({"dry_run": config.DRY_RUN, "adsets": []})
        rows = build_adsets_view(campaign["id"])
        return jsonify({"dry_run": config.DRY_RUN, "adsets": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/adsets/<adset_id>/toggle", methods=["POST"])
def api_toggle(adset_id):
    enable = request.json.get("enable", False)
    try:
        actions.enable_adset(adset_id) if enable else actions.pause_adset(adset_id)
        return jsonify({"ok": True, "status": "ACTIVE" if enable else "PAUSED", "dry_run": config.DRY_RUN})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/adsets/<adset_id>/budget", methods=["POST"])
def api_budget(adset_id):
    body = request.json
    new_budget = body.get("budget")
    if new_budget is None:
        return jsonify({"ok": False, "error": "חסר budget"}), 400
    try:
        actions.update_adset_budget(adset_id, float(new_budget))
        return jsonify({"ok": True, "budget": new_budget, "dry_run": config.DRY_RUN})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/launch", methods=["POST"])
def api_launch():
    try:
        job_id = _start_job("launch", campaign_launch.main)
        return jsonify({"ok": True, "job_id": job_id, "dry_run": config.DRY_RUN})
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 409


@app.route("/api/job/<job_id>")
def api_job_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(job))


PAGE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="IG בקרה">
<meta name="theme-color" content="#0e1016">
<title>לוח בקרה - תנועה לאינסטגרם</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0e1016; --card: #171a23; --ink: #e9ebf1; --muted: #8c93a4; --border: #262b38;
    --brand: #6366f1; --brand-2: #22d3ee;
    --green: #34d399; --green-soft: #113328;
    --red: #f87171; --red-soft: #3a1818;
    --amber: #fbbf24; --amber-soft: #3a2a0d;
    --radius: 16px; --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px -12px rgba(0,0,0,.55);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: 'Heebo', 'Segoe UI', Arial, sans-serif;
    background: var(--bg); color: var(--ink); padding: 28px clamp(16px, 4vw, 48px) 60px;
  }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 13px; margin: 0 0 20px; }
  .banner {
    background: var(--amber-soft); color: var(--amber); border: 1px solid rgba(251,191,36,.25);
    border-radius: 12px; padding: 12px 16px; font-size: 13px; font-weight: 600; margin-bottom: 20px;
    display: none;
  }
  .banner.show { display: block; }
  .card {
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); overflow: hidden;
  }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  thead th {
    text-align: right; padding: 12px 14px; background: #1b1f29; color: var(--muted);
    font-weight: 600; font-size: 12px; border-bottom: 1px solid var(--border);
  }
  tbody td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: rgba(255,255,255,.02); }

  .status-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
  .status-badge.on { background: var(--green-soft); color: var(--green); }
  .status-badge.off { background: #262b38; color: var(--muted); }

  .toggle-btn {
    border: none; border-radius: 8px; padding: 7px 14px; font-family: inherit;
    font-size: 12.5px; font-weight: 700; cursor: pointer; transition: opacity .15s;
  }
  .toggle-btn:hover { opacity: .85; }
  .toggle-btn:disabled { opacity: .5; cursor: wait; }
  .toggle-btn.pause { background: var(--red-soft); color: var(--red); }
  .toggle-btn.enable { background: var(--green-soft); color: var(--green); }

  .budget-form { display: flex; align-items: center; gap: 6px; }
  .budget-form input {
    width: 70px; background: #1b1f29; border: 1px solid var(--border); color: var(--ink);
    border-radius: 8px; padding: 6px 8px; font-family: inherit; font-size: 13px; text-align: center;
  }
  .budget-form button {
    border: none; border-radius: 8px; padding: 7px 12px; font-family: inherit; font-size: 12.5px;
    font-weight: 700; cursor: pointer; background: linear-gradient(135deg, var(--brand), var(--brand-2)); color: white;
  }
  .budget-form button:hover { opacity: .9; }
  .budget-form button:disabled { opacity: .5; cursor: wait; }
  .saved-flash { color: var(--green); font-size: 11px; margin-right: 4px; opacity: 0; transition: opacity .3s; }
  .saved-flash.show { opacity: 1; }

  .muted { color: var(--muted); }
  .empty { text-align: center; color: var(--muted); padding: 40px; }
  .refresh-btn {
    border: 1px solid var(--border); background: var(--card); color: var(--ink);
    border-radius: 10px; padding: 8px 16px; font-family: inherit; font-size: 13px;
    font-weight: 600; cursor: pointer; margin-bottom: 16px;
  }
  .refresh-btn:hover { border-color: var(--brand); }
  .actions-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
  .action-btn {
    border: none; border-radius: 10px; padding: 9px 16px; font-family: inherit; font-size: 13px;
    font-weight: 700; cursor: pointer; color: white;
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
  }
  .action-btn:hover { opacity: .9; }
  .action-btn:disabled { opacity: .5; cursor: wait; }
  .job-log {
    display: none; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 16px 18px; margin-bottom: 20px; box-shadow: var(--shadow);
  }
  .job-log.show { display: block; }
  .job-log .job-title { font-size: 13px; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
  .job-log pre {
    background: #0b0d13; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px;
    font-size: 12px; max-height: 220px; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
    color: var(--muted); margin: 0; direction: ltr; text-align: left;
  }
  .job-badge { font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px; }
  .job-badge.running { background: var(--amber-soft); color: var(--amber); }
  .job-badge.done { background: var(--green-soft); color: var(--green); }
  .job-badge.error { background: var(--red-soft); color: var(--red); }
  .header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .logout-link { color: var(--muted); font-size: 12.5px; text-decoration: none; white-space: nowrap; padding-top: 4px; }
  .logout-link:hover { color: var(--ink); }

  /* מסך צר (אייפון) - הופך כל שורת טבלה לכרטיס מוערם במקום גלילה אופקית לא נוחה */
  @media (max-width: 700px) {
    body { padding: 16px 12px 40px; }
    h1 { font-size: 17px; }
    table, thead, tbody, tr, td { display: block; width: 100%; }
    thead { display: none; }
    tbody tr {
      border: 1px solid var(--border); border-radius: 12px; padding: 4px 0; margin-bottom: 12px;
    }
    tbody tr:last-child { margin-bottom: 0; }
    tbody td {
      display: flex; align-items: center; justify-content: space-between; gap: 10px;
      padding: 10px 14px; border-bottom: 1px solid var(--border);
    }
    tbody td:last-child { border-bottom: none; }
    tbody td::before { content: attr(data-label); font-size: 11.5px; font-weight: 600; color: var(--muted); flex-shrink: 0; }
    tbody td[data-label="סרטון"] { font-weight: 700; font-size: 14.5px; }
    tbody td[data-label="סרטון"]::before { display: none; }
    .budget-form { flex: 1; justify-content: flex-end; }
  }
</style>
</head>
<body>

<div class="header-row">
  <div>
    <h1>לוח בקרה - תנועה לאינסטגרם (ben_nahum_1)</h1>
    <p class="sub">כיבוי/הדלקת Ad Sets ועדכון תקציב יומי בלחיצת כפתור. פועל על החשבון המחובר מקומית בלבד.</p>
  </div>
  <a class="logout-link" href="/logout">התנתקות</a>
</div>

<div id="dryRunBanner" class="banner">🧪 מצב בדיקה (DRY_RUN=true) - הלחיצות כאן <b>לא</b> משנות באמת כלום ב-Meta. כדי לבצע שינויים אמיתיים, הגדירו משתנה סביבה DRY_RUN=false.</div>

<div class="actions-row">
  <button class="refresh-btn" onclick="loadAdsets()">🔄 רענן נתונים</button>
  <button class="action-btn" id="launchBtn" onclick="confirmLaunch()">🚀 השק סרטונים חדשים</button>
</div>

<div class="job-log" id="jobLog">
  <div class="job-title"><span id="jobTitle"></span> <span class="job-badge" id="jobBadge"></span></div>
  <pre id="jobOutput"></pre>
</div>

<div class="card">
  <table>
    <thead>
      <tr>
        <th>סרטון</th>
        <th>סטטוס</th>
        <th>הפעלה/השהיה</th>
        <th>תקציב יומי (₪)</th>
        <th>הוצאה</th>
        <th>קליקים</th>
        <th>CTR</th>
      </tr>
    </thead>
    <tbody id="adsetsBody">
      <tr><td colspan="7" class="empty">טוען...</td></tr>
    </tbody>
  </table>
</div>

<script>
async function loadAdsets() {
  const tbody = document.getElementById('adsetsBody');
  tbody.innerHTML = '<tr><td colspan="7" class="empty">טוען...</td></tr>';
  try {
    const res = await fetch('/api/adsets');
    const data = await res.json();
    if (data.error) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">שגיאה: ${data.error}</td></tr>`;
      return;
    }
    document.getElementById('dryRunBanner').classList.toggle('show', data.dry_run);

    if (!data.adsets.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">אין עדיין Ad Sets - הריצו "השק סרטונים חדשים"</td></tr>';
      return;
    }

    tbody.innerHTML = data.adsets.map(a => {
      const isOn = a.status === 'ACTIVE';
      return `
        <tr>
          <td data-label="סרטון">${a.name}</td>
          <td data-label="סטטוס"><span class="status-badge ${isOn ? 'on' : 'off'}">${isOn ? 'פעיל' : 'מושהה'}</span></td>
          <td data-label="הפעלה/השהיה">
            <button class="toggle-btn ${isOn ? 'pause' : 'enable'}" onclick="toggleAdset(this, '${a.adset_id}', ${!isOn})">
              ${isOn ? '⏸ השהה' : '▶ הפעל'}
            </button>
          </td>
          <td data-label="תקציב יומי (₪)">
            <div class="budget-form">
              <input type="number" min="1" step="1" value="${a.daily_budget_ils}" id="budget-${a.adset_id}">
              <button onclick="saveBudget(this, '${a.adset_id}')">שמור</button>
              <span class="saved-flash" id="flash-${a.adset_id}">✓ נשמר</span>
            </div>
          </td>
          <td data-label="הוצאה">₪${a.spend.toFixed(2)}</td>
          <td data-label="קליקים">${a.clicks.toFixed(0)}</td>
          <td data-label="CTR">${a.ctr.toFixed(2)}%</td>
        </tr>`;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">שגיאת רשת: ${e}</td></tr>`;
  }
}

async function toggleAdset(btn, adsetId, enable) {
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = '...';
  try {
    const res = await fetch(`/api/adsets/${adsetId}/toggle`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({enable}),
    });
    const data = await res.json();
    if (!data.ok) { alert('שגיאה: ' + data.error); btn.disabled = false; btn.textContent = original; return; }
    loadAdsets();
  } catch (e) {
    alert('שגיאת רשת: ' + e);
    btn.disabled = false; btn.textContent = original;
  }
}

async function saveBudget(btn, adsetId) {
  const input = document.getElementById(`budget-${adsetId}`);
  const value = parseFloat(input.value);
  if (!value || value <= 0) { alert('תקציב לא תקין'); return; }
  btn.disabled = true;
  try {
    const res = await fetch(`/api/adsets/${adsetId}/budget`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({budget: value}),
    });
    const data = await res.json();
    btn.disabled = false;
    if (!data.ok) { alert('שגיאה: ' + data.error); return; }
    const flash = document.getElementById(`flash-${adsetId}`);
    flash.classList.add('show');
    setTimeout(() => flash.classList.remove('show'), 2000);
  } catch (e) {
    alert('שגיאת רשת: ' + e);
    btn.disabled = false;
  }
}

function confirmLaunch() {
  const msg = 'זה יוריד סרטונים חדשים מה-Drive (אם יש) וייצור עבורם Ad Set + קריאטיב + מודעה. סרטונים שכבר הושקו ידולגו. ';
  const extra = document.getElementById('dryRunBanner').classList.contains('show')
    ? '(מצב בדיקה פעיל - לא יבוצע שינוי אמיתי)'
    : '(DRY_RUN כבוי - זו פעולה אמיתית!)';
  if (confirm(msg + extra + ' להמשיך?')) {
    runLaunchJob();
  }
}

async function runLaunchJob() {
  const launchBtn = document.getElementById('launchBtn');
  launchBtn.disabled = true;

  const jobLog = document.getElementById('jobLog');
  const jobTitle = document.getElementById('jobTitle');
  const jobBadge = document.getElementById('jobBadge');
  const jobOutput = document.getElementById('jobOutput');

  jobLog.classList.add('show');
  jobTitle.textContent = 'השקת סרטונים חדשים';
  jobBadge.textContent = 'רץ...';
  jobBadge.className = 'job-badge running';
  jobOutput.textContent = 'מתחיל...';

  try {
    const res = await fetch('/api/launch', {method: 'POST'});
    const data = await res.json();
    if (!data.ok) {
      jobBadge.textContent = 'שגיאה';
      jobBadge.className = 'job-badge error';
      jobOutput.textContent = data.error;
      launchBtn.disabled = false;
      return;
    }
    pollJob(data.job_id, jobBadge, jobOutput, launchBtn);
  } catch (e) {
    jobBadge.textContent = 'שגיאה';
    jobBadge.className = 'job-badge error';
    jobOutput.textContent = 'שגיאת רשת: ' + e;
    launchBtn.disabled = false;
  }
}

async function pollJob(jobId, jobBadge, jobOutput, launchBtn) {
  try {
    const res = await fetch(`/api/job/${jobId}`);
    const job = await res.json();
    jobOutput.textContent = job.log || 'מעבד...';
    jobOutput.scrollTop = jobOutput.scrollHeight;

    if (job.status === 'running') {
      setTimeout(() => pollJob(jobId, jobBadge, jobOutput, launchBtn), 1500);
      return;
    }

    jobBadge.textContent = job.status === 'done' ? 'הושלם' : 'שגיאה';
    jobBadge.className = 'job-badge ' + (job.status === 'done' ? 'done' : 'error');
    launchBtn.disabled = false;
    loadAdsets();
  } catch (e) {
    jobBadge.textContent = 'שגיאה';
    jobBadge.className = 'job-badge error';
    jobOutput.textContent = 'שגיאת רשת בבדיקת סטטוס: ' + e;
    launchBtn.disabled = false;
  }
}

loadAdsets();
</script>

</body>
</html>"""


@app.route("/")
def index():
    return PAGE


if __name__ == "__main__":
    import webbrowser

    if config.PANEL_PASSWORD == "שנה_את_הסיסמה":
        print("שגיאה: יש להגדיר סיסמה אמיתית לפני הפעלה - אחרת כל מכשיר ברשת ה-WiFi יוכל להיכנס.")
        print('הריצו: set IG_PANEL_PASSWORD=משהו-סודי-שלכם   (ואז py webapp.py שוב)')
        sys.exit(1)

    lan_ip = get_lan_ip()
    local_url = "http://localhost:5001"
    lan_url = f"http://{lan_ip}:5001"
    print(f"לוח הבקרה זמין במחשב הזה ב: {local_url}")
    print(f"ומהאייפון/מכשיר אחר, כשהם על אותה רשת WiFi, ב: {lan_url}")
    print("(באייפון: Safari -> כפתור השיתוף -> 'הוסף למסך הבית' כדי שיהיה כמו אפליקציה)")
    threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()
    app.run(host="0.0.0.0", port=5001, debug=False)
