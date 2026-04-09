# Multi-Format Output Reference

> Load this when the user runs `/banana formats` or asks to convert an image
> to multiple formats or sizes.

## Overview

Generate an image once at max resolution, then convert to multiple formats and sizes using ImageMagick. One API call, many output files.

## Usage

```bash
# Convert to multiple formats and sizes
python3 ${CLAUDE_SKILL_DIR}/scripts/multiformat.py convert --input PATH --formats png,webp,jpeg --sizes 4k,2k,1k

# Get image dimensions and format info
python3 ${CLAUDE_SKILL_DIR}/scripts/multiformat.py info --input PATH
```

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PNG | `.png` | Lossless, supports transparency, largest files |
| WebP | `.webp` | Lossy/lossless, 25-35% smaller than PNG, wide browser support |
| JPEG | `.jpg` | Lossy, no transparency (alpha flattened to white), smallest files |

## Size Tiers

| Tier | 16:9 | 1:1 | 4:5 | 9:16 |
|------|------|-----|-----|------|
| 4K | 3840x2160 | 3840x3840 | 3072x3840 | 2160x3840 |
| 2K | 2560x1440 | 2560x2560 | 2048x2560 | 1440x2560 |
| 1K | 1920x1080 | 1080x1080 | 864x1080 | 1080x1920 |
| 512 | 910x512 | 512x512 | 410x512 | 512x910 |

The script detects the source image's aspect ratio and uses the correct pixel dimensions for each size tier.

## Quality Settings

Default quality: 85 (adjustable via `--quality`).
- PNG: quality flag ignored (lossless)
- WebP: 85 = good balance of size and quality
- JPEG: 85-90 recommended for print/web

## Prerequisites

Requires ImageMagick. The script checks for `magick` (v7) first, falls back to `convert` (v6).

```bash
# macOS
brew install imagemagick

# Ubuntu/Debian
sudo apt install imagemagick
```

## Output Structure

```
~/Documents/nanobanana_generated/multiformat_TIMESTAMP/
    image-4k.png
    image-4k.webp
    image-4k.jpg
    image-2k.png
    image-2k.webp
    image-2k.jpg
    image-1k.png
    image-1k.webp
    image-1k.jpg
    manifest.json
```

The `manifest.json` lists all outputs with paths, dimensions, and file sizes — useful for downstream tools like the content pipeline.
