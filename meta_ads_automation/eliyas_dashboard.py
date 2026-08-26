# -*- coding: utf-8 -*-
"""
eliyas_dashboard - דשבורד חיצוני, קריאה-בלבד, לקמפיין בודד ("קמפיין יהב-אליאס")
בחשבון המודעות של רחל, המיועד ללקוח צד ג' שאינו קשור לשאר הלקוחות המנוהלים.

נפרד לגמרי מ-god_manager.html: קובץ HTML משלו, לא כולל שום מידע על לקוחות/קמפיינים
אחרים. לא מבצע שום פעולה על החשבון - קורא נתונים בלבד.

מופעל אוטומטית דרך GitHub Actions (ראו update-dashboard.yml), וגם ידנית עם:
    python eliyas_dashboard.py
"""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import insights as insights_mod
from dashboard import PRESET_LABELS, STATUS_LABELS, fetch_campaigns, fetch_campaign_insights


def build_dashboard_data() -> tuple[dict, list[str]]:
    """
    בונה, עבור כל טווח תאריכים ב-config.DASHBOARD_DATE_PRESETS, שורת נתונים אחת
    עבור הקמפיין היחיד (config.ELIYAS_CAMPAIGN_ID). מחזיר (data, errors) כאשר
    data = {preset: row_or_None}.
    """
    errors: list[str] = []

    try:
        campaigns = fetch_campaigns(config.ELIYAS_AD_ACCOUNT_ID)
    except Exception as e:
        return {}, [f"שגיאה במשיכת רשימת הקמפיינים מהחשבון: {e}"]

    camp = campaigns.get(config.ELIYAS_CAMPAIGN_ID)
    if not camp:
        return {}, [f"הקמפיין (ID {config.ELIYAS_CAMPAIGN_ID}) לא נמצא בחשבון המודעות."]

    data: dict[str, dict] = {}

    for preset in config.DASHBOARD_DATE_PRESETS:
        try:
            insight_rows = fetch_campaign_insights(config.ELIYAS_AD_ACCOUNT_ID, preset)
        except Exception as e:
            errors.append(f"{PRESET_LABELS.get(preset, preset)}: {e}")
            continue

        row = next(
            (r for r in insight_rows if r.get("campaign_id") == config.ELIYAS_CAMPAIGN_ID),
            {},
        )

        spend = float(row.get("spend", 0) or 0)
        leads = insights_mod.extract_leads(row)
        roas = insights_mod.extract_roas(row)
        cost_per_lead = (spend / leads) if leads > 0 else None
        status_key = camp.get("effective_status", camp.get("status", "UNKNOWN"))

        data[preset] = {
            "campaign_name": camp.get("name", config.ELIYAS_CAMPAIGN_ID),
            "status": status_key,
            "status_label": STATUS_LABELS.get(status_key, status_key),
            "spend": round(spend, 2),
            "leads": leads,
            "cost_per_lead": round(cost_per_lead, 2) if cost_per_lead is not None else None,
            "roas": round(roas, 2) if roas is not None else None,
            "impressions": int(row.get("impressions", 0) or 0),
            "clicks": int(row.get("clicks", 0) or 0),
        }

    return data, errors


TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>דשבורד ביצועים - קמפיין</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0e1016;
    --card: #171a23;
    --ink: #e9ebf1;
    --muted: #8c93a4;
    --border: #262b38;
    --brand: #6366f1;
    --brand-2: #22d3ee;
    --green: #34d399;
    --green-soft: #113328;
    --amber: #fbbf24;
    --amber-soft: #3a2a0d;
    --red: #f87171;
    --red-soft: #3a1818;
    --radius: 16px;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px -12px rgba(0,0,0,.55);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: 'Heebo', 'Segoe UI', Arial, sans-serif;
    background:
      radial-gradient(1200px 500px at 90% -10%, rgba(99,102,241,.10) 0%, transparent 60%),
      radial-gradient(900px 400px at -10% 0%, rgba(34,211,238,.08) 0%, transparent 55%),
      var(--bg);
    color: var(--ink);
    padding: 28px clamp(16px, 4vw, 48px) 60px;
  }
  .topbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 22px;
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand .logo {
    width: 44px; height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 800; font-size: 18px;
    box-shadow: var(--shadow);
  }
  .brand h1 { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -.02em; }
  .brand .sub { margin: 2px 0 0; font-size: 13px; color: var(--muted); }
  .live-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--green-soft); color: var(--green);
    font-size: 12px; font-weight: 700; padding: 6px 12px; border-radius: 999px;
    border: 1px solid rgba(22,163,74,.18);
  }
  .live-pill .dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--green);
    box-shadow: 0 0 0 3px rgba(22,163,74,.18);
  }
  .controls { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
  .segmented {
    display: inline-flex; background: var(--card); padding: 4px;
    border-radius: 12px; border: 1px solid var(--border); box-shadow: var(--shadow);
    flex-wrap: wrap; gap: 2px;
  }
  .segmented button {
    border: none; background: transparent; padding: 8px 14px;
    font-family: inherit; font-size: 13px; font-weight: 600; color: var(--muted);
    border-radius: 9px; cursor: pointer; transition: all .15s ease;
    white-space: nowrap;
  }
  .segmented button:hover { color: var(--ink); }
  .segmented button.active { background: linear-gradient(135deg, var(--brand), var(--brand-2)); color: white; }
  .kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
  }
  .kpi {
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 18px 20px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .kpi .value { font-size: 24px; font-weight: 800; letter-spacing: -.02em; }
  .kpi .label { font-size: 12.5px; color: var(--muted); font-weight: 500; }
  .panel {
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 20px; margin-bottom: 20px;
  }
  .panel h2 { margin: 0 0 14px; font-size: 15px; font-weight: 700; }
  .badge { display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }
  .badge.st-ACTIVE { background: var(--green-soft); color: var(--green); }
  .badge.st-PAUSED { background: var(--amber-soft); color: var(--amber); }
  .badge.st-ARCHIVED, .badge.st-DELETED { background: #262b38; color: var(--muted); }
  .badge.st-WITH_ISSUES { background: var(--red-soft); color: var(--red); }
  .campaign-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
  .campaign-title .name { font-size: 17px; font-weight: 700; }
  .error-box, .note-box {
    background: var(--red-soft); color: #fca5a5; border-radius: 12px; padding: 14px 18px;
    margin-bottom: 18px; font-size: 13px; border: 1px solid rgba(248,113,113,.2);
  }
  .error-box ul { margin: 6px 0 0; padding-inline-start: 20px; }
  .note-box { background: var(--amber-soft); color: #fde68a; border: 1px solid rgba(251,191,36,.2); }
  footer { margin-top: 26px; font-size: 12px; color: var(--muted); text-align: center; }
  .empty-state { padding: 40px; text-align: center; color: var(--muted); font-size: 13.5px; }
</style>
</head>
<body>

  <div class="topbar">
    <div class="brand">
      <div class="logo">📊</div>
      <div>
        <h1>דשבורד ביצועים</h1>
        <p class="sub">קמפיין בודד · עודכן __NOW__</p>
      </div>
    </div>
    <span class="live-pill"><span class="dot"></span> מתעדכן אוטומטית כל שעה</span>
  </div>

  <div id="errorBox"></div>
  <div id="noteBox"></div>

  <div class="controls">
    <div class="segmented" id="presetSwitch"></div>
  </div>

  <div class="kpis" id="kpiRow"></div>

  <div class="panel" id="detailsPanel"></div>

  <footer>דשבורד קריאה-בלבד · לא מבצע שינויים בחשבון המודעות</footer>

<script>
const DASHBOARD_DATA = __DATA_JSON__;
const PRESET_LABELS = __PRESETS_JSON__;
const PRESET_ORDER = __PRESET_ORDER_JSON__;
const ERRORS = __ERRORS_JSON__;

const fmtMoney = (v) => "₪" + Number(v || 0).toLocaleString("he-IL", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtInt = (v) => Number(v || 0).toLocaleString("he-IL");
const fmtOptMoney = (v) => v === null || v === undefined ? "—" : fmtMoney(v);
const fmtRoas = (v) => v === null || v === undefined ? "—" : (Number(v).toFixed(2) + "x");

let state = { preset: "last_7d" };
if (!PRESET_ORDER.includes(state.preset)) state.preset = PRESET_ORDER[0];

function buildErrorBox() {
  const box = document.getElementById("errorBox");
  if (!ERRORS.length) { box.innerHTML = ""; return; }
  box.innerHTML = '<div class="error-box"><strong>שימו לב - נכשלה משיכת נתונים:</strong><ul>' +
    ERRORS.map(e => "<li>" + e + "</li>").join("") + "</ul></div>";
}

function buildPresetSwitch() {
  const el = document.getElementById("presetSwitch");
  el.innerHTML = PRESET_ORDER.map(p =>
    `<button data-preset="${p}" class="${p === state.preset ? "active" : ""}">${PRESET_LABELS[p] || p}</button>`
  ).join("");
  el.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => { state.preset = btn.dataset.preset; render(); });
  });
}

function renderKpis(row) {
  const el = document.getElementById("kpiRow");
  if (!row) { el.innerHTML = ""; return; }
  const kpis = [
    { label: "הוצאה", value: fmtMoney(row.spend), color: "var(--brand)" },
    { label: "לידים", value: fmtInt(row.leads), color: "var(--brand-2)" },
    { label: "עלות לליד", value: fmtOptMoney(row.cost_per_lead), color: "var(--green)" },
    { label: "ROAS", value: fmtRoas(row.roas), color: "var(--amber)" },
    { label: "חשיפות", value: fmtInt(row.impressions), color: "#7c3aed" },
    { label: "קליקים", value: fmtInt(row.clicks), color: "#db2777" },
  ];
  el.innerHTML = kpis.map(k =>
    `<div class="kpi"><div class="value" style="color:${k.color}">${k.value}</div><div class="label">${k.label}</div></div>`
  ).join("");
}

function renderDetails(row) {
  const el = document.getElementById("detailsPanel");
  const note = document.getElementById("noteBox");
  if (!row) {
    el.innerHTML = '<div class="empty-state">אין נתונים להצגה בטווח הזה.</div>';
    note.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <div class="campaign-title">
      <span class="name">${row.campaign_name}</span>
      <span class="badge st-${row.status}">${row.status_label}</span>
    </div>
    <p style="color:var(--muted); font-size:13px; margin:0;">נתונים עבור: ${PRESET_LABELS[state.preset] || state.preset}</p>
  `;
  if (!ERRORS.length && row.leads === 0) {
    note.innerHTML = '<div class="note-box">לא נרשמו אירועי המרה (ליד) עבור הקמפיין בטווח הזה - ' +
      'ייתכן שמדובר בבעיית מעקב (פיקסל/אירוע המרה) באתר היעד, ולא בבעיית תקציב או חשיפה.</div>';
  } else {
    note.innerHTML = "";
  }
}

function render() {
  buildPresetSwitch();
  const row = DASHBOARD_DATA[state.preset] || null;
  renderKpis(row);
  renderDetails(row);
}

buildErrorBox();
render();
</script>
</body>
</html>
"""


def render_html(data: dict, errors: list[str]) -> str:
    now_str = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")
    preset_order = [p for p in config.DASHBOARD_DATE_PRESETS if p in data]

    html = TEMPLATE
    html = html.replace("__NOW__", now_str)
    html = html.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__PRESETS_JSON__", json.dumps(PRESET_LABELS, ensure_ascii=False))
    html = html.replace("__PRESET_ORDER_JSON__", json.dumps(preset_order, ensure_ascii=False))
    html = html.replace("__ERRORS_JSON__", json.dumps(errors, ensure_ascii=False))
    return html


def generate_dashboard() -> str:
    """מושך נתונים לקמפיין הבודד לכל טווחי התאריכים, בונה HTML, כותב ל-config.ELIYAS_DASHBOARD_FILE."""
    data, errors = build_dashboard_data()
    html = render_html(data, errors)
    out_path = Path(config.ELIYAS_DASHBOARD_FILE)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path.resolve())


if __name__ == "__main__":
    path = generate_dashboard()
    print(f"eliyas_dashboard נוצר: {path}")
