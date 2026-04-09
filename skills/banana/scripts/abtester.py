#!/usr/bin/env python3
"""Banana Claude -- A/B Prompt Variation Tester

Generate Literal/Creative/Premium prompt variations from the same creative
brief, rate them, and track preferences over time.

Usage:
    abtester.py generate --idea "coffee shop hero image" --count 3 [--preset NAME] [--ratio 1:1] [--resolution 2K] [--api-key KEY]
    abtester.py rate --test-id ab_20260409_143000 --ratings "1:4,2:5,3:3"
    abtester.py preferences [--limit 10]
    abtester.py history [--limit 10]
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_RESOLUTION = "2K"
DEFAULT_RATIO = "1:1"
COST_PER_IMAGE = 0.078
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"
PREFS_PATH = Path.home() / ".banana" / "ab_preferences.json"
HISTORY_DIR = Path.home() / ".banana" / "ab_history"
PRESETS_DIR = Path.home() / ".banana" / "presets"

VARIATION_STYLES = {
    "literal": {
        "prefix": "A straightforward, clean, commercial-quality",
        "style_hint": "realistic, well-lit, standard commercial photography. Photographed on a Canon EOS R5 with natural studio lighting.",
    },
    "creative": {
        "prefix": "An artistic, conceptual interpretation of",
        "style_hint": "dramatic angles, creative lighting, unexpected composition. Shot on a Sony A7R IV with dramatic side lighting and shallow depth of field.",
    },
    "premium": {
        "prefix": "A premium, luxury editorial",
        "style_hint": "Vanity Fair editorial quality, dramatic Rembrandt lighting, rich depth. Captured on a Hasselblad H6D-100c medium format camera for a prestigious publication spread.",
    },
}

STYLE_ORDER = ["literal", "creative", "premium"]


def _load_api_key(cli_key):
    """Load API key: CLI -> env -> config.json."""
    key = cli_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    config_path = Path.home() / ".banana" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                key = json.load(f).get("google_ai_api_key", "")
        except (json.JSONDecodeError, OSError):
            pass
    if not key:
        print(json.dumps({"error": True, "message": "No API key. Run /banana setup, set GOOGLE_AI_API_KEY env, or pass --api-key"}), file=sys.stderr)
        sys.exit(1)
    return key


def _generate_image(prompt, model, ratio, resolution, api_key):
    """Single Gemini API call with 3-retry exponential backoff on 429."""
    url = f"{API_BASE}/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageSizeOptions": {"imageSize": resolution},
            "aspectRatio": ratio,
        },
    }
    data = json.dumps(body).encode("utf-8")

    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(json.dumps({"retry": True, "attempt": attempt + 1, "wait_seconds": wait}), file=sys.stderr)
                time.sleep(wait)
                continue
            print(json.dumps({"error": True, "status": e.code, "message": error_body}), file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(json.dumps({"error": True, "message": str(e.reason)}), file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps({"error": True, "message": "Max retries exceeded"}), file=sys.stderr)
        sys.exit(1)

    candidates = result.get("candidates", [])
    if not candidates:
        print(json.dumps({"error": True, "message": "No candidates returned"}), file=sys.stderr)
        sys.exit(1)

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])

    print(json.dumps({"error": True, "message": "No image in response"}), file=sys.stderr)
    sys.exit(1)


def _load_preset(name):
    """Load a brand preset by name, return dict or None."""
    if not name:
        return None
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        print(json.dumps({"error": True, "message": f"Preset '{name}' not found"}), file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def build_variation_prompt(idea, style_name, preset=None):
    """Construct prompt from idea + variation style + optional preset."""
    style = VARIATION_STYLES[style_name]
    parts = [f"{style['prefix']} {idea}."]
    parts.append(f"Style: {style['style_hint']}")
    if preset:
        if preset.get("style_description"):
            parts.append(f"Brand style: {preset['style_description']}")
        if preset.get("colors"):
            colors = preset["colors"] if isinstance(preset["colors"], str) else ", ".join(preset["colors"])
            parts.append(f"Color palette: {colors}")
    return " ".join(parts)


def _load_preferences():
    """Load aggregate preferences, return dict."""
    if PREFS_PATH.exists():
        try:
            with open(PREFS_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {s: {"total_score": 0, "count": 0} for s in STYLE_ORDER}


def _save_preferences(prefs):
    """Save aggregate preferences."""
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f, indent=2)


def cmd_generate(args):
    """Generate N variations, save images + comparison JSON."""
    api_key = _load_api_key(args.api_key)
    preset_data = _load_preset(args.preset)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_id = f"ab_{timestamp}"
    test_dir = OUTPUT_DIR / f"ab_test_{timestamp}"
    test_dir.mkdir(parents=True, exist_ok=True)

    styles = STYLE_ORDER[:args.count]
    variations = []

    for style_name in styles:
        prompt = build_variation_prompt(args.idea, style_name, preset_data)
        print(json.dumps({"status": "generating", "style": style_name}), file=sys.stderr)
        image_data = _generate_image(prompt, DEFAULT_MODEL, args.ratio, args.resolution, api_key)
        image_path = test_dir / f"{style_name}.png"
        with open(image_path, "wb") as f:
            f.write(image_data)
        variations.append({
            "style": style_name,
            "prompt": prompt,
            "image_path": str(image_path),
            "cost": COST_PER_IMAGE,
        })

    result = {
        "test_id": test_id,
        "idea": args.idea,
        "variations": variations,
        "total_cost": round(COST_PER_IMAGE * len(variations), 3),
        "output_dir": str(test_dir),
    }

    # Save comparison JSON alongside images
    with open(test_dir / "comparison.json", "w") as f:
        json.dump(result, f, indent=2)

    # Save to history
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_DIR / f"{test_id}.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


def cmd_rate(args):
    """Record ratings and update aggregate preferences."""
    # Load the test from history
    history_path = HISTORY_DIR / f"{args.test_id}.json"
    if not history_path.exists():
        print(json.dumps({"error": True, "message": f"Test '{args.test_id}' not found"}), file=sys.stderr)
        sys.exit(1)

    with open(history_path) as f:
        test_data = json.load(f)

    # Parse ratings: "1:4,2:5,3:3" -> {index: score}
    ratings_map = {}
    for pair in args.ratings.split(","):
        idx_str, score_str = pair.strip().split(":")
        idx = int(idx_str) - 1  # 1-indexed to 0-indexed
        score = int(score_str)
        if score < 1 or score > 5:
            print(json.dumps({"error": True, "message": f"Rating must be 1-5, got {score}"}), file=sys.stderr)
            sys.exit(1)
        ratings_map[idx] = score

    # Map index to style name
    rated = {}
    for idx, score in ratings_map.items():
        if idx < len(test_data["variations"]):
            style = test_data["variations"][idx]["style"]
            rated[style] = score

    # Update aggregate preferences
    prefs = _load_preferences()
    for style, score in rated.items():
        if style not in prefs:
            prefs[style] = {"total_score": 0, "count": 0}
        prefs[style]["total_score"] += score
        prefs[style]["count"] += 1
    _save_preferences(prefs)

    # Save ratings back to test history
    test_data["ratings"] = rated
    with open(history_path, "w") as f:
        json.dump(test_data, f, indent=2)

    print(json.dumps({"test_id": args.test_id, "rated": True, "ratings": rated}, indent=2))


def cmd_preferences(args):
    """Show aggregate preference data with recommendation."""
    prefs = _load_preferences()
    total_tests = max(prefs[s]["count"] for s in prefs) if any(prefs[s]["count"] for s in prefs) else 0

    output = {}
    best_style = None
    best_avg = 0.0
    for style in STYLE_ORDER:
        p = prefs.get(style, {"total_score": 0, "count": 0})
        avg = round(p["total_score"] / p["count"], 1) if p["count"] else 0.0
        output[style] = {"total_score": p["total_score"], "count": p["count"], "avg_score": avg}
        if avg > best_avg:
            best_avg = avg
            best_style = style

    result = {
        "preferences": output,
        "total_tests": total_tests,
        "recommendation": best_style or "none",
    }
    print(json.dumps(result, indent=2))


def cmd_history(args):
    """List past A/B tests."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(HISTORY_DIR.glob("ab_*.json"), key=lambda f: f.stem, reverse=True)
    files = files[:args.limit]

    tests = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            tests.append({
                "test_id": data.get("test_id", f.stem),
                "idea": data.get("idea", ""),
                "variations": len(data.get("variations", [])),
                "rated": "ratings" in data,
                "total_cost": data.get("total_cost", 0),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    print(json.dumps({"tests": tests, "total": len(list(HISTORY_DIR.glob("ab_*.json")))}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Banana Claude A/B Prompt Variation Tester")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="Generate prompt variations for an idea")
    p_gen.add_argument("--idea", required=True, help="Creative brief / idea description")
    p_gen.add_argument("--count", type=int, default=3, choices=[1, 2, 3], help="Number of variations (default: 3)")
    p_gen.add_argument("--preset", help="Brand Style Guide preset name")
    p_gen.add_argument("--ratio", default=DEFAULT_RATIO, help=f"Aspect ratio (default: {DEFAULT_RATIO})")
    p_gen.add_argument("--resolution", default=DEFAULT_RESOLUTION, help=f"Resolution (default: {DEFAULT_RESOLUTION})")
    p_gen.add_argument("--api-key", default=None, help="Google AI API key")

    # rate
    p_rate = sub.add_parser("rate", help="Rate variations from a test")
    p_rate.add_argument("--test-id", required=True, help="Test ID (e.g. ab_20260409_143000)")
    p_rate.add_argument("--ratings", required=True, help="Ratings as index:score pairs (e.g. 1:4,2:5,3:3)")

    # preferences
    p_prefs = sub.add_parser("preferences", help="Show aggregate style preferences")
    p_prefs.add_argument("--limit", type=int, default=10, help="Max entries (unused, reserved)")

    # history
    p_hist = sub.add_parser("history", help="List past A/B tests")
    p_hist.add_argument("--limit", type=int, default=10, help="Max tests to show")

    args = parser.parse_args()
    cmds = {
        "generate": cmd_generate,
        "rate": cmd_rate,
        "preferences": cmd_preferences,
        "history": cmd_history,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
