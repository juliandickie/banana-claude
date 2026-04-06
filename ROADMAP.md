# Banana Claude: Expansion Roadmap

## Context

Banana Claude v1.5.0 is a comprehensive Creative Director skill for AI image generation. This roadmap captures planned features, organized by implementation priority.

**Architecture note:** As this grows, the skill should split into three interlinked skills:
1. **Brand Learning** (`/banana brand`) — Brand guide creation, asset registry, presets
2. **Image Generation** (`/banana`, `/banana generate`, `/banana slides`, `/banana social`) — The current core, images only
3. **Video Generation** (`/banana video`) — VEO 3.1 integration, separate skill with shared brand/asset system

These would share the brand preset system and asset registry but have their own domain modes, prompt engineering, and output pipelines.

---

## Tier 1: High Priority (Next to build)

### 1.1 — `/banana slides` — Batch Slide Deck Pipeline

Automates a current manual 3-step, 2-session workflow into a single skill command.

**Current manual process:**
1. User gives Claude transcripts → Claude writes a detailed visual design brief (markdown)
2. User takes the brief to a new session → Claude writes Nano Banana Pro prompts
3. Team manually copies/pastes each prompt to generate images one at a time

**Automated pipeline:**

```
/banana slides plan --content ~/transcripts/chapter-16/ --preset avant-garde
# → ch16-slide-plan.md (design brief with slide concepts)

/banana slides prompts --plan ch16-slide-plan.md
# → ch16-prompts.md (image prompts for each slide)

/banana slides generate --prompts ch16-prompts.md --output ~/slides/ch16/
# → Generates all images in batch, saves numbered PNGs
```

**Or all at once:**
```
/banana slides --content ~/transcripts/chapter-16/ --preset avant-garde --output ~/slides/ch16/
```

**Slide plan depth:** Each slide entry is a full creative brief:

```markdown
## Slide 03 — Common Issue: Incorrect Bite Registration
**Timestamp:** 00:00:33 - 00:01:07
**Transcript Reference:**
> "Sometimes we are finding that the bite just looks wrong..."

**Background Style:** Style B (Gold Gradient)
**Slide Type:** content (diagnostic comparison)

**Design Concept:**
A clinical diagnostic image showing the bite registration challenge.
Two digital dental arch models displayed as 3D renders — one misaligned
with amber warning indicators, one correctly articulated with gold
checkmarks. Gold gradient background. Annotation arrows guide the eye.

**Visual Elements:**
- Two 3D dental arch models (misaligned vs. correct)
- Amber warning indicators / gold checkmarks
- Diagnostic arrows and highlight zones
- Gold gradient background, premium infographic style

**Intended Message:** Verify the bite, don't assume it.
```

**Output modes:** Both Complete Slide (text rendered) and Background Only (for Keynote/PPT layering).

### 1.2 — `/banana brand` — Conversational Brand Guide Builder

A single conversational flow that starts by learning from existing sources, then refines interactively.

**Phase 1 — Gather Sources:**
- "Got a website URL?" → Claude visits with browser tools, scans multiple pages
- "A brand guidelines PDF?" → Claude reads the file
- "Reference images or mood board?" → Claude analyzes visual patterns
- "Start from scratch?" → Skips to Phase 3

**Phase 2 — Auto-Extract:**
Colors, typography, lighting, mood, style, visual motifs, do's/don'ts — from whatever sources were provided.

**Phase 3 — Show & Refine:**
Claude presents what it found, asks targeted questions about gaps (background styles, logo placement, what to avoid), user confirms or adjusts.

**Phase 4 — Preview & Save:**
Generate a sample image in the brand style. If approved → save preset. If not → refine and regenerate.

### 1.3 — Pre-Built Brand Style Guide Library

Ship example brand guide JSON files as templates:
- `tech-saas.json` — Clean, blue, modern
- `luxury-dark.json` — Black + gold, dramatic
- `organic-natural.json` — Warm earthy tones
- `startup-bold.json` — High contrast, energetic
- `corporate-professional.json` — Navy + white, trustworthy
- `creative-agency.json` — Bold, experimental

Users copy one, customize, and have instant brand consistency.

### 1.4 — `/banana social` — Platform-Native Generation

Generate separate images AT the correct ratio for each platform. Not cropping — each image is natively composed with platform-aware negative space.

```
/banana social "product shot for wireless earbuds" --platforms instagram-feed,youtube-thumb,linkedin
```

| Platform | Ratio | Resolution | Negative Space Notes |
|----------|-------|-----------|---------------------|
| YouTube thumbnail | 16:9 | 4K (3840×2160) | Right 40% clear for title |
| Instagram feed | 1:1 | 4K (4096×4096) | Center-weighted subject |
| Instagram story | 9:16 | 4K (3072×5504) | Top 15% + bottom 20% clear for UI |
| LinkedIn post | 4:3 | 4K (4608×3456) | Lower third clear for headline |
| Twitter/X header | 4:1 | 2K (4096×1024) | Center subject, edges croppable |
| Pinterest pin | 2:3 | 4K (3072×4608) | Top third for text overlay |

**Text option (same as slides):** Complete (2-3 word text rendered by model) or Image Only (clean for overlay). Both saved, or user picks one.

**Expandable to ads:** Google Display, Meta Ads, programmatic banners — same approach.

---

## Tier 2: Medium Priority (Valuable, more effort)

### 2.1 — Asset Registry: Persistent Characters, Products & Objects

Save named references with images and descriptions for reuse across sessions:

```
/banana asset create "iTero Scanner" --type product --reference ~/photos/itero.jpg \
  --description "Handheld intraoral scanner, white and gray, ergonomic grip, LED ring"
```

Then: `/banana generate "Alex scanning a patient with the iTero Scanner"`

Types: characters (people), products (your products for e-commerce/UGC), equipment (tools, devices), environments (recurring settings).

Storage: `~/.banana/assets/NAME.json` with `name`, `type`, `description`, `reference_images[]`, `default_context`, `consistency_notes`.

### 2.2 — `/banana video` — Video Generation with VEO 3.1

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

### 2.3 — Smart A/B Testing with Prompt Variations

Expand Literal/Creative/Premium variations into a feedback framework:

```
/banana ab-test "landing page hero for fintech app" --count 3
```

Generate all three, display with prompts, let user rate. Over time, learn which patterns work best.

### 2.4 — Image-to-Prompt Reverse Engineering

Upload an image, get the 5-Component Formula prompt that would recreate it:

```
/banana reverse ~/photos/inspiration.jpg
```

Uses `gemini_chat` with the image to analyze and output a structured prompt.

### 2.5 — Session History with Visual Gallery

`/banana history` shows all generations in the current session with prompts, settings, and file paths.

### 2.6 — Multi-Format Output

Generate once, output in multiple formats:

```
/banana generate "hero image" --output-formats png,webp --output-sizes 4k,2k,1k
```

---

## Tier 3: Ambitious (Larger projects)

### 3.1 — Presentation Deck Builder (.pptx)

Generate slide backgrounds AND produce an actual editable `.pptx` file with:
- Generated backgrounds as slide images
- Text layers with proper hierarchy
- Logo placed per brand guide
- Notes section with prompts used

### 3.2 — Visual Brand Book Generator

From a brand preset, generate a complete visual brand book (PDF):
- Color palette, typography specimens, photography style samples
- Do's/don'ts with visual examples
- Social media and slide templates

### 3.3 — Multi-Modal Content Pipeline

```
/banana content "product launch" --preset brand --outputs hero,social-pack,email-header,deck
```

### 3.4 — Analytics Dashboard

Local web dashboard showing cost trends, domain mode usage, quota monitoring.

### 3.5 — Team Collaboration: Shared Presets via Git

Share brand guides and prompt templates across a team via a shared git repo.

---

## Future Considerations

- **Figma Plugin Bridge** — Export to Figma frames via API
- **CMS Integration** — Auto-upload to WordPress, Contentful, Sanity
- **E-Commerce Automation** — Connect to Shopify/WooCommerce for product shots
- **3D Object Generation** — When model support exists
- **Interactive Prototypes** — Generate clickable UI mockups

---

## Priority Summary

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | `/banana slides` pipeline | Medium | Very High |
| 2 | `/banana brand` conversational builder | Medium | Very High |
| 3 | Pre-built brand guide library | Low | High |
| 4 | `/banana social` platform-native gen | Medium | High |
| 5 | Asset registry (people + products + objects) | Medium | High |
| 6 | `/banana video` with VEO 3.1 (separate skill) | Medium | Very High |
| 7 | Image-to-prompt reverse | Medium | High |
| 8 | Deck builder (.pptx output) | Medium | Very High |
| 9 | Visual brand book | Medium | High |
| 10 | Analytics dashboard | Medium | Medium |
