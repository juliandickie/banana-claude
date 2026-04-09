# Nano Banana Studio: Expansion Roadmap

## Context

Nano Banana Studio v3.1.0 is a comprehensive Creative Director plugin for AI image generation. This roadmap captures planned features, organized by implementation priority.

**Architecture note:** As this grows, the skill should split into three interlinked skills:
1. **Brand Learning** (`/banana brand`) — Brand guide creation, asset registry, presets
2. **Image Generation** (`/banana`, `/banana generate`, `/banana slides`, `/banana social`) — The current core, images only
3. **Video Generation** (`/banana video`) — VEO 3.1 integration, separate skill with shared brand/asset system

These would share the brand preset system and asset registry but have their own domain modes, prompt engineering, and output pipelines.

---

## Completed Features

| # | Feature | Version | Notes |
|---|---------|---------|-------|
| 1 | `/banana slides` — batch slide deck pipeline | v1.6.0 | plan → prompts → generate workflow |
| 2 | `/banana brand` — conversational brand guide builder | v1.7.0 | learn → extract → refine → preview → save |
| 3 | Pre-built brand guide library (12 presets) | v1.7.0 | tech-saas, luxury-dark, organic-natural, etc. |
| 4 | `/banana social` — platform-native generation | v1.7.0 | 46 platforms, ratio grouping, 4K + auto-crop |
| 5 | `/banana asset` — persistent asset registry | v1.8.0 | characters, products, equipment, environments |
| 6 | `/banana reverse` — image-to-prompt reverse engineering | v1.9.0 | Claude vs Gemini perspectives + blended prompt |
| 7 | `/banana book` — visual brand book generator | v2.0.0 | markdown + pptx + html, 3 tiers, Pantone colors |
| 8 | `/banana formats` — multi-format image converter | v2.2.0 | PNG/WebP/JPEG at 4K/2K/1K/512, sips fallback |
| 9 | `/banana history` — session generation history | v2.3.0 | log, list, export as markdown gallery |
| 10 | `/banana ab-test` — A/B prompt variation testing | v2.4.0 | Literal/Creative/Premium + preference learning |
| 11 | `/banana deck` — slide deck builder | v2.5.0 | .pptx with 3 layouts, brand styling, logo placement |
| 12 | `/banana analytics` — analytics dashboard | v2.6.0 | HTML with SVG charts, cost/usage/quota |
| 13 | `/banana content` — multi-modal content pipeline | v2.7.0 | hero + social + email + formats orchestration |
| 14 | `/video` — VEO 3.1 video generation (core) | v3.0.0 | Text-to-video, image-to-video, first/last frame |

---

## Next Up

### `/banana video` — Video Generation with VEO 3.1

VEO 3.1 (`veo-3.1-generate-preview`) is live and uses the same Google AI API key.

- Text-to-video and image-to-video (animate a generated image)
- 4-8 second clips at 24fps, up to 4K resolution
- Built-in audio generation (dialogue, sound effects, ambient)
- 16:9 and 9:16, reference images (up to 3), video extension (up to 141s)

**Should be a separate skill** that shares brand presets and asset registry with the image generation skill.

```
/banana video "product reveal of the iTero Scanner rotating on dark surface"
/banana video --from ~/slides/slide-03.png "animate the dental arch models"
```

Implementation: `video_generate.py` (stdlib-only, same pattern), `/banana video` skill file.

---

## Planned Features

---

## Future Considerations

- **Figma Plugin Bridge** — Export to Figma frames via API
- **CMS Integration** — Auto-upload to WordPress, Contentful, Sanity
- **E-Commerce Automation** — Connect to Shopify/WooCommerce for product shots
- **3D Object Generation** — When model support exists
- **Interactive Prototypes** — Generate clickable UI mockups
- **Team Collaboration** — Shared presets via git repo

---

## Priority Summary

| # | Feature | Effort | Impact | Status |
|---|---------|--------|--------|--------|
| 1 | `/video` sequence production (storyboard, multi-shot) | Medium | Very High | Next |
| 2 | `/video extend` + `/video stitch` | Low | Medium | Planned |
