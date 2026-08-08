"""
god_manager - דשבורד קריאה-בלבד שמציג את נתוני הקמפיינים של כל חשבונות המודעות
המנוהלים (רחל, טל, גל, ויהב) במקום אחד.

לא מבצע שום פעולה על החשבונות (לא משהה, לא מחליף קריאטיב) - קורא נתונים בלבד
ובונה קובץ HTML סטטי שנפתח בדפדפן.

מושך כמה טווחי תאריכים מראש (config.DASHBOARD_DATE_PRESETS) ומטמיע את כולם
בתוך הדף כ-JSON, כדי שהמעבר בין טווחים בדפדפן יהיה מיידי - בלי לחשוף את טוקן
ה-API בצד הלקוח (הדף פתוח לציבור).

מופעל אוטומטית בסוף כל הרצה של main.py, וגם דרך GitHub Actions כל שעה.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

import config
import insights as insights_mod


PRESET_LABELS = {
    "today": "היום",
    "yesterday": "אתמול",
    "last_7d": "7 ימים אחרונים",
    "last_14d": "14 ימים אחרונים",
    "last_30d": "30 ימים אחרונים",
    "last_90d": "90 ימים אחרונים",
}

STATUS_LABELS = {
    "ACTIVE": "פעיל",
    "PAUSED": "מושהה",
    "ARCHIVED": "בארכיון",
    "DELETED": "נמחק",
    "IN_PROCESS": "בתהליך",
    "WITH_ISSUES": "עם בעיה",
}


def fetch_campaigns(ad_account_id: str) -> dict:
    """מחזיר dict של campaign_id -> {name, status, effective_status, objective}."""
    url = f"{config.GRAPH_URL}/act_{ad_account_id}/campaigns"
    params = {
        "fields": "id,name,status,effective_status,objective",
        "access_token": config.ACCESS_TOKEN,
        "limit": 200,
    }

    campaigns = {}
    while url:
        resp = requests.get(url, params=params, timeout=30)
        params = None
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Meta API error (campaigns) for act_{ad_account_id}: {data['error']}")
        for c in data.get("data", []):
            campaigns[c["id"]] = c
        url = data.get("paging", {}).get("next")

    return campaigns


def fetch_campaign_insights(ad_account_id: str, date_preset: str) -> list[dict]:
    """מושך insights ברמת קמפיין (הוצאה, לידים, ROAS) לטווח תאריכים נתון."""
    url = f"{config.GRAPH_URL}/act_{ad_account_id}/insights"
    params = {
        "level": "campaign",
        "date_preset": date_preset,
        "fields": "campaign_id,campaign_name,spend,purchase_roas,actions,impressions,clicks",
        "access_token": config.ACCESS_TOKEN,
        "limit": 200,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        params = None
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Meta API error (insights) for act_{ad_account_id}: {data['error']}")
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")

    return rows


def _campaign_allowed(client_name: str, campaign_name: str) -> bool:
    allowlist = config.DASHBOARD_CAMPAIGN_ALLOWLIST.get(client_name)
    if not allowlist:
        return True
    return campaign_name in allowlist


def build_dashboard_data() -> tuple[dict, list[str]]:
    """
    בונה עבור כל טווח תאריכים ב-config.DASHBOARD_DATE_PRESETS את כל שורות הדשבורד,
    עבור כל החשבונות ב-config.DASHBOARD_ACCOUNTS.
    מחזיר (data, errors) כאשר data = {preset: [row, ...]}.
    שגיאות משיכה (per account) לא מפילות את כל הדשבורד - פשוט מדלגים על החשבון.
    """
    errors: list[str] = []

    # שולפים רשימת קמפיינים פעם אחת לכל חשבון (לא תלוי בטווח תאריכים)
    campaigns_by_client: dict[str, dict] = {}
    for client_name, ad_account_id in config.DASHBOARD_ACCOUNTS.items():
        try:
            campaigns_by_client[client_name] = fetch_campaigns(ad_account_id)
        except Exception as e:
            errors.append(f"{client_name}: {e}")
            campaigns_by_client[client_name] = {}

    data: dict[str, list[dict]] = {}

    for preset in config.DASHBOARD_DATE_PRESETS:
        preset_rows: list[dict] = []

        for client_name, ad_account_id in config.DASHBOARD_ACCOUNTS.items():
            campaigns = campaigns_by_client.get(client_name, {})
            if not campaigns:
                continue

            try:
                insight_rows = fetch_campaign_insights(ad_account_id, preset)
            except Exception as e:
                msg = f"{client_name} ({PRESET_LABELS.get(preset, preset)}): {e}"
                if msg not in errors:
                    errors.append(msg)
                continue

            insights_by_campaign = {row["campaign_id"]: row for row in insight_rows if row.get("campaign_id")}

            for cid, camp in campaigns.items():
                camp_name = camp.get("name", cid)
                if not _campaign_allowed(client_name, camp_name):
                    continue

                row = insights_by_campaign.get(cid, {})
                spend = float(row.get("spend", 0) or 0)
                leads = insights_mod.extract_leads(row)
                roas = insights_mod.extract_roas(row)
                cost_per_lead = (spend / leads) if leads > 0 else None
                status_key = camp.get("effective_status", camp.get("status", "UNKNOWN"))
                status_label = STATUS_LABELS.get(status_key, status_key)

                preset_rows.append({
                    "client": client_name,
                    "campaign_name": camp_name,
                    "status": status_key,
                    "status_label": status_label,
                    "spend": round(spend, 2),
                    "leads": leads,
                    "cost_per_lead": round(cost_per_lead, 2) if cost_per_lead is not None else None,
                    "roas": round(roas, 2) if roas is not None else None,
                    "impressions": int(row.get("impressions", 0) or 0),
                    "clicks": int(row.get("clicks", 0) or 0),
                })

        preset_rows.sort(key=lambda r: (r["client"], -r["spend"]))
        data[preset] = preset_rows

    return data, errors


TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>god_manager - דשבורד קמפיינים</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #f2f4f8;
    --card: #ffffff;
    --ink: #1b1f2a;
    --muted: #6b7280;
    --border: #e7e9ef;
    --brand: #4f46e5;
    --brand-2: #06b6d4;
    --brand-soft: #eef0fe;
    --green: #16a34a;
    --green-soft: #e8f7ec;
    --amber: #b45309;
    --amber-soft: #fdf1de;
    --red: #dc2626;
    --red-soft: #fdeaea;
    --radius: 16px;
    --shadow: 0 1px 2px rgba(16,24,40,.04), 0 8px 24px -12px rgba(16,24,40,.10);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: 'Heebo', 'Segoe UI', Arial, sans-serif;
    background:
      radial-gradient(1200px 500px at 90% -10%, #eef2ff 0%, transparent 60%),
      radial-gradient(900px 400px at -10% 0%, #ecfeff 0%, transparent 55%),
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
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
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

  .controls {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px;
    margin-bottom: 20px;
  }
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
  .segmented button.active {
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
    color: white;
  }

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
  .kpi .icon {
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 4px;
  }
  .kpi .value { font-size: 24px; font-weight: 800; letter-spacing: -.02em; }
  .kpi .label { font-size: 12.5px; color: var(--muted); font-weight: 500; }

  .grid-2 {
    display: grid;
    grid-template-columns: 1.1fr .9fr;
    gap: 16px;
    margin-bottom: 20px;
  }
  @media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

  .panel {
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 20px;
  }
  .panel h2 {
    margin: 0 0 14px; font-size: 15px; font-weight: 700;
  }
  .chart-wrap { position: relative; height: 240px; }

  .client-cards {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }
  .client-card {
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 16px 18px; cursor: pointer;
    transition: transform .12s ease, box-shadow .12s ease;
    border-top: 3px solid var(--brand);
  }
  .client-card:hover { transform: translateY(-2px); }
  .client-card.selected { outline: 2px solid var(--brand); }
  .client-card .name { font-weight: 700; font-size: 14.5px; margin-bottom: 10px; }
  .client-card .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .client-card .metrics b { display: block; font-size: 16px; font-weight: 800; }
  .client-card .metrics span { display: block; font-size: 11px; color: var(--muted); margin-top: 2px; }

  table { width: 100%; border-collapse: collapse; }
  .table-panel { padding: 0; overflow: hidden; }
  .table-panel h2 { padding: 18px 20px 0; }
  .table-scroll { overflow-x: auto; }
  th, td { padding: 12px 16px; text-align: right; font-size: 13px; white-space: nowrap; }
  thead th {
    background: #fafbfd; color: var(--muted); font-weight: 600; font-size: 12px;
    position: sticky; top: 0; border-bottom: 1px solid var(--border);
  }
  tbody tr { border-bottom: 1px solid var(--border); transition: background .1s ease; }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #fafbff; }
  .badge {
    display: inline-block; padding: 4px 11px; border-radius: 999px;
    font-size: 11.5px; font-weight: 700;
  }
  .badge.st-ACTIVE { background: var(--green-soft); color: var(--green); }
  .badge.st-PAUSED { background: var(--amber-soft); color: var(--amber); }
  .badge.st-ARCHIVED, .badge.st-DELETED { background: #eef0f3; color: #6b7280; }
  .badge.st-WITH_ISSUES { background: var(--red-soft); color: var(--red); }
  .badge.st-IN_PROCESS { background: var(--brand-soft); color: var(--brand); }
  .cell-strong { font-weight: 700; }
  .empty-state { padding: 40px; text-align: center; color: var(--muted); font-size: 13.5px; }

  .error-box {
    background: var(--red-soft); color: #8a2c22; border-radius: 12px; padding: 14px 18px;
    margin-bottom: 18px; font-size: 13px; border: 1px solid rgba(220,38,38,.15);
  }
  .error-box ul { margin: 6px 0 0; padding-inline-start: 20px; }

  footer {
    margin-top: 26px; font-size: 12px; color: var(--muted); text-align: center;
  }
</style>
</head>
<body>

  <div class="topbar">
    <div class="brand">
      <div class="logo">GM</div>
      <div>
        <h1>god_manager</h1>
        <p class="sub">דשבורד קמפיינים מאוחד · כל החשבונות המנוהלים · עודכן __NOW__</p>
      </div>
    </div>
    <span class="live-pill"><span class="dot"></span> מתעדכן אוטומטית כל שעה</span>
  </div>

  <div id="errorBox"></div>

  <div class="controls">
    <div class="segmented" id="presetSwitch"></div>
    <div class="segmented" id="clientSwitch"></div>
  </div>

  <div class="kpis" id="kpiRow"></div>

  <div class="grid-2">
    <div class="panel">
      <h2>הוצאה לפי לקוח</h2>
      <div class="chart-wrap"><canvas id="spendChart"></canvas></div>
    </div>
    <div class="panel">
      <h2>לידים לפי לקוח</h2>
      <div class="chart-wrap"><canvas id="leadsChart"></canvas></div>
    </div>
  </div>

  <div class="client-cards" id="clientCards"></div>

  <div class="panel table-panel">
    <h2>קמפיינים</h2>
    <div class="table-scroll">
      <table id="campaignsTable">
        <thead>
          <tr>
            <th>לקוח</th>
            <th>קמפיין</th>
            <th>סטטוס</th>
            <th>הוצאה</th>
            <th>לידים</th>
            <th>עלות לליד</th>
            <th>ROAS</th>
            <th>חשיפות</th>
            <th>קליקים</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
      <div class="empty-state" id="emptyState" style="display:none;">אין קמפיינים להצגה בטווח/סינון הזה.</div>
    </div>
  </div>

  <footer>נוצר אוטומטית ע"י meta_ads_automation · קריאה-בלבד, לא מבצע שינויים בחשבונות</footer>

<script>
const DASHBOARD_DATA = __DATA_JSON__;
const PRESET_LABELS = __PRESETS_JSON__;
const PRESET_ORDER = __PRESET_ORDER_JSON__;
const CLIENTS = __CLIENTS_JSON__;
const ERRORS = __ERRORS_JSON__;

const CLIENT_COLORS = ["#4f46e5", "#06b6d4", "#f97316", "#16a34a", "#db2777", "#7c3aed"];
function clientColor(name) {
  const idx = CLIENTS.indexOf(name);
  return CLIENT_COLORS[idx % CLIENT_COLORS.length] || "#4f46e5";
}

const fmtMoney = (v) => "₪" + Number(v || 0).toLocaleString("he-IL", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtInt = (v) => Number(v || 0).toLocaleString("he-IL");
const fmtOptMoney = (v) => v === null || v === undefined ? "—" : fmtMoney(v);
const fmtRoas = (v) => v === null || v === undefined ? "—" : (Number(v).toFixed(2) + "x");

let state = { preset: "last_7d", client: "all" };
if (!PRESET_ORDER.includes(state.preset)) state.preset = PRESET_ORDER[0];

let spendChart, leadsChart;

function buildErrorBox() {
  const box = document.getElementById("errorBox");
  if (!ERRORS.length) { box.innerHTML = ""; return; }
  box.innerHTML = '<div class="error-box"><strong>שימו לב - נכשלה משיכת נתונים עבור:</strong><ul>' +
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

function buildClientSwitch() {
  const el = document.getElementById("clientSwitch");
  const buttons = ['<button data-client="all" class="' + (state.client === "all" ? "active" : "") + '">הכל</button>']
    .concat(CLIENTS.map(c => `<button data-client="${c}" class="${state.client === c ? "active" : ""}">${c}</button>`));
  el.innerHTML = buttons.join("");
  el.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => { state.client = btn.dataset.client; render(); });
  });
}

function currentRows() {
  const rows = DASHBOARD_DATA[state.preset] || [];
  if (state.client === "all") return rows;
  return rows.filter(r => r.client === state.client);
}

function renderKpis(rows) {
  const totalSpend = rows.reduce((s, r) => s + r.spend, 0);
  const totalLeads = rows.reduce((s, r) => s + r.leads, 0);
  const activeCount = rows.filter(r => r.status === "ACTIVE").length;
  const avgCpl = totalLeads > 0 ? totalSpend / totalLeads : null;
  const clientsCount = state.client === "all" ? CLIENTS.length : 1;

  const kpis = [
    { label: "הוצאה כוללת", value: fmtMoney(totalSpend), color: "var(--brand)" },
    { label: "לידים כוללים", value: fmtInt(totalLeads), color: "var(--brand-2)" },
    { label: "עלות ממוצעת לליד", value: fmtOptMoney(avgCpl), color: "var(--green)" },
    { label: "קמפיינים פעילים", value: fmtInt(activeCount), color: "var(--amber)" },
    { label: "חשבונות מוצגים", value: fmtInt(clientsCount), color: "#7c3aed" },
  ];
  document.getElementById("kpiRow").innerHTML = kpis.map(k =>
    `<div class="kpi"><div class="value" style="color:${k.color}">${k.value}</div><div class="label">${k.label}</div></div>`
  ).join("");
}

function renderClientCards(rows) {
  const el = document.getElementById("clientCards");
  el.innerHTML = CLIENTS.map(c => {
    const crows = rows.filter(r => r.client === c);
    const spend = crows.reduce((s, r) => s + r.spend, 0);
    const leads = crows.reduce((s, r) => s + r.leads, 0);
    const active = crows.filter(r => r.status === "ACTIVE").length;
    const cpl = leads > 0 ? spend / leads : null;
    const selected = state.client === c ? "selected" : "";
    return `<div class="client-card ${selected}" style="border-top-color:${clientColor(c)}" data-client="${c}">
      <div class="name">${c}</div>
      <div class="metrics">
        <div><b>${fmtMoney(spend)}</b><span>הוצאה</span></div>
        <div><b>${fmtInt(leads)}</b><span>לידים</span></div>
        <div><b>${fmtOptMoney(cpl)}</b><span>עלות לליד</span></div>
        <div><b>${fmtInt(active)}</b><span>פעילים</span></div>
      </div>
    </div>`;
  }).join("");
  el.querySelectorAll(".client-card").forEach(card => {
    card.addEventListener("click", () => {
      const c = card.dataset.client;
      state.client = (state.client === c) ? "all" : c;
      render();
    });
  });
}

function renderTable(rows) {
  const body = document.getElementById("tableBody");
  const empty = document.getElementById("emptyState");
  if (!rows.length) {
    body.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  body.innerHTML = rows.map(r => `
    <tr>
      <td class="cell-strong">${r.client}</td>
      <td>${r.campaign_name}</td>
      <td><span class="badge st-${r.status}">${r.status_label}</span></td>
      <td class="cell-strong">${fmtMoney(r.spend)}</td>
      <td>${fmtInt(r.leads)}</td>
      <td>${fmtOptMoney(r.cost_per_lead)}</td>
      <td>${fmtRoas(r.roas)}</td>
      <td>${fmtInt(r.impressions)}</td>
      <td>${fmtInt(r.clicks)}</td>
    </tr>
  `).join("");
}

function aggByClient(rows, key) {
  const map = {};
  CLIENTS.forEach(c => map[c] = 0);
  rows.forEach(r => { map[r.client] = (map[r.client] || 0) + r[key]; });
  return CLIENTS.map(c => map[c] || 0);
}

function renderCharts(rowsForChart) {
  const labels = CLIENTS;
  const spendData = aggByClient(rowsForChart, "spend");
  const leadsData = aggByClient(rowsForChart, "leads");
  const colors = CLIENTS.map(clientColor);

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: "Heebo" } } },
      y: { grid: { color: "#eef0f3" }, ticks: { font: { family: "Heebo" } } },
    },
  };

  if (spendChart) spendChart.destroy();
  spendChart = new Chart(document.getElementById("spendChart"), {
    type: "bar",
    data: { labels, datasets: [{ data: spendData, backgroundColor: colors, borderRadius: 8, maxBarThickness: 46 }] },
    options: commonOptions,
  });

  if (leadsChart) leadsChart.destroy();
  leadsChart = new Chart(document.getElementById("leadsChart"), {
    type: "bar",
    data: { labels, datasets: [{ data: leadsData, backgroundColor: colors, borderRadius: 8, maxBarThickness: 46 }] },
    options: commonOptions,
  });
}

function render() {
  buildPresetSwitch();
  buildClientSwitch();
  const rows = currentRows();
  renderKpis(rows);
  // charts always reflect all clients (comparison view), regardless of table filter
  renderCharts(DASHBOARD_DATA[state.preset] || []);
  renderClientCards(DASHBOARD_DATA[state.preset] || []);
  renderTable(rows);
}

buildErrorBox();
render();
</script>
</body>
</html>
"""


def render_html(data: dict, errors: list[str]) -> str:
    now_str = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    clients = list(config.DASHBOARD_ACCOUNTS.keys())
    preset_order = [p for p in config.DASHBOARD_DATE_PRESETS if p in data]

    html = TEMPLATE
    html = html.replace("__NOW__", now_str)
    html = html.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__PRESETS_JSON__", json.dumps(PRESET_LABELS, ensure_ascii=False))
    html = html.replace("__PRESET_ORDER_JSON__", json.dumps(preset_order, ensure_ascii=False))
    html = html.replace("__CLIENTS_JSON__", json.dumps(clients, ensure_ascii=False))
    html = html.replace("__ERRORS_JSON__", json.dumps(errors, ensure_ascii=False))
    return html


def generate_dashboard() -> str:
    """מושך נתונים מכל החשבונות לכל טווחי התאריכים, בונה HTML, כותב ל-config.DASHBOARD_FILE."""
    data, errors = build_dashboard_data()
    html = render_html(data, errors)
    out_path = Path(config.DASHBOARD_FILE)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path.resolve())


if __name__ == "__main__":
    path = generate_dashboard()
    print(f"god_manager נוצר: {path}")
