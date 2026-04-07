# Social Media Platform Specifications

Reference for generating platform-optimized images from a single prompt.

## Generation Strategy

1. **Generate at the nearest Nano Banana native ratio at 4K resolution** -- this avoids distortion and maximizes quality.
2. **Crop to exact platform pixels** using ImageMagick `convert -gravity center -crop WxH+0+0 +repage`.
3. **Save both versions** -- the uncropped original (reusable across platforms sharing the same ratio) and the cropped platform-specific file.

## Output Modes

| Mode | Flag | Description |
|------|------|-------------|
| Complete | `--mode complete` | Full image with text overlays baked in (hero banners, ads with CTA) |
| Image Only | `--mode image-only` | Clean image, no text -- for posts where text is added in-app or via design tool |

Image Only is the default. Use Complete when the platform placement expects a finished visual (ads, covers).

---

## Nano Banana 2 Native Ratios

```
1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, 1:4, 4:1, 1:8, 8:1
```

---

## Platform Specifications

### Instagram

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed Portrait | 1080x1350 | 4:5 | 4:5 | 3200x4000 | Keep subject centered; bottom 20% may be cropped by caption overlay |
| Feed Square | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Center subject; edges may clip on older devices |
| Feed Landscape | 1080x566 | ~1.91:1 | 16:9 | 4096x2304 | Crop top/bottom from 16:9; avoid key content in extreme top/bottom |
| Story / Reel | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Top 15% and bottom 25% obscured by UI (username, CTA buttons) |
| Reel Cover | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Center of frame is the visible thumbnail; edges heavily cropped in grid view |
| Profile Picture | 320x320 | 1:1 | 1:1 | 4096x4096 | Circular crop -- keep subject in center 70% |

### Facebook

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed Square | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Center subject |
| Feed Landscape | 1200x630 | ~1.91:1 | 16:9 | 4096x2304 | Crop from 16:9; link preview crops tighter |
| Feed Portrait | 1080x1350 | 4:5 | 4:5 | 3200x4000 | Truncated in feed with "See More" -- put hook in top 60% |
| Story / Reel | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Top 14% is profile bar; bottom 20% is CTA area |
| Cover Photo | 820x312 | ~2.63:1 | 21:9 | 4096x1756 | Crop from 21:9; mobile crops to ~640x360, keep subject in center band |
| Feed Ad | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Bottom 20% overlaid with ad copy |
| Story Ad | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Bottom 25% is CTA button area |

### YouTube

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Thumbnail | 1280x720 | 16:9 | 16:9 | 4096x2304 | Bottom-right corner often has timestamp overlay; avoid text there |
| Channel Banner | 2560x1440 | 16:9 | 16:9 | 4096x2304 | Safe area is center 1546x423 on desktop; TV shows full image |
| Shorts Thumbnail | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Center subject; top/bottom cropped in browse view |

### LinkedIn

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed Landscape | 1200x627 | ~1.91:1 | 16:9 | 4096x2304 | Standard share image; crops from 16:9 |
| Feed Portrait | 1080x1350 | 4:5 | 4:5 | 3200x4000 | Truncated in feed; top portion is most visible |
| Feed Square | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Safe choice for LinkedIn |
| Banner / Hero | 1584x396 | 4:1 | 4:1 | 4096x1024 | Exactly 4:1 native; subject in center band |
| Carousel Slide | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Keep margins; swipe arrows overlay edges |
| Carousel Slide (Portrait) | 1080x1350 | 4:5 | 4:5 | 3200x4000 | More vertical real estate for carousels |
| Sponsored Content Ad | 1200x627 | ~1.91:1 | 16:9 | 4096x2304 | Same as feed landscape |

### Twitter / X

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed Landscape | 1600x900 | 16:9 | 16:9 | 4096x2304 | Standard in-feed image; crops from center on mobile |
| Feed Square | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Displayed with slight letterboxing |
| Header / Banner | 1500x500 | 3:1 | 3:2 | 4096x2731 | Crop from 3:2 (heavy top/bottom crop); keep subject in narrow center band |
| In-Feed Ad | 1600x900 | 16:9 | 16:9 | 4096x2304 | Bottom may have ad label overlay |

### TikTok

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed / Video Cover | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Bottom 25% has caption/music overlay; top 10% has following/search |
| In-Feed Ad | 1080x1920 | 9:16 | 9:16 | 2304x4096 | CTA button in bottom 20%; keep subject in center 50% |

### Pinterest

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Standard Pin | 1000x1500 | 2:3 | 2:3 | 2731x4096 | Optimal ratio for Pinterest grid; bottom may show title overlay |
| Long Pin | 1000x2100 | ~1:2.1 | 1:4 | 1024x4096 | Crop from 1:4; tall pins get more grid space but may be truncated |
| Square Pin | 1000x1000 | 1:1 | 1:1 | 4096x4096 | Less grid presence than portrait but cleaner crop |

### Threads

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Feed Portrait | 1080x1350 | 4:5 | 4:5 | 3200x4000 | Same as Instagram feed portrait |
| Feed Vertical | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Full vertical; bottom has interaction bar |
| Feed Square | 1080x1080 | 1:1 | 1:1 | 4096x4096 | Safe default |

### Snapchat

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Story | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Top 15% has header bar; bottom 20% has swipe-up/reply |
| Snap Ad | 1080x1920 | 9:16 | 9:16 | 2304x4096 | Bottom 30% is CTA; keep subject in upper 60% |

### Google Ads

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Responsive Landscape | 1200x628 | ~1.91:1 | 16:9 | 4096x2304 | Crop from 16:9; Google may auto-crop further |
| Responsive Square | 1200x1200 | 1:1 | 1:1 | 4096x4096 | Center subject; ad text overlaid below |
| Display Leaderboard | 728x90 | ~8:1 | 8:1 | 4096x512 | Extreme horizontal; use for patterns/textures or simple centered subject |
| Display Skyscraper | 160x600 | ~1:3.75 | 1:4 | 1024x4096 | Crop from 1:4; narrow vertical -- text must be large |
| Display Half-Page | 300x600 | 1:2 | 1:4 | 1024x4096 | Crop from 1:4; keep subject in upper half |
| Display Rectangle | 300x250 | 6:5 | 5:4 | 4096x3277 | Crop from 5:4; compact format, center everything |
| Performance Max | 1200x628 | ~1.91:1 | 16:9 | 4096x2304 | Same as responsive landscape; Google auto-crops aggressively |

### Spotify

| Placement | Pixels | Ratio | Nearest Native Ratio | Generate At | Negative Space Notes |
|-----------|--------|-------|----------------------|-------------|----------------------|
| Playlist / Album Cover | 3000x3000 | 1:1 | 1:1 | 4096x4096 | Circular crop on some views; keep subject in center 80% |
| Artist Banner | 2660x1140 | ~2.33:1 | 21:9 | 4096x1756 | Crop from 21:9; text overlays on left side |

---

## Cropping Commands (ImageMagick)

After generating at the native ratio, crop to exact platform pixels:

```bash
# Basic center crop
convert input.png -gravity center -crop WIDTHxHEIGHT+0+0 +repage output.png

# Examples
convert original_16x9.png -gravity center -crop 1280x720+0+0 +repage youtube_thumb.png
convert original_4x5.png -gravity center -crop 1080x1350+0+0 +repage ig_feed.png
convert original_9x16.png -gravity center -crop 1080x1920+0+0 +repage ig_story.png
convert original_1x1.png -gravity center -crop 1080x1080+0+0 +repage ig_square.png
convert original_21x9.png -gravity center -crop 820x312+0+0 +repage fb_cover.png
convert original_4x1.png -gravity center -crop 1584x396+0+0 +repage linkedin_banner.png
convert original_8x1.png -gravity center -crop 728x90+0+0 +repage google_leaderboard.png

# Resize then crop (when generated image is larger than needed)
convert input.png -resize WIDTHxHEIGHT^ -gravity center -crop WIDTHxHEIGHT+0+0 +repage output.png
```

---

## Platform Shorthand Names

Use these shorthands with the `--platforms` flag in `social.py`:

| Shorthand | Platform & Placement |
|-----------|---------------------|
| `ig-feed` | Instagram Feed Portrait (1080x1350) |
| `ig-square` | Instagram Feed Square (1080x1080) |
| `ig-landscape` | Instagram Feed Landscape (1080x566) |
| `ig-story` | Instagram Story / Reel (1080x1920) |
| `ig-reel-cover` | Instagram Reel Cover (1080x1920) |
| `ig-profile` | Instagram Profile Picture (320x320) |
| `fb-feed` | Facebook Feed Square (1080x1080) |
| `fb-landscape` | Facebook Feed Landscape (1200x630) |
| `fb-portrait` | Facebook Feed Portrait (1080x1350) |
| `fb-story` | Facebook Story / Reel (1080x1920) |
| `fb-cover` | Facebook Cover Photo (820x312) |
| `fb-ad` | Facebook Feed Ad (1080x1080) |
| `fb-story-ad` | Facebook Story Ad (1080x1920) |
| `yt-thumb` | YouTube Thumbnail (1280x720) |
| `yt-banner` | YouTube Channel Banner (2560x1440) |
| `yt-shorts` | YouTube Shorts Thumbnail (1080x1920) |
| `li-landscape` | LinkedIn Feed Landscape (1200x627) |
| `li-portrait` | LinkedIn Feed Portrait (1080x1350) |
| `li-square` | LinkedIn Feed Square (1080x1080) |
| `li-banner` | LinkedIn Banner (1584x396) |
| `li-carousel` | LinkedIn Carousel Slide (1080x1080) |
| `li-carousel-portrait` | LinkedIn Carousel Portrait (1080x1350) |
| `li-ad` | LinkedIn Sponsored Content (1200x627) |
| `x-landscape` | Twitter/X Feed Landscape (1600x900) |
| `x-square` | Twitter/X Feed Square (1080x1080) |
| `x-header` | Twitter/X Header (1500x500) |
| `x-ad` | Twitter/X In-Feed Ad (1600x900) |
| `tt-feed` | TikTok Feed / Cover (1080x1920) |
| `tt-ad` | TikTok In-Feed Ad (1080x1920) |
| `pin-standard` | Pinterest Standard Pin (1000x1500) |
| `pin-long` | Pinterest Long Pin (1000x2100) |
| `pin-square` | Pinterest Square Pin (1000x1000) |
| `threads-portrait` | Threads Feed Portrait (1080x1350) |
| `threads-vertical` | Threads Feed Vertical (1080x1920) |
| `threads-square` | Threads Feed Square (1080x1080) |
| `snap-story` | Snapchat Story (1080x1920) |
| `snap-ad` | Snapchat Ad (1080x1920) |
| `gads-landscape` | Google Ads Responsive Landscape (1200x628) |
| `gads-square` | Google Ads Responsive Square (1200x1200) |
| `gads-leaderboard` | Google Ads Display Leaderboard (728x90) |
| `gads-skyscraper` | Google Ads Display Skyscraper (160x600) |
| `gads-half-page` | Google Ads Display Half-Page (300x600) |
| `gads-rectangle` | Google Ads Display Rectangle (300x250) |
| `gads-pmax` | Google Ads Performance Max (1200x628) |
| `spotify-cover` | Spotify Playlist/Album Cover (3000x3000) |
| `spotify-banner` | Spotify Artist Banner (2660x1140) |

### Group Shorthands

| Shorthand | Expands To |
|-----------|-----------|
| `instagram` | `ig-feed,ig-square,ig-story` |
| `facebook` | `fb-feed,fb-landscape,fb-story` |
| `youtube` | `yt-thumb,yt-banner` |
| `linkedin` | `li-landscape,li-square,li-banner` |
| `twitter` | `x-landscape,x-header` |
| `tiktok` | `tt-feed` |
| `pinterest` | `pin-standard` |
| `threads` | `threads-portrait,threads-square` |
| `snapchat` | `snap-story` |
| `google-ads` | `gads-landscape,gads-square` |
| `spotify` | `spotify-cover` |
| `all-feeds` | `ig-feed,fb-feed,li-landscape,x-landscape,threads-portrait` |
| `all-stories` | `ig-story,fb-story,snap-story,tt-feed` |
| `all-ads` | `fb-ad,fb-story-ad,li-ad,x-ad,tt-ad,gads-landscape,gads-square,snap-ad` |
