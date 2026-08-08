"""
god_manager - דשבורד קריאה-בלבד שמציג את נתוני הקמפיינים של כל חשבונות המודעות
המנוהלים (רחל, טל, גל, והחשבון האישי) במקום אחד.

לא מבצע שום פעולה על החשבונות (לא משהה, לא מחליף קריאטיב) - קורא נתונים בלבד
ובונה קובץ HTML סטטי שנפתח בדפדפן.

מופעל אוטומטית בסוף כל הרצה של main.py, כך שהוא מתעדכן מדי יום ביחד עם
בדיקת ה-ROAS/רוטציית הקריאטיב.
"""

from datetime import datetime, timezone
from pathlib import Path

import requests

import config
import insights as insights_mod


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


def fetch_campaign_insights(ad_account_id: str) -> list[dict]:
    """מושך insights ברמת קמפיין (הוצאה, לידים, ROAS) לחלון הזמן המוגדר ב-config.DATE_PRESET."""
    url = f"{config.GRAPH_URL}/act_{ad_account_id}/insights"
    params = {
        "level": "campaign",
        "date_preset": config.DATE_PRESET,
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


STATUS_LABELS = {
    "ACTIVE": ("פעיל", "status-active"),
    "PAUSED": ("מושהה", "status-paused"),
    "ARCHIVED": ("בארכיון", "status-archived"),
    "DELETED": ("נמחק", "status-archived"),
    "IN_PROCESS": ("בתהליך", "status-paused"),
    "WITH_ISSUES": ("עם בעיה", "status-issue"),
}


def build_dashboard_rows() -> tuple[list[dict], list[str]]:
    """
    בונה את כל שורות הדשבורד עבור כל החשבונות ב-config.DASHBOARD_ACCOUNTS.
    מחזיר (rows, errors) - כדי שתקלה בחשבון אחד לא תפיל את כל הדשבורד.
    """
    all_rows = []
    errors = []

    for client_name, ad_account_id in config.DASHBOARD_ACCOUNTS.items():
        try:
            campaigns = fetch_campaigns(ad_account_id)
            insight_rows = fetch_campaign_insights(ad_account_id)
        except Exception as e:
            errors.append(f"{client_name}: {e}")
            continue

        insights_by_campaign = {row["campaign_id"]: row for row in insight_rows if row.get("campaign_id")}

        # לוקחים את כל הקמפיינים (גם כאלה בלי insights בטווח הנוכחי, למשל אם לא רצו)
        for cid, camp in campaigns.items():
            row = insights_by_campaign.get(cid, {})
            spend = float(row.get("spend", 0) or 0)
            leads = insights_mod.extract_leads(row)
            roas = insights_mod.extract_roas(row)
            cost_per_lead = (spend / leads) if leads > 0 else None
            status_key = camp.get("effective_status", camp.get("status", "UNKNOWN"))
            status_label, status_class = STATUS_LABELS.get(status_key, (status_key, "status-archived"))

            all_rows.append({
                "client": client_name,
                "campaign_name": camp.get("name", cid),
                "status_label": status_label,
                "status_class": status_class,
                "spend": spend,
                "leads": leads,
                "cost_per_lead": cost_per_lead,
                "roas": roas,
                "impressions": int(row.get("impressions", 0) or 0),
                "clicks": int(row.get("clicks", 0) or 0),
            })

    # מיון: לקוח, ואז לפי הוצאה יורד
    all_rows.sort(key=lambda r: (r["client"], -r["spend"]))
    return all_rows, errors


def _fmt_money(v: float) -> str:
    return f"₪{v:,.2f}"


def _fmt_optional_money(v):
    return _fmt_money(v) if v is not None else "—"


def _fmt_roas(v):
    return f"{v:.2f}x" if v is not None else "—"


def render_html(rows: list[dict], errors: list[str]) -> str:
    now_str = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")

    clients = sorted({r["client"] for r in rows})
    total_spend = sum(r["spend"] for r in rows)
    total_leads = sum(r["leads"] for r in rows)
    active_count = sum(1 for r in rows if r["status_class"] == "status-active")

    # כרטיסי סיכום לפי לקוח
    client_cards = []
    for c in clients:
        crows = [r for r in rows if r["client"] == c]
        c_spend = sum(r["spend"] for r in crows)
        c_leads = sum(r["leads"] for r in crows)
        c_active = sum(1 for r in crows if r["status_class"] == "status-active")
        c_cpl = (c_spend / c_leads) if c_leads > 0 else None
        client_cards.append(f"""
        <div class="client-card">
          <div class="client-card-name">{c}</div>
          <div class="client-card-metrics">
            <div><span class="metric-value">{_fmt_money(c_spend)}</span><span class="metric-label">הוצאה (7 ימים)</span></div>
            <div><span class="metric-value">{c_leads}</span><span class="metric-label">לידים</span></div>
            <div><span class="metric-value">{_fmt_optional_money(c_cpl)}</span><span class="metric-label">עלות לליד</span></div>
            <div><span class="metric-value">{c_active}</span><span class="metric-label">קמפיינים פעילים</span></div>
          </div>
        </div>""")

    # שורות הטבלה
    table_rows = []
    for r in rows:
        table_rows.append(f"""
        <tr data-client="{r['client']}">
          <td>{r['client']}</td>
          <td>{r['campaign_name']}</td>
          <td><span class="badge {r['status_class']}">{r['status_label']}</span></td>
          <td>{_fmt_money(r['spend'])}</td>
          <td>{r['leads']}</td>
          <td>{_fmt_optional_money(r['cost_per_lead'])}</td>
          <td>{_fmt_roas(r['roas'])}</td>
          <td>{r['impressions']:,}</td>
          <td>{r['clicks']:,}</td>
        </tr>""")

    error_block = ""
    if errors:
        items = "".join(f"<li>{e}</li>" for e in errors)
        error_block = f"""
        <div class="error-box">
          <strong>שימו לב - נכשלה משיכת נתונים עבור:</strong>
          <ul>{items}</ul>
        </div>"""

    filter_buttons = "".join(
        f'<button class="filter-btn" data-filter="{c}">{c}</button>' for c in clients
    )

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>god_manager - דשבורד קמפיינים</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f4f5f7;
    color: #1c1e21;
    margin: 0;
    padding: 24px;
  }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .subtitle {{ color: #65676b; font-size: 13px; margin-bottom: 20px; }}
  .summary-bar {{
    display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
  }}
  .summary-item {{
    background: #fff; border-radius: 10px; padding: 14px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 140px;
  }}
  .summary-item .value {{ font-size: 22px; font-weight: 700; }}
  .summary-item .label {{ font-size: 12px; color: #65676b; }}
  .client-cards {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px; margin-bottom: 24px;
  }}
  .client-card {{
    background: #fff; border-radius: 10px; padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  .client-card-name {{ font-weight: 700; font-size: 15px; margin-bottom: 10px; }}
  .client-card-metrics {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  }}
  .client-card-metrics .metric-value {{ display: block; font-size: 16px; font-weight: 700; }}
  .client-card-metrics .metric-label {{ display: block; font-size: 11px; color: #65676b; }}
  .filters {{ margin-bottom: 12px; }}
  .filter-btn {{
    background: #fff; border: 1px solid #dadde1; border-radius: 16px;
    padding: 6px 14px; margin-inline-end: 6px; font-size: 13px; cursor: pointer;
  }}
  .filter-btn.active {{ background: #1877f2; color: #fff; border-color: #1877f2; }}
  table {{
    width: 100%; border-collapse: collapse; background: #fff;
    border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  th, td {{ padding: 10px 12px; text-align: right; font-size: 13px; }}
  th {{
    background: #f0f2f5; font-weight: 600; color: #444; position: sticky; top: 0;
  }}
  tr:not(:last-child) td {{ border-bottom: 1px solid #eee; }}
  .badge {{
    padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;
  }}
  .status-active {{ background: #e3f5e6; color: #2a8a3e; }}
  .status-paused {{ background: #fdf0d5; color: #9a6a00; }}
  .status-archived {{ background: #eee; color: #777; }}
  .status-issue {{ background: #fde2e1; color: #c0392b; }}
  .error-box {{
    background: #fde2e1; color: #7a2019; border-radius: 8px; padding: 12px 16px;
    margin-bottom: 16px; font-size: 13px;
  }}
  .error-box ul {{ margin: 6px 0 0; padding-inline-start: 20px; }}
  footer {{ margin-top: 20px; font-size: 12px; color: #999; text-align: center; }}
</style>
</head>
<body>
  <h1>🎯 god_manager</h1>
  <div class="subtitle">דשבורד קמפיינים - כל החשבונות המנוהלים · עודכן לאחרונה: {now_str} · טווח נתונים: 7 ימים אחרונים</div>

  {error_block}

  <div class="summary-bar">
    <div class="summary-item"><div class="value">{_fmt_money(total_spend)}</div><div class="label">סה"כ הוצאה</div></div>
    <div class="summary-item"><div class="value">{total_leads}</div><div class="label">סה"כ לידים</div></div>
    <div class="summary-item"><div class="value">{active_count}</div><div class="label">קמפיינים פעילים</div></div>
    <div class="summary-item"><div class="value">{len(clients)}</div><div class="label">חשבונות מנוהלים</div></div>
  </div>

  <div class="client-cards">
    {"".join(client_cards)}
  </div>

  <div class="filters">
    <button class="filter-btn active" data-filter="all">הכל</button>
    {filter_buttons}
  </div>

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
    <tbody>
      {"".join(table_rows)}
    </tbody>
  </table>

  <footer>נוצר אוטומטית ע"י meta_ads_automation · קריאה-בלבד, לא מבצע שינויים בחשבונות</footer>

  <script>
    const buttons = document.querySelectorAll('.filter-btn');
    const rows = document.querySelectorAll('#campaignsTable tbody tr');
    buttons.forEach(btn => {{
      btn.addEventListener('click', () => {{
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        rows.forEach(row => {{
          row.style.display = (filter === 'all' || row.dataset.client === filter) ? '' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def generate_dashboard() -> str:
    """מושך נתונים מכל החשבונות, בונה HTML, כותב ל-config.DASHBOARD_FILE. מחזיר את הנתיב שנכתב."""
    rows, errors = build_dashboard_rows()
    html = render_html(rows, errors)
    out_path = Path(config.DASHBOARD_FILE)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path.resolve())


if __name__ == "__main__":
    path = generate_dashboard()
    print(f"god_manager נוצר: {path}")
