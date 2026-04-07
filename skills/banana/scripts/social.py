#!/usr/bin/env python3
"""Banana Claude -- Social Media Multi-Platform Image Generator

Generate images optimized for 45+ social media placements from a single prompt.
Groups platforms by aspect ratio to avoid duplicate API calls, generates at 4K,
and crops to exact platform pixels with ImageMagick.

Uses only Python stdlib (no pip dependencies).

Usage:
    social.py generate --prompt "a cat in space" --platforms ig-feed,yt-thumb
    social.py generate --prompt "product hero" --platforms instagram,youtube --mode complete
    social.py list
    social.py info ig-feed
    social.py info instagram
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_RESOLUTION = "4K"
OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# ---------------------------------------------------------------------------
# Platform definitions
# ---------------------------------------------------------------------------

PLATFORMS = {
    # --- Instagram ---
    "ig-feed":        {"name": "Instagram Feed Portrait",       "pixels": (1080, 1350), "ratio": "4:5",  "resolution": "4K", "notes": "Bottom 20% may be obscured by caption overlay"},
    "ig-square":      {"name": "Instagram Feed Square",         "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Center subject; edges may clip on older devices"},
    "ig-landscape":   {"name": "Instagram Feed Landscape",      "pixels": (1080, 566),  "ratio": "16:9", "resolution": "4K", "notes": "Crop top/bottom from 16:9"},
    "ig-story":       {"name": "Instagram Story / Reel",        "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Top 15% and bottom 25% obscured by UI"},
    "ig-reel-cover":  {"name": "Instagram Reel Cover",          "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Center of frame is visible thumbnail"},
    "ig-profile":     {"name": "Instagram Profile Picture",     "pixels": (320, 320),   "ratio": "1:1",  "resolution": "4K", "notes": "Circular crop -- keep subject in center 70%"},

    # --- Facebook ---
    "fb-feed":        {"name": "Facebook Feed Square",          "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Center subject"},
    "fb-landscape":   {"name": "Facebook Feed Landscape",       "pixels": (1200, 630),  "ratio": "16:9", "resolution": "4K", "notes": "Crop from 16:9; link preview crops tighter"},
    "fb-portrait":    {"name": "Facebook Feed Portrait",        "pixels": (1080, 1350), "ratio": "4:5",  "resolution": "4K", "notes": "Truncated in feed with See More"},
    "fb-story":       {"name": "Facebook Story / Reel",         "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Top 14% is profile bar; bottom 20% is CTA"},
    "fb-cover":       {"name": "Facebook Cover Photo",          "pixels": (820, 312),   "ratio": "21:9", "resolution": "4K", "notes": "Mobile crops to ~640x360; keep subject centered"},
    "fb-ad":          {"name": "Facebook Feed Ad",              "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Bottom 20% overlaid with ad copy"},
    "fb-story-ad":    {"name": "Facebook Story Ad",             "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Bottom 25% is CTA button area"},

    # --- YouTube ---
    "yt-thumb":       {"name": "YouTube Thumbnail",             "pixels": (1280, 720),  "ratio": "16:9", "resolution": "4K", "notes": "Bottom-right corner has timestamp overlay"},
    "yt-banner":      {"name": "YouTube Channel Banner",        "pixels": (2560, 1440), "ratio": "16:9", "resolution": "4K", "notes": "Safe area is center 1546x423 on desktop"},
    "yt-shorts":      {"name": "YouTube Shorts Thumbnail",      "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Center subject; top/bottom cropped in browse"},

    # --- LinkedIn ---
    "li-landscape":   {"name": "LinkedIn Feed Landscape",       "pixels": (1200, 627),  "ratio": "16:9", "resolution": "4K", "notes": "Standard share image"},
    "li-portrait":    {"name": "LinkedIn Feed Portrait",        "pixels": (1080, 1350), "ratio": "4:5",  "resolution": "4K", "notes": "Truncated in feed; top portion most visible"},
    "li-square":      {"name": "LinkedIn Feed Square",          "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Safe choice for LinkedIn"},
    "li-banner":      {"name": "LinkedIn Banner",               "pixels": (1584, 396),  "ratio": "4:1",  "resolution": "4K", "notes": "Keep subject in center band"},
    "li-carousel":    {"name": "LinkedIn Carousel Slide",       "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Keep margins; swipe arrows overlay edges"},
    "li-carousel-portrait": {"name": "LinkedIn Carousel Portrait", "pixels": (1080, 1350), "ratio": "4:5", "resolution": "4K", "notes": "More vertical real estate"},
    "li-ad":          {"name": "LinkedIn Sponsored Content",     "pixels": (1200, 627),  "ratio": "16:9", "resolution": "4K", "notes": "Same as feed landscape"},

    # --- Twitter / X ---
    "x-landscape":    {"name": "Twitter/X Feed Landscape",      "pixels": (1600, 900),  "ratio": "16:9", "resolution": "4K", "notes": "Crops from center on mobile"},
    "x-square":       {"name": "Twitter/X Feed Square",         "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Displayed with slight letterboxing"},
    "x-header":       {"name": "Twitter/X Header",              "pixels": (1500, 500),  "ratio": "3:2",  "resolution": "4K", "notes": "Crop from 3:2; keep subject in center band"},
    "x-ad":           {"name": "Twitter/X In-Feed Ad",          "pixels": (1600, 900),  "ratio": "16:9", "resolution": "4K", "notes": "Bottom may have ad label overlay"},

    # --- TikTok ---
    "tt-feed":        {"name": "TikTok Feed / Cover",           "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Bottom 25% has caption/music overlay"},
    "tt-ad":          {"name": "TikTok In-Feed Ad",             "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "CTA button in bottom 20%"},

    # --- Pinterest ---
    "pin-standard":   {"name": "Pinterest Standard Pin",        "pixels": (1000, 1500), "ratio": "2:3",  "resolution": "4K", "notes": "Optimal ratio for Pinterest grid"},
    "pin-long":       {"name": "Pinterest Long Pin",            "pixels": (1000, 2100), "ratio": "1:4",  "resolution": "4K", "notes": "Crop from 1:4; tall pins get more grid space"},
    "pin-square":     {"name": "Pinterest Square Pin",          "pixels": (1000, 1000), "ratio": "1:1",  "resolution": "4K", "notes": "Less grid presence than portrait"},

    # --- Threads ---
    "threads-portrait":  {"name": "Threads Feed Portrait",      "pixels": (1080, 1350), "ratio": "4:5",  "resolution": "4K", "notes": "Same as Instagram feed portrait"},
    "threads-vertical":  {"name": "Threads Feed Vertical",      "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Full vertical; bottom has interaction bar"},
    "threads-square":    {"name": "Threads Feed Square",        "pixels": (1080, 1080), "ratio": "1:1",  "resolution": "4K", "notes": "Safe default"},

    # --- Snapchat ---
    "snap-story":     {"name": "Snapchat Story",                "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Top 15% header; bottom 20% swipe-up/reply"},
    "snap-ad":        {"name": "Snapchat Ad",                   "pixels": (1080, 1920), "ratio": "9:16", "resolution": "4K", "notes": "Bottom 30% is CTA; subject in upper 60%"},

    # --- Google Ads ---
    "gads-landscape":   {"name": "Google Ads Responsive Landscape", "pixels": (1200, 628),  "ratio": "16:9", "resolution": "4K", "notes": "Google may auto-crop further"},
    "gads-square":      {"name": "Google Ads Responsive Square",    "pixels": (1200, 1200), "ratio": "1:1",  "resolution": "4K", "notes": "Ad text overlaid below"},
    "gads-leaderboard": {"name": "Google Ads Display Leaderboard",  "pixels": (728, 90),    "ratio": "8:1",  "resolution": "4K", "notes": "Extreme horizontal; patterns or simple subject"},
    "gads-skyscraper":  {"name": "Google Ads Display Skyscraper",   "pixels": (160, 600),   "ratio": "1:4",  "resolution": "4K", "notes": "Narrow vertical; text must be large"},
    "gads-half-page":   {"name": "Google Ads Display Half-Page",    "pixels": (300, 600),   "ratio": "1:4",  "resolution": "4K", "notes": "Keep subject in upper half"},
    "gads-rectangle":   {"name": "Google Ads Display Rectangle",    "pixels": (300, 250),   "ratio": "5:4",  "resolution": "4K", "notes": "Compact format; center everything"},
    "gads-pmax":        {"name": "Google Ads Performance Max",      "pixels": (1200, 628),  "ratio": "16:9", "resolution": "4K", "notes": "Google auto-crops aggressively"},

    # --- Spotify ---
    "spotify-cover":    {"name": "Spotify Playlist/Album Cover",  "pixels": (3000, 3000), "ratio": "1:1",  "resolution": "4K", "notes": "Circular crop on some views; center 80%"},
    "spotify-banner":   {"name": "Spotify Artist Banner",         "pixels": (2660, 1140), "ratio": "21:9", "resolution": "4K", "notes": "Text overlays on left side"},
}

# Group shorthands expand to multiple platform keys
GROUPS = {
    "instagram":   ["ig-feed", "ig-square", "ig-story"],
    "facebook":    ["fb-feed", "fb-landscape", "fb-story"],
    "youtube":     ["yt-thumb", "yt-banner"],
    "linkedin":    ["li-landscape", "li-square", "li-banner"],
    "twitter":     ["x-landscape", "x-header"],
    "tiktok":      ["tt-feed"],
    "pinterest":   ["pin-standard"],
    "threads":     ["threads-portrait", "threads-square"],
    "snapchat":    ["snap-story"],
    "google-ads":  ["gads-landscape", "gads-square"],
    "spotify":     ["spotify-cover"],
    "all-feeds":   ["ig-feed", "fb-feed", "li-landscape", "x-landscape", "threads-portrait"],
    "all-stories": ["ig-story", "fb-story", "snap-story", "tt-feed"],
    "all-ads":     ["fb-ad", "fb-story-ad", "li-ad", "x-ad", "tt-ad", "gads-landscape", "gads-square", "snap-ad"],
}

# 4K generation sizes for each native ratio
RATIO_4K_SIZES = {
    "1:1":  (4096, 4096),
    "2:3":  (2731, 4096),
    "3:2":  (4096, 2731),
    "3:4":  (3072, 4096),
    "4:3":  (4096, 3072),
    "4:5":  (3200, 4000),
    "5:4":  (4096, 3277),
    "9:16": (2304, 4096),
    "16:9": (4096, 2304),
    "21:9": (4096, 1756),
    "1:4":  (1024, 4096),
    "4:1":  (4096, 1024),
    "1:8":  (512, 4096),
    "8:1":  (4096, 512),
}


# ---------------------------------------------------------------------------
# API key loading
# ---------------------------------------------------------------------------

def _load_api_key(cli_key=None):
    """Load Google AI API key from CLI, env, or config file."""
    key = cli_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        config_path = Path.home() / ".banana" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    key = json.load(f).get("google_ai_api_key", "")
            except (json.JSONDecodeError, OSError):
                pass
    return key or None


# ---------------------------------------------------------------------------
# Platform resolution
# ---------------------------------------------------------------------------

def resolve_platforms(platform_str):
    """Resolve a comma-separated platform string into a list of platform keys.

    Handles individual keys (ig-feed), group names (instagram), and 'all'.
    """
    if platform_str.strip().lower() == "all":
        return sorted(PLATFORMS.keys())

    keys = []
    for token in platform_str.split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token in GROUPS:
            keys.extend(GROUPS[token])
        elif token in PLATFORMS:
            keys.append(token)
        else:
            print(json.dumps({"error": True, "message": f"Unknown platform '{token}'. Run 'social.py list' to see available platforms."}))
            sys.exit(1)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def group_by_ratio(platform_keys):
    """Group platform keys by their generation ratio.

    Returns dict: ratio -> list of platform keys.
    This avoids duplicate API calls for platforms sharing the same ratio.
    """
    groups = {}
    for key in platform_keys:
        ratio = PLATFORMS[key]["ratio"]
        groups.setdefault(ratio, []).append(key)
    return groups


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

def generate_image(prompt, model, aspect_ratio, resolution, api_key, image_only=True):
    """Call Gemini API to generate an image. Returns (image_bytes, error_string)."""
    import urllib.request
    import urllib.error

    url = f"{API_BASE}/{model}:generateContent?key={api_key}"

    modalities = ["IMAGE"] if image_only else ["TEXT", "IMAGE"]
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": modalities,
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": resolution,
            },
        },
    }

    data = json.dumps(body).encode("utf-8")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            candidates = result.get("candidates", [])
            if not candidates:
                reason = result.get("promptFeedback", {}).get("blockReason", "No candidates")
                return None, f"No candidates: {reason}"

            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"]), None

            finish_reason = candidates[0].get("finishReason", "UNKNOWN")
            return None, f"No image in response. finishReason: {finish_reason}"

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429 and attempt < max_retries - 1:
                wait = min(2 ** (attempt + 1), 32)
                print(f"  Rate limited (429). Waiting {wait}s... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code == 400 and "FAILED_PRECONDITION" in error_body:
                return None, "Billing not enabled. Enable at https://aistudio.google.com/apikey"
            return None, f"HTTP {e.code}: {error_body[:300]}"
        except urllib.error.URLError as e:
            return None, f"Network error: {e.reason}"

    return None, "Max retries exceeded"


# ---------------------------------------------------------------------------
# ImageMagick cropping
# ---------------------------------------------------------------------------

def crop_image(input_path, output_path, target_w, target_h):
    """Crop an image to exact dimensions using ImageMagick.

    Uses -resize to scale down to cover the target, then -crop to exact pixels.
    Falls back to a copy if ImageMagick is not available.
    """
    convert_cmd = shutil.which("magick") or shutil.which("convert")
    if not convert_cmd:
        # No ImageMagick -- just copy the original
        shutil.copy2(input_path, output_path)
        return False

    cmd = [
        convert_cmd, str(input_path),
        "-resize", f"{target_w}x{target_h}^",
        "-gravity", "center",
        "-crop", f"{target_w}x{target_h}+0+0",
        "+repage",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        shutil.copy2(input_path, output_path)
        return False


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_generate(args):
    """Generate images for one or more social media platforms."""
    api_key = _load_api_key(args.api_key)
    if not api_key:
        print(json.dumps({"error": True, "message": "No API key. Run /banana setup, set GOOGLE_AI_API_KEY env, or pass --api-key"}))
        sys.exit(1)

    platform_keys = resolve_platforms(args.platforms)
    if not platform_keys:
        print(json.dumps({"error": True, "message": "No platforms specified. Use --platforms ig-feed,yt-thumb or --platforms instagram"}))
        sys.exit(1)

    model = args.model or DEFAULT_MODEL
    image_only = args.mode != "complete"

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output).resolve() if args.output else OUTPUT_DIR / f"social_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group platforms by ratio to minimize API calls
    ratio_groups = group_by_ratio(platform_keys)

    print(f"Generating for {len(platform_keys)} platform(s) across {len(ratio_groups)} unique ratio(s)...")
    print(f"  Model: {model}")
    print(f"  Mode: {'Complete (with text)' if not image_only else 'Image Only'}")
    print(f"  Output: {output_dir}")
    print()

    results = []
    generated_originals = {}  # ratio -> path to original file

    for ratio_idx, (ratio, keys) in enumerate(sorted(ratio_groups.items())):
        gen_w, gen_h = RATIO_4K_SIZES.get(ratio, (4096, 4096))
        platform_names = ", ".join(PLATFORMS[k]["name"] for k in keys)
        print(f"  [{ratio_idx + 1}/{len(ratio_groups)}] Generating {ratio} ({gen_w}x{gen_h}) for: {platform_names}...", end=" ", flush=True)

        image_data, error = generate_image(
            prompt=args.prompt,
            model=model,
            aspect_ratio=ratio,
            resolution=DEFAULT_RESOLUTION,
            api_key=api_key,
            image_only=image_only,
        )

        if not image_data:
            print(f"FAILED: {error}")
            for k in keys:
                results.append({"platform": k, "name": PLATFORMS[k]["name"], "success": False, "error": error})
            continue

        # Save original (uncropped)
        safe_ratio = ratio.replace(":", "x")
        original_filename = f"original_{safe_ratio}_{timestamp}.png"
        original_path = output_dir / original_filename
        with open(original_path, "wb") as f:
            f.write(image_data)
        generated_originals[ratio] = str(original_path)
        print("OK")

        # Crop for each platform in this ratio group
        for k in keys:
            spec = PLATFORMS[k]
            target_w, target_h = spec["pixels"]
            cropped_filename = f"{k}_{target_w}x{target_h}.png"
            cropped_path = output_dir / cropped_filename

            used_magick = crop_image(original_path, cropped_path, target_w, target_h)
            method = "cropped" if used_magick else "copied (no ImageMagick)"
            print(f"    -> {k}: {target_w}x{target_h} ({method})")

            results.append({
                "platform": k,
                "name": spec["name"],
                "pixels": f"{target_w}x{target_h}",
                "ratio": ratio,
                "original": str(original_path),
                "cropped": str(cropped_path),
                "success": True,
            })

        # Brief pause between ratio groups to avoid rate limits
        if ratio_idx < len(ratio_groups) - 1:
            time.sleep(1)

    # Summary
    succeeded = sum(1 for r in results if r["success"])
    failed = len(results) - succeeded

    print()
    print(f"Done! {succeeded}/{len(platform_keys)} platform images generated.")
    if failed:
        print(f"  {failed} failed -- check errors above.")
    print(f"  API calls made: {len(ratio_groups)} (one per unique ratio)")
    print(f"  Output: {output_dir}")

    # Write summary JSON
    summary = {
        "timestamp": timestamp,
        "prompt": args.prompt,
        "model": model,
        "mode": "complete" if not image_only else "image-only",
        "total_platforms": len(platform_keys),
        "succeeded": succeeded,
        "failed": failed,
        "api_calls": len(ratio_groups),
        "originals": generated_originals,
        "platforms": results,
    }
    summary_path = output_dir / "social-summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Machine-readable final output
    print(json.dumps({
        "success": True,
        "total": len(platform_keys),
        "succeeded": succeeded,
        "failed": failed,
        "api_calls": len(ratio_groups),
        "output_dir": str(output_dir),
        "summary": str(summary_path),
    }))


def cmd_list(args):
    """List all available platforms and groups."""
    print("Available platforms:")
    print()

    # Group by platform family
    families = {}
    for key, spec in sorted(PLATFORMS.items()):
        family = key.split("-")[0]
        families.setdefault(family, []).append((key, spec))

    for family, entries in families.items():
        family_label = {
            "ig": "Instagram", "fb": "Facebook", "yt": "YouTube",
            "li": "LinkedIn", "x": "Twitter/X", "tt": "TikTok",
            "pin": "Pinterest", "threads": "Threads", "snap": "Snapchat",
            "gads": "Google Ads", "spotify": "Spotify",
        }.get(family, family.upper())

        print(f"  {family_label}:")
        for key, spec in entries:
            w, h = spec["pixels"]
            print(f"    {key:<25} {w:>4}x{h:<4}  ({spec['ratio']})")
        print()

    print("Group shorthands:")
    for group, keys in sorted(GROUPS.items()):
        print(f"  {group:<15} -> {', '.join(keys)}")
    print()
    print(f"Total: {len(PLATFORMS)} platforms, {len(GROUPS)} groups")
    print()
    print("Use 'all' to generate for every platform.")


def cmd_info(args):
    """Show detailed info for a platform or group."""
    target = args.target.strip().lower()

    if target in GROUPS:
        print(f"Group: {target}")
        print(f"  Expands to: {', '.join(GROUPS[target])}")
        print()
        for key in GROUPS[target]:
            _print_platform_info(key)
        return

    if target in PLATFORMS:
        _print_platform_info(target)
        return

    print(json.dumps({"error": True, "message": f"Unknown platform or group '{target}'. Run 'social.py list' to see options."}))
    sys.exit(1)


def _print_platform_info(key):
    """Print detailed info for a single platform."""
    spec = PLATFORMS[key]
    w, h = spec["pixels"]
    gen_w, gen_h = RATIO_4K_SIZES.get(spec["ratio"], (4096, 4096))
    print(f"  {key}:")
    print(f"    Name:          {spec['name']}")
    print(f"    Pixels:        {w}x{h}")
    print(f"    Ratio:         {spec['ratio']}")
    print(f"    Generate at:   {gen_w}x{gen_h} (4K)")
    print(f"    Notes:         {spec['notes']}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Banana Claude Social Media Multi-Platform Image Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  social.py generate --prompt "a red sports car" --platforms ig-feed,yt-thumb
  social.py generate --prompt "product hero" --platforms instagram --mode complete
  social.py generate --prompt "sunset beach" --platforms all-feeds
  social.py list
  social.py info ig-feed
  social.py info instagram""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="Generate images for social media platforms")
    p_gen.add_argument("--prompt", required=True, help="Image generation prompt")
    p_gen.add_argument("--platforms", required=True,
                       help="Comma-separated platform keys, group names, or 'all'")
    p_gen.add_argument("--output", default=None, help="Output directory")
    p_gen.add_argument("--mode", choices=["complete", "image-only"], default="image-only",
                       help="Output mode: complete (with text) or image-only (default)")
    p_gen.add_argument("--model", default=None, help=f"Model ID (default: {DEFAULT_MODEL})")
    p_gen.add_argument("--api-key", default=None, help="Google AI API key")

    # list
    sub.add_parser("list", help="List all available platforms and groups")

    # info
    p_info = sub.add_parser("info", help="Show details for a platform or group")
    p_info.add_argument("target", help="Platform key or group name")

    args = parser.parse_args()
    cmds = {"generate": cmd_generate, "list": cmd_list, "info": cmd_info}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
