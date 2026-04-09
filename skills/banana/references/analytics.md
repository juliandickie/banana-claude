# Analytics Dashboard Reference

> Load this when the user runs `/banana analytics` or asks about usage
> statistics, cost trends, or quota monitoring.

## Overview

Self-contained HTML dashboard showing cost trends, domain usage, model breakdown, and quota monitoring. Reads from existing cost tracker and session history data.

## Usage

```bash
# Generate HTML dashboard
python3 ${CLAUDE_SKILL_DIR}/scripts/analytics.py report --format html --output ~/analytics.html

# Get raw data as JSON
python3 ${CLAUDE_SKILL_DIR}/scripts/analytics.py data --days 30

# Export as JSON file
python3 ${CLAUDE_SKILL_DIR}/scripts/analytics.py report --format json --output ~/analytics.json
```

## Dashboard Sections

| Section | Chart Type | Data Source |
|---------|-----------|-------------|
| Summary Cards | Text | costs.json totals |
| Cost Timeline | Bar chart | costs.json daily entries |
| Model Breakdown | Donut chart | costs.json + history entries |
| Resolution Distribution | Horizontal bars | costs.json entries |
| Domain Mode Usage | Horizontal bars | history session entries |
| Quota Gauge | Arc gauge | costs.json today count vs 500 RPD limit |
| A/B Preferences | Bars | ab_preferences.json (if exists) |

## Data Sources

The dashboard aggregates from three existing data files (no new logging needed):
- `~/.banana/costs.json` — created by cost_tracker.py
- `~/.banana/history/*.json` — created by history.py
- `~/.banana/ab_preferences.json` — created by abtester.py

## Time Range

Default: last 30 days. Adjust with `--days N`. The dashboard shows data within the specified period only.

## Output

The HTML dashboard is self-contained — no external JavaScript or CSS dependencies. Opens in any browser. Can be printed to PDF.
