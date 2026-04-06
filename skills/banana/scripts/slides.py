#!/usr/bin/env python3
"""Banana Claude -- Slide Deck Pipeline

Parse slide prompts from markdown and batch-generate images.
Uses only Python stdlib (no pip dependencies).

Usage:
    slides.py generate --prompts path/to/prompts.md --output ~/slides/
    slides.py generate --prompts path/to/prompts.md --output ~/slides/ --mode background
    slides.py generate --prompts path/to/prompts.md --output ~/slides/ --mode complete
    slides.py estimate --prompts path/to/prompts.md
    slides.py template --output path/to/template.md

Prompts markdown format:
    ## Slide 01 — Title Slide
    ```
    A dark premium presentation slide background...
    ```

    ## Slide 02 — Content Slide
    ```
    A widescreen slide background with...
    ```

Each ## heading with a ``` code block is one slide to generate.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_RESOLUTION = "4K"
DEFAULT_RATIO = "16:9"
OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Pricing for estimates
PRICING = {
    "gemini-3.1-flash-image-preview": {"512": 0.020, "1K": 0.039, "2K": 0.078, "4K": 0.156},
}


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


def parse_prompts_markdown(md_path):
    """Parse a slide prompts markdown file into a list of slide dicts.

    Expected format:
        ## Slide 01 — Title Slide
        ```
        prompt text here
        ```

    Returns list of: {"number": "01", "name": "Title Slide", "prompt": "..."}
    """
    md_path = Path(md_path).resolve()
    if not md_path.exists():
        print(json.dumps({"error": True, "message": f"Prompts file not found: {md_path}"}))
        sys.exit(1)

    with open(md_path, "r") as f:
        content = f.read()

    slides = []
    # Match ## Slide NN — Name followed by a code block
    pattern = r'##\s+Slide\s+(\S+)\s*[—–-]\s*(.+?)\n.*?```\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    for number, name, prompt in matches:
        prompt = prompt.strip()
        if prompt:
            slides.append({
                "number": number.strip(),
                "name": name.strip(),
                "prompt": prompt,
            })

    if not slides:
        # Try simpler format: any ## heading followed by a code block
        pattern = r'##\s+(.+?)\n.*?```\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        for i, (name, prompt) in enumerate(matches, 1):
            prompt = prompt.strip()
            if prompt:
                slides.append({
                    "number": f"{i:02d}",
                    "name": name.strip(),
                    "prompt": prompt,
                })

    return slides


def generate_single_image(prompt, model, aspect_ratio, resolution, api_key):
    """Call Gemini API to generate a single image. Returns image bytes or None."""
    url = f"{API_BASE}/{model}:generateContent?key={api_key}"

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": resolution,
            },
        },
    }

    data = json.dumps(body).encode("utf-8")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # Extract image
            candidates = result.get("candidates", [])
            if not candidates:
                return None, result.get("promptFeedback", {}).get("blockReason", "No candidates")

            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"]), None

            finish_reason = candidates[0].get("finishReason", "UNKNOWN")
            return None, f"No image in response. finishReason: {finish_reason}"

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited. Waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            return None, f"HTTP {e.code}: {error_body[:200]}"
        except urllib.error.URLError as e:
            return None, f"Network error: {e.reason}"

    return None, "Max retries exceeded"


def cmd_generate(args):
    """Generate images from a prompts markdown file."""
    slides = parse_prompts_markdown(args.prompts)
    if not slides:
        print(json.dumps({"error": True, "message": "No slides found in prompts file. Expected ## Slide NN — Name followed by ``` code blocks."}))
        sys.exit(1)

    api_key = _load_api_key(args.api_key)
    if not api_key:
        print(json.dumps({"error": True, "message": "No API key. Run /banana setup, set GOOGLE_AI_API_KEY env, or pass --api-key"}))
        sys.exit(1)

    # Set up output directory
    output_dir = Path(args.output).resolve() if args.output else OUTPUT_DIR / f"slides_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = args.model or DEFAULT_MODEL
    resolution = args.resolution or DEFAULT_RESOLUTION
    ratio = args.ratio or DEFAULT_RATIO

    # Filter by mode if specified
    mode_suffix = ""
    if args.mode == "background":
        mode_suffix = "_bg"
    elif args.mode == "complete":
        mode_suffix = "_complete"

    print(f"Generating {len(slides)} slides...")
    print(f"  Model: {model}")
    print(f"  Resolution: {resolution}")
    print(f"  Ratio: {ratio}")
    print(f"  Output: {output_dir}")
    print(f"  Estimated cost: ${len(slides) * PRICING.get(model, PRICING[DEFAULT_MODEL]).get(resolution, 0.078):.2f}")
    print()

    results = []
    for i, slide in enumerate(slides):
        slide_num = slide["number"]
        slide_name = slide["name"]
        # Clean name for filename
        safe_name = re.sub(r'[^\w\s-]', '', slide_name).strip().lower()
        safe_name = re.sub(r'[\s]+', '-', safe_name)
        filename = f"slide-{slide_num}-{safe_name}{mode_suffix}.png"
        filepath = output_dir / filename

        print(f"  [{i+1}/{len(slides)}] Slide {slide_num}: {slide_name}...", end=" ", flush=True)

        image_data, error = generate_single_image(
            prompt=slide["prompt"],
            model=model,
            aspect_ratio=ratio,
            resolution=resolution,
            api_key=api_key,
        )

        if image_data:
            with open(filepath, "wb") as f:
                f.write(image_data)
            print(f"OK → {filename}")
            results.append({"slide": slide_num, "name": slide_name, "path": str(filepath), "success": True})
        else:
            print(f"FAILED: {error}")
            results.append({"slide": slide_num, "name": slide_name, "error": error, "success": False})

        # Brief pause between generations to avoid rate limits
        if i < len(slides) - 1:
            time.sleep(1)

    # Summary
    succeeded = sum(1 for r in results if r["success"])
    failed = len(results) - succeeded
    total_cost = succeeded * PRICING.get(model, PRICING[DEFAULT_MODEL]).get(resolution, 0.078)

    print()
    print(f"Done! {succeeded}/{len(slides)} slides generated.")
    if failed:
        print(f"  {failed} failed — check errors above.")
    print(f"  Output: {output_dir}")
    print(f"  Estimated cost: ${total_cost:.2f}")

    # Write summary JSON
    summary_path = output_dir / "generation-summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "total": len(slides),
            "succeeded": succeeded,
            "failed": failed,
            "estimated_cost": round(total_cost, 3),
            "model": model,
            "resolution": resolution,
            "ratio": ratio,
            "slides": results,
        }, f, indent=2)

    print(json.dumps({"success": True, "total": len(slides), "succeeded": succeeded,
                       "failed": failed, "output_dir": str(output_dir),
                       "estimated_cost": round(total_cost, 3)}))


def cmd_estimate(args):
    """Estimate cost for a prompts file without generating."""
    slides = parse_prompts_markdown(args.prompts)
    if not slides:
        print(json.dumps({"error": True, "message": "No slides found in prompts file."}))
        sys.exit(1)

    model = args.model or DEFAULT_MODEL
    resolution = args.resolution or DEFAULT_RESOLUTION
    cost_per = PRICING.get(model, PRICING[DEFAULT_MODEL]).get(resolution, 0.078)
    total = round(cost_per * len(slides), 3)

    print(f"Slides found: {len(slides)}")
    print(f"Model: {model}")
    print(f"Resolution: {resolution}")
    print(f"Cost per slide: ${cost_per:.3f}")
    print(f"Total estimate: ${total:.3f}")
    print()
    for s in slides:
        print(f"  Slide {s['number']}: {s['name']}")


def cmd_template(args):
    """Output a template prompts markdown file."""
    template = """# Slide Prompts — [Project Name]

**Brand preset:** [preset-name]
**Format:** 16:9, 4K
**Generated:** [date]

---

## Slide 01 — Title Slide
```
A dark premium presentation slide background in pure black with generous
clean negative space in the upper half and center. A subtle geometric
network pattern of connected silver nodes and thin lines at 30% opacity
in the lower-right quadrant. Simple uncluttered lower-left corner.
16:9 widescreen, 4K resolution. NO text, NO logos, NO labels.
Premium keynote aesthetic.
```

## Slide 02 — Section Divider
```
A widescreen slide background with a smooth gradient sweep from rich
gold (#FFC000) at the top transitioning to deep amber and dark charcoal
at the bottom. A faint geometric dot grid at 20% opacity across the
surface. Large open areas of clean gradient. 16:9 format, 4K resolution.
NO text, NO logos, NO labels. Premium corporate keynote background.
```

## Slide 03 — Content Slide
```
A dark charcoal slide background with subtle silver geometric network
pattern at 15% opacity concentrated in the upper-right corner. The
majority of the slide is clean dark space for content overlay. Warm
golden accent light from the left edge creates a subtle glow. 16:9
widescreen, 4K resolution. NO text, NO logos, NO labels. Clean
professional presentation aesthetic.
```
"""
    output_path = Path(args.output).resolve() if args.output else Path("slide-prompts-template.md")
    with open(output_path, "w") as f:
        f.write(template)
    print(f"Template saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Banana Claude Slide Deck Pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="Generate slide images from prompts markdown")
    p_gen.add_argument("--prompts", required=True, help="Path to prompts markdown file")
    p_gen.add_argument("--output", help="Output directory (default: ~/Documents/nanobanana_generated/slides_TIMESTAMP/)")
    p_gen.add_argument("--model", default=None, help=f"Model ID (default: {DEFAULT_MODEL})")
    p_gen.add_argument("--resolution", default=None, help=f"Resolution (default: {DEFAULT_RESOLUTION})")
    p_gen.add_argument("--ratio", default=None, help=f"Aspect ratio (default: {DEFAULT_RATIO})")
    p_gen.add_argument("--mode", choices=["complete", "background", "both"], default=None,
                        help="Generation mode: complete (with text), background (no text), or both")
    p_gen.add_argument("--api-key", default=None, help="Google AI API key")

    # estimate
    p_est = sub.add_parser("estimate", help="Estimate cost without generating")
    p_est.add_argument("--prompts", required=True, help="Path to prompts markdown file")
    p_est.add_argument("--model", default=None, help=f"Model ID (default: {DEFAULT_MODEL})")
    p_est.add_argument("--resolution", default=None, help=f"Resolution (default: {DEFAULT_RESOLUTION})")

    # template
    p_tpl = sub.add_parser("template", help="Output a template prompts markdown file")
    p_tpl.add_argument("--output", default=None, help="Output path (default: slide-prompts-template.md)")

    args = parser.parse_args()
    cmds = {"generate": cmd_generate, "estimate": cmd_estimate, "template": cmd_template}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
