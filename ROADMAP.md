# Nano Banana Studio: Expansion Roadmap

## Context

Nano Banana Studio v2.1.0 is a comprehensive Creative Director plugin for AI image generation. This roadmap captures planned features, organized by implementation priority.

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

### Deck Builder (.pptx Output)

Generate slide backgrounds AND produce an actual editable `.pptx` file with:
- Generated backgrounds as slide images
- Text layers with proper hierarchy
- Logo placed per brand guide
- Notes section with prompts used

### Smart A/B Testing with Prompt Variations

Expand Literal/Creative/Premium variations into a feedback framework:

```
/banana ab-test "landing page hero for fintech app" --count 3
```

Generate all three, display with prompts, let user rate. Over time, learn which patterns work best.

### Session History with Visual Gallery

`/banana history` shows all generations in the current session with prompts, settings, and file paths.

### Multi-Format Output

Generate once, output in multiple formats:

```
/banana generate "hero image" --output-formats png,webp --output-sizes 4k,2k,1k
```

### Analytics Dashboard

Local web dashboard showing cost trends, domain mode usage, quota monitoring.

### Multi-Modal Content Pipeline

```
/banana content "product launch" --preset brand --outputs hero,social-pack,email-header,deck
```

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
| 1 | `/banana video` with VEO 3.1 | Medium | Very High | Next |
| 2 | Deck builder (.pptx output) | Medium | Very High | Planned |
| 3 | A/B testing with prompt variations | Low | Medium | Planned |
| 4 | Session history gallery | Low | Medium | Planned |
| 5 | Multi-format output | Low | Medium | Planned |
| 6 | Analytics dashboard | Medium | Medium | Future |
| 7 | Multi-modal content pipeline | High | High | Future |
