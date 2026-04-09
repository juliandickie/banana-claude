# A/B Testing Reference

> Load this when the user runs `/banana ab-test` or asks to compare
> prompt variations or test different styles.

## Overview

Generate Literal/Creative/Premium prompt variations from the same creative brief. Each variation applies a different creative lens to the same idea. Users rate the results, and preferences are tracked over time to learn which styles work best.

## Usage

```bash
# Generate 3 variations (default: literal, creative, premium)
python3 ${CLAUDE_SKILL_DIR}/scripts/abtester.py generate --idea "coffee shop hero image" --count 3

# Rate the results (1-5 scale per variation)
python3 ${CLAUDE_SKILL_DIR}/scripts/abtester.py rate --test-id ab_20260409_143000 --ratings "1:4,2:5,3:3"

# View aggregate preferences
python3 ${CLAUDE_SKILL_DIR}/scripts/abtester.py preferences

# See past tests
python3 ${CLAUDE_SKILL_DIR}/scripts/abtester.py history
```

## Variation Styles

| Style | Approach | Best For |
|-------|----------|----------|
| **Literal** | Clean, commercial, faithful to brief | E-commerce, product pages, documentation |
| **Creative** | Dramatic angles, unexpected composition | Social media, blog headers, editorial |
| **Premium** | Luxury editorial, prestigious context anchors | Ads, hero images, print campaigns |

Each style adds a prefix and style hint to the base prompt, keeping the core subject and composition consistent while varying the aesthetic approach.

## Rating System

After reviewing the generated variations, rate each on a 1-5 scale:
- **5** — Perfect, would use as-is
- **4** — Strong, minor tweaks needed
- **3** — Acceptable, significant refinement needed
- **2** — Wrong direction
- **1** — Completely off

Ratings are format: `"variation_index:score"` (e.g., `"1:4,2:5,3:3"`).

## Preferences

Ratings aggregate over time in `~/.banana/ab_preferences.json`. The system tracks:
- Average score per variation style
- Total tests run
- Which style is recommended based on aggregate scores

## Storage

- Test results: `~/Documents/nanobanana_generated/ab_test_TIMESTAMP/`
- Preferences: `~/.banana/ab_preferences.json`
- History: `~/.banana/ab_history/`
