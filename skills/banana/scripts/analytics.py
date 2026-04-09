#!/usr/bin/env python3
"""Banana Claude -- Analytics Dashboard

Generate a self-contained HTML analytics dashboard showing cost trends,
domain usage, model breakdown, and quota monitoring.

Usage:
    analytics.py report --format html [--output PATH] [--days 30]
    analytics.py report --format json [--output PATH] [--days 30]
    analytics.py data [--days 30]
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEDGER_PATH = Path.home() / ".banana" / "costs.json"
HISTORY_DIR = Path.home() / ".banana" / "history"
AB_PREFS_PATH = Path.home() / ".banana" / "ab_preferences.json"
DEFAULT_OUTPUT = Path.home() / ".banana" / "analytics.html"
DAILY_QUOTA_LIMIT = 500
VERSION = "2.6.0"

COLORS = {
    "bg": "#1a1a2e", "card": "#16213e", "primary": "#FFC000",
    "secondary": "#e94560", "text": "#eee", "muted": "#8892b0",
}
CHART_PALETTE = ["#FFC000", "#e94560", "#0f3460", "#53d8fb", "#a29bfe",
                 "#fd79a8", "#00b894", "#fdcb6e"]


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_cost_data():
    """Read costs.json ledger."""
    if not LEDGER_PATH.exists():
        return {"total_cost": 0.0, "total_images": 0, "entries": [], "daily": {}}
    with open(LEDGER_PATH, "r") as f:
        return json.load(f)


def _load_history_data():
    """Read all session history JSON files."""
    sessions = []
    if not HISTORY_DIR.exists():
        return sessions
    for p in sorted(HISTORY_DIR.glob("*.json")):
        try:
            with open(p, "r") as f:
                sessions.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def _load_ab_prefs():
    """Read ab_preferences.json if it exists."""
    if not AB_PREFS_PATH.exists():
        return None
    try:
        with open(AB_PREFS_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_data(days=30):
    """Combine all data sources into a single analytics dict."""
    ledger = _load_cost_data()
    sessions = _load_history_data()
    ab_prefs = _load_ab_prefs()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    today_str = now.strftime("%Y-%m-%d")

    # --- daily from ledger ---
    daily_map = {}
    for date_str, info in ledger.get("daily", {}).items():
        if date_str >= cutoff_str:
            daily_map[date_str] = {"date": date_str, "count": info["count"],
                                   "cost": round(info["cost"], 4)}

    # --- breakdowns from history entries ---
    by_model = {}
    by_resolution = {}
    by_domain = {}
    by_preset = {}
    session_count = 0

    for sess in sessions:
        sess_dominated = False
        for entry in sess.get("entries", []):
            ts = entry.get("timestamp", "")[:10]
            if ts < cutoff_str:
                continue
            if not sess_dominated:
                sess_dominated = True
                session_count += 1

            model = entry.get("model", "unknown")
            res = entry.get("resolution", "unknown")
            domain = entry.get("domain_mode", "") or "Unspecified"
            preset = entry.get("preset", "") or "none"
            cost = entry.get("cost", 0.0)

            by_model.setdefault(model, {"count": 0, "cost": 0.0})
            by_model[model]["count"] += 1
            by_model[model]["cost"] = round(by_model[model]["cost"] + cost, 4)

            by_resolution.setdefault(res, {"count": 0, "cost": 0.0})
            by_resolution[res]["count"] += 1
            by_resolution[res]["cost"] = round(by_resolution[res]["cost"] + cost, 4)

            by_domain[domain] = by_domain.get(domain, 0) + 1

            if preset != "none":
                by_preset[preset] = by_preset.get(preset, 0) + 1

    # fill missing dates with zeros
    daily_list = []
    d = cutoff
    while d.strftime("%Y-%m-%d") <= today_str:
        ds = d.strftime("%Y-%m-%d")
        if ds in daily_map:
            daily_list.append(daily_map[ds])
        else:
            daily_list.append({"date": ds, "count": 0, "cost": 0.0})
        d += timedelta(days=1)

    total_images = ledger.get("total_images", 0)
    total_cost = ledger.get("total_cost", 0.0)
    today_daily = ledger.get("daily", {}).get(today_str, {"count": 0, "cost": 0.0})

    return {
        "period": {"start": cutoff_str, "end": today_str, "days": days},
        "totals": {"images": total_images, "cost": round(total_cost, 4),
                   "sessions": session_count},
        "daily": daily_list,
        "by_model": by_model,
        "by_resolution": by_resolution,
        "by_domain": by_domain,
        "by_preset": by_preset,
        "quota": {"daily_limit": DAILY_QUOTA_LIMIT,
                  "today_used": today_daily["count"],
                  "today_remaining": max(0, DAILY_QUOTA_LIMIT - today_daily["count"])},
        "avg_cost_per_image": round(total_cost / max(total_images, 1), 4),
        "ab_preferences": ab_prefs,
    }


# ---------------------------------------------------------------------------
# SVG chart helpers
# ---------------------------------------------------------------------------

def _svg_bar_chart(points, width=600, height=200, label_key="date",
                   value_key="cost", color="#FFC000", title=""):
    """Render an SVG bar chart. Returns SVG string."""
    if not points:
        return ""
    max_val = max((p[value_key] for p in points), default=1) or 1
    n = len(points)
    pad_l, pad_r, pad_t, pad_b = 10, 10, 30, 40
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    bar_w = max(2, chart_w / max(n, 1) - 2)

    bars = []
    for i, p in enumerate(points):
        v = p[value_key]
        bh = (v / max_val) * chart_h if max_val else 0
        x = pad_l + i * (chart_w / n) + 1
        y = pad_t + chart_h - bh
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                    f'height="{bh:.1f}" rx="2" fill="{color}" opacity="0.85"/>')
        # label every ~5th bar for readability
        if n <= 10 or i % max(1, n // 7) == 0:
            lbl = p[label_key][-5:]  # show MM-DD
            bars.append(f'<text x="{x + bar_w / 2:.1f}" y="{height - 5}" '
                        f'text-anchor="middle" fill="{COLORS["muted"]}" '
                        f'font-size="9">{lbl}</text>')

    title_svg = (f'<text x="{width / 2}" y="18" text-anchor="middle" '
                 f'fill="{COLORS["text"]}" font-size="13" '
                 f'font-weight="bold">{title}</text>') if title else ""

    return (f'<svg viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">{title_svg}'
            f'{"".join(bars)}</svg>')


def _svg_donut_chart(segments, width=250, height=280, title=""):
    """Render an SVG donut chart using stroke-dasharray. Returns SVG string."""
    if not segments:
        return ""
    total = sum(s["value"] for s in segments) or 1
    cx, cy, r = width / 2, 110, 70
    circumference = 2 * math.pi * r
    offset = 0
    arcs = []
    legend = []

    for i, seg in enumerate(segments):
        frac = seg["value"] / total
        dash = frac * circumference
        gap = circumference - dash
        col = seg.get("color", CHART_PALETTE[i % len(CHART_PALETTE)])
        arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                    f'stroke="{col}" stroke-width="30" '
                    f'stroke-dasharray="{dash:.2f} {gap:.2f}" '
                    f'stroke-dashoffset="{-offset:.2f}" '
                    f'transform="rotate(-90 {cx} {cy})"/>')
        offset += dash

        ly = 200 + i * 18
        pct = frac * 100
        legend.append(f'<rect x="20" y="{ly}" width="10" height="10" '
                      f'rx="2" fill="{col}"/>')
        legend.append(f'<text x="36" y="{ly + 10}" fill="{COLORS["text"]}" '
                      f'font-size="11">{seg["label"]} ({pct:.0f}%)</text>')

    dyn_h = 200 + len(segments) * 18 + 10
    title_svg = (f'<text x="{width / 2}" y="18" text-anchor="middle" '
                 f'fill="{COLORS["text"]}" font-size="13" '
                 f'font-weight="bold">{title}</text>') if title else ""

    return (f'<svg viewBox="0 0 {width} {dyn_h}" '
            f'xmlns="http://www.w3.org/2000/svg">{title_svg}'
            f'{"".join(arcs)}{"".join(legend)}</svg>')


def _svg_horiz_bars(items, width=400, height=200, color="#FFC000", title=""):
    """Horizontal bar chart for categorical data. items = [(label, value), ...]"""
    if not items:
        return ""
    max_val = max(v for _, v in items) or 1
    pad_l, pad_t = 100, 30
    bar_h = 22
    dyn_h = pad_t + len(items) * (bar_h + 6) + 10
    chart_w = width - pad_l - 20

    bars = []
    for i, (label, val) in enumerate(items):
        y = pad_t + i * (bar_h + 6)
        bw = (val / max_val) * chart_w
        bars.append(f'<text x="{pad_l - 6}" y="{y + 15}" text-anchor="end" '
                    f'fill="{COLORS["text"]}" font-size="11">{label[:15]}</text>')
        bars.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" '
                    f'height="{bar_h}" rx="4" fill="{color}" opacity="0.85"/>')
        bars.append(f'<text x="{pad_l + bw + 6:.1f}" y="{y + 15}" '
                    f'fill="{COLORS["muted"]}" font-size="11">{val}</text>')

    title_svg = (f'<text x="{width / 2}" y="18" text-anchor="middle" '
                 f'fill="{COLORS["text"]}" font-size="13" '
                 f'font-weight="bold">{title}</text>') if title else ""

    return (f'<svg viewBox="0 0 {width} {dyn_h}" '
            f'xmlns="http://www.w3.org/2000/svg">{title_svg}'
            f'{"".join(bars)}</svg>')


def _svg_gauge(value, max_val, width=200, title=""):
    """Semi-circle arc gauge for quota. Returns SVG string."""
    frac = min(value / max(max_val, 1), 1.0)
    cx, cy, r = width / 2, 110, 70
    # semi-circle path
    circumference_half = math.pi * r

    if frac < 0.5:
        fill_color = "#00b894"
    elif frac < 0.8:
        fill_color = "#fdcb6e"
    else:
        fill_color = "#e94560"

    bg_arc = (f'<path d="M {cx - r} {cy} A {r} {r} 0 1 1 {cx + r} {cy}" '
              f'fill="none" stroke="{COLORS["card"]}" stroke-width="18" '
              f'stroke-linecap="round"/>')
    dash = frac * circumference_half
    gap = circumference_half - dash
    fg_arc = (f'<path d="M {cx - r} {cy} A {r} {r} 0 1 1 {cx + r} {cy}" '
              f'fill="none" stroke="{fill_color}" stroke-width="18" '
              f'stroke-linecap="round" stroke-dasharray="{dash:.2f} {gap:.2f}"/>')

    label = f'{value} / {max_val} today'
    title_svg = (f'<text x="{cx}" y="20" text-anchor="middle" '
                 f'fill="{COLORS["text"]}" font-size="13" '
                 f'font-weight="bold">{title}</text>') if title else ""

    return (f'<svg viewBox="0 0 {width} 150" xmlns="http://www.w3.org/2000/svg">'
            f'{title_svg}{bg_arc}{fg_arc}'
            f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" '
            f'fill="{COLORS["text"]}" font-size="14" font-weight="bold">'
            f'{label}</text></svg>')


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def render_html(data):
    """Generate a self-contained HTML analytics dashboard string."""
    t = data["totals"]
    p = data["period"]
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # -- summary cards --
    cards = [
        ("Total Images", str(t["images"])),
        ("Total Cost", f"${t['cost']:.2f}"),
        ("Avg Cost/Image", f"${data['avg_cost_per_image']:.3f}"),
        ("Sessions", str(t["sessions"])),
    ]
    cards_html = "\n".join(
        f'<div class="card"><div class="card-val">{v}</div>'
        f'<div class="card-lbl">{l}</div></div>'
        for l, v in cards
    )

    # -- charts --
    cost_timeline = _svg_bar_chart(data["daily"], 620, 200, "date", "cost",
                                   COLORS["primary"], "Daily Cost ($)")
    count_timeline = _svg_bar_chart(data["daily"], 620, 160, "date", "count",
                                    COLORS["secondary"], "Daily Image Count")

    # model donut
    model_segs = [{"label": m.split("/")[-1][:20], "value": info["count"],
                   "color": CHART_PALETTE[i % len(CHART_PALETTE)]}
                  for i, (m, info) in enumerate(data["by_model"].items())]
    model_donut = _svg_donut_chart(model_segs, 280, 300, "Model Breakdown")

    # resolution bars
    res_items = sorted(data["by_resolution"].items(),
                       key=lambda x: x[1]["count"], reverse=True)
    res_bars = _svg_horiz_bars([(k, v["count"]) for k, v in res_items],
                               380, 200, COLORS["primary"],
                               "Resolution Distribution")

    # domain bars
    dom_items = sorted(data["by_domain"].items(), key=lambda x: x[1],
                       reverse=True)
    dom_bars = _svg_horiz_bars(dom_items, 380, 200, COLORS["secondary"],
                               "Domain Mode Usage")

    # quota gauge
    q = data["quota"]
    gauge = _svg_gauge(q["today_used"], q["daily_limit"], 220, "Daily Quota")

    # AB preferences bars
    ab_html = ""
    if data.get("ab_preferences"):
        ab = data["ab_preferences"]
        ab_items = [(k, round(v.get("avg_score", 0), 1))
                    for k, v in ab.items() if isinstance(v, dict) and "avg_score" in v]
        if ab_items:
            ab_html = ('<div class="chart-box">'
                       + _svg_horiz_bars(ab_items, 380, 200, "#a29bfe",
                                         "A/B Preference Scores")
                       + '</div>')

    # preset bars
    preset_html = ""
    if data["by_preset"]:
        ps_items = sorted(data["by_preset"].items(), key=lambda x: x[1],
                          reverse=True)[:8]
        preset_html = ('<div class="chart-box">'
                       + _svg_horiz_bars(ps_items, 380, 200, "#53d8fb",
                                         "Top Presets")
                       + '</div>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nano Banana Studio Analytics</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{COLORS["bg"]};color:{COLORS["text"]};font-family:system-ui,-apple-system,sans-serif;padding:24px;max-width:1100px;margin:0 auto}}
header{{text-align:center;padding:20px 0 10px;font-size:22px;font-weight:700;letter-spacing:0.5px}}
header span{{color:{COLORS["primary"]}}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin:20px 0}}
.card{{background:{COLORS["card"]};border-radius:10px;padding:18px 24px;min-width:160px;text-align:center;flex:1;max-width:220px}}
.card-val{{font-size:26px;font-weight:700;color:{COLORS["primary"]}}}
.card-lbl{{font-size:12px;color:{COLORS["muted"]};margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:24px 0}}
.chart-box{{background:{COLORS["card"]};border-radius:10px;padding:16px;overflow:hidden}}
.chart-box.wide{{grid-column:1/-1}}
.chart-box svg{{width:100%;height:auto}}
footer{{text-align:center;color:{COLORS["muted"]};font-size:11px;padding:24px 0 8px;border-top:1px solid {COLORS["card"]}}}
@media(max-width:700px){{.charts{{grid-template-columns:1fr}}.cards{{flex-direction:column;align-items:center}}}}
</style>
</head>
<body>
<header>Nano Banana Studio &mdash; <span>Analytics Dashboard</span></header>
<div class="cards">{cards_html}</div>
<div class="charts">
  <div class="chart-box wide">{cost_timeline}</div>
  <div class="chart-box wide">{count_timeline}</div>
  <div class="chart-box">{model_donut}</div>
  <div class="chart-box">{res_bars}</div>
  <div class="chart-box">{dom_bars}</div>
  <div class="chart-box">{gauge}</div>
  {preset_html}
  {ab_html}
</div>
<footer>Generated {gen_date} | Period: {p["start"]} to {p["end"]} ({p["days"]} days) | Nano Banana Studio v{VERSION}</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_data(args):
    """Output aggregated analytics JSON to stdout."""
    data = aggregate_data(args.days)
    print(json.dumps(data, indent=2))


def cmd_report(args):
    """Generate report in requested format."""
    data = aggregate_data(args.days)

    if args.format == "html":
        html = render_html(data)
        out_path = args.output or str(DEFAULT_OUTPUT)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(html)
        print(json.dumps({"output_path": out_path,
                          "period_days": args.days,
                          "total_images": data["totals"]["images"]}))
    elif args.format == "json":
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(data, f, indent=2)
            print(json.dumps({"output_path": args.output,
                              "period_days": args.days,
                              "total_images": data["totals"]["images"]}))
        else:
            print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Banana Claude Analytics Dashboard")
    sub = parser.add_subparsers(dest="command", required=True)

    # report
    p_report = sub.add_parser("report", help="Generate analytics report")
    p_report.add_argument("--format", required=True, choices=["html", "json"],
                          help="Output format")
    p_report.add_argument("--output", help="Output file path")
    p_report.add_argument("--days", type=int, default=30,
                          help="Number of days to include (default: 30)")

    # data
    p_data = sub.add_parser("data", help="Output aggregated data as JSON")
    p_data.add_argument("--days", type=int, default=30,
                        help="Number of days to include (default: 30)")

    args = parser.parse_args()
    cmds = {"report": cmd_report, "data": cmd_data}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
