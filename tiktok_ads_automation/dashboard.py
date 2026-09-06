# -*- coding: utf-8 -*-
"""
performance_dashboard.html - דשבורד קריאה-בלבד שמשווה בין המודעות/סרטונים בקמפיין
לפי חשיפות, קליקים ו-CTR, כדי לזהות אילו "מתבלטות" (להמשיך איתן) ואילו "כושלות"
(לזנוח) - בדיוק המטרה שהוגדרה: להריץ כמה ימים ואז להשוות.

לא מבצע שום פעולה על החשבון - קורא נתונים בלבד ובונה קובץ HTML סטטי שנפתח בדפדפן.
הרצה: python main.py dashboard
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
import insights

STATUS_LABELS = {
    "ENABLE": "פעילה",
    "DISABLE": "מושהית",
    "DELETE": "נמחקה",
}


def _badge(rank: int, total: int) -> tuple[str, str]:
    """מחזיר (טקסט, מחלקת-CSS) לפי דירוג המודעה (0 = הכי טובה)."""
    if total <= 1:
        return "", ""
    if rank == 0:
        return "🏆 מצטיינת", "st-win"
    if rank == total - 1:
        return "⚠️ חלשה ביותר", "st-lose"
    return "", ""


def _display_name(ad_name: str) -> str:
    """מסיר סיומת קובץ וידאו מהשם לתצוגה - מונע ערבוב RTL/LTR מכוער (עברית + '.mov')."""
    for ext in (".mov", ".mp4", ".MOV", ".MP4"):
        if ad_name.endswith(ext):
            return ad_name[: -len(ext)]
    return ad_name


def build_rows(advertiser_id: str) -> list[dict]:
    perf = insights.fetch_traffic_performance(advertiser_id)
    perf.sort(key=lambda r: r["ctr"], reverse=True)

    ad_ids = [r["ad_id"] for r in perf]
    statuses = insights.get_ads_status(advertiser_id, ad_ids)

    max_ctr = max((r["ctr"] for r in perf), default=0) or 1
    rows = []
    for i, r in enumerate(perf):
        badge_text, badge_class = _badge(i, len(perf))
        rows.append({
            **r,
            "ad_name": _display_name(r["ad_name"]),
            "status": STATUS_LABELS.get(statuses.get(r["ad_id"]), statuses.get(r["ad_id"], "-")),
            "bar_pct": round((r["ctr"] / max_ctr) * 100, 1),
            "badge_text": badge_text,
            "badge_class": badge_class,
        })
    return rows


def generate_dashboard() -> str:
    all_rows = []
    for client_name, advertiser_id in config.ADVERTISER_ACCOUNTS.items():
        all_rows.extend(build_rows(advertiser_id))

    total_spend = sum(r["spend"] for r in all_rows)
    total_impressions = sum(r["impressions"] for r in all_rows)
    total_clicks = sum(r["clicks"] for r in all_rows)
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0.0

    now_str = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")

    bars_html = "\n".join(f"""
      <div class="bar-row">
        <div class="bar-label">
          <span class="bar-name">{r['ad_name']}</span>
          {f'<span class="badge {r["badge_class"]}">{r["badge_text"]}</span>' if r['badge_text'] else ''}
        </div>
        <div class="bar-track" title="{r['ad_name']}: {r['clicks']:,.0f} קליקים מתוך {r['impressions']:,.0f} חשיפות (CTR {r['ctr']:.2f}%)">
          <div class="bar-fill" style="width:{max(r['bar_pct'], 3)}%"></div>
          <span class="bar-value">{r['ctr']:.2f}%</span>
        </div>
      </div>""" for r in all_rows)

    table_rows_html = "\n".join(f"""
        <tr>
          <td>{r['ad_name']}</td>
          <td><span class="badge st-{'ENABLE' if r['status'] == 'פעילה' else 'other'}">{r['status']}</span></td>
          <td>₪{r['spend']:.2f}</td>
          <td>{r['impressions']:,.0f}</td>
          <td>{r['clicks']:,.0f}</td>
          <td>{r['ctr']:.2f}%</td>
          <td>₪{r['cpc']:.2f}</td>
        </tr>""" for r in all_rows)

    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ביצועי קמפיין TikTok - קידום אינסטגרם</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0e1016;
    --card: #171a23;
    --ink: #e9ebf1;
    --muted: #8c93a4;
    --border: #262b38;
    --brand: #6366f1;
    --brand-2: #22d3ee;
    --green: #34d399;
    --green-soft: #113328;
    --red: #f87171;
    --red-soft: #3a1818;
    --radius: 16px;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px -12px rgba(0,0,0,.55);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: 'Heebo', 'Segoe UI', Arial, sans-serif;
    background: var(--bg);
    color: var(--ink);
    padding: 28px clamp(16px, 4vw, 48px) 60px;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: var(--muted); font-size: 13px; margin: 0 0 24px; }}
  .kpis {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 26px;
  }}
  .kpi {{
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 16px 18px;
  }}
  .kpi .value {{ font-size: 22px; font-weight: 800; }}
  .kpi .label {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

  .card {{
    background: var(--card); border-radius: var(--radius); border: 1px solid var(--border);
    box-shadow: var(--shadow); padding: 20px 22px; margin-bottom: 22px;
  }}
  .card h2 {{ font-size: 15px; margin: 0 0 16px; }}

  .bar-row {{ margin-bottom: 14px; }}
  .bar-label {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 13px; }}
  .bar-name {{ font-weight: 600; }}
  .bar-track {{ position: relative; height: 22px; background: #1b1f29; border-radius: 6px; overflow: visible; }}
  .bar-fill {{
    height: 100%; min-width: 3%; border-radius: 6px;
    background: linear-gradient(90deg, var(--brand), var(--brand-2));
  }}
  .bar-value {{
    position: absolute; top: 50%; transform: translateY(-50%); left: 8px;
    font-size: 11.5px; font-weight: 700; color: var(--ink); white-space: nowrap;
  }}

  .badge {{ font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; }}
  .badge.st-win {{ background: var(--green-soft); color: var(--green); }}
  .badge.st-lose {{ background: var(--red-soft); color: var(--red); }}
  .badge.st-ENABLE {{ background: var(--green-soft); color: var(--green); }}
  .badge.st-other {{ background: #262b38; color: var(--muted); }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{
    text-align: right; padding: 10px 8px; background: #1b1f29; color: var(--muted);
    font-weight: 600; font-size: 12px; border-bottom: 1px solid var(--border);
  }}
  tbody td {{ padding: 10px 8px; border-bottom: 1px solid var(--border); }}
  tbody tr:hover {{ background: rgba(255,255,255,.03); }}

  .empty {{ color: var(--muted); text-align: center; padding: 30px; }}
  footer {{ margin-top: 20px; font-size: 12px; color: var(--muted); text-align: center; }}
</style>
</head>
<body>

<h1>ביצועי קמפיין TikTok - קידום אינסטגרם</h1>
<p class="sub">עודכן לאחרונה: {now_str} · חלון נתונים: {config.REPORT_LOOKBACK_DAYS} ימים אחרונים · יעד: {config.DESTINATION_URL}</p>

<div class="kpis">
  <div class="kpi"><div class="value">₪{total_spend:.2f}</div><div class="label">הוצאה כוללת</div></div>
  <div class="kpi"><div class="value">{total_impressions:,.0f}</div><div class="label">חשיפות</div></div>
  <div class="kpi"><div class="value">{total_clicks:,.0f}</div><div class="label">קליקים</div></div>
  <div class="kpi"><div class="value">{overall_ctr:.2f}%</div><div class="label">CTR ממוצע</div></div>
</div>

<div class="card">
  <h2>דירוג לפי CTR (הקלקות מתוך חשיפות) - מהמצטיינת לחלשה</h2>
  {bars_html if all_rows else '<div class="empty">אין עדיין נתונים - הריצו את הקמפיין כמה ימים ואז רעננו את הדשבורד.</div>'}
</div>

<div class="card">
  <h2>טבלה מלאה</h2>
  <table>
    <thead>
      <tr><th>סרטון / מודעה</th><th>סטטוס</th><th>הוצאה</th><th>חשיפות</th><th>קליקים</th><th>CTR</th><th>עלות לקליק</th></tr>
    </thead>
    <tbody>
      {table_rows_html if all_rows else '<tr><td colspan="7" class="empty">אין נתונים</td></tr>'}
    </tbody>
  </table>
</div>

<footer>נוצר אוטומטית ע"י tiktok_ads_automation/dashboard.py - קריאה-בלבד, לא נוגע בשום מודעה.</footer>

</body>
</html>"""

    Path(config.PERFORMANCE_DASHBOARD_FILE).write_text(html, encoding="utf-8")
    return config.PERFORMANCE_DASHBOARD_FILE
