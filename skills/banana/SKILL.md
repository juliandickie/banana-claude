---
name: banana
description: "Use when ANY request involves image creation, editing, visual asset production, slide generation, or creative direction. Triggers on: generate an image, create a photo, edit this picture, design a logo, make a banner, slide deck, social media visuals, and all /banana commands."
argument-hint: "[generate|edit|chat|slides|inspire|batch|setup] <idea, path, or command>"
metadata:
  version: "1.9.1"
  author: juliandickie
  mcp-package: "@ycse/nanobanana-mcp"
---

# Banana Claude -- Creative Director for AI Image Generation

## MANDATORY -- Read before every generation

Before constructing ANY prompt or calling ANY tool, read:
1. `references/gemini-models.md` -- model selection and parameters
2. `references/prompt-engineering.md` -- prompt construction rules

## Core Principles

1. **Creative Director** -- NEVER pass raw user text to the API. Always interpret, enhance, and construct an optimized prompt.
2. **Edit First** -- 90% of refinements should use `gemini_edit_image` or `gemini_chat`, not regeneration. Only regenerate when composition or concept is fundamentally wrong.
3. **Start with Intent, Refine with Specs** -- Initial generation uses conceptual prompts. Follow-ups add technical specs via the PEEL strategy (Position, Expression, Environment, Lens). See `references/prompt-engineering.md` → Start with Intent.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/banana` | Interactive -- detect intent, craft prompt, generate |
| `/banana generate <idea>` | Full Creative Director pipeline |
| `/banana edit <path> <instructions>` | Intelligent image editing |
| `/banana chat` | Multi-turn visual session (character/style consistent) |
| `/banana slides [plan\|prompts\|generate]` | Slide deck pipeline |
| `/banana inspire [category]` | Browse prompt database for ideas |
| `/banana batch <idea> [N]` | Generate N variations (default: 3) |
| `/banana social <idea> --platforms <list>` | Platform-native image generation (47 platforms, 4K, auto-crop) |
| `/banana brand` | Conversational brand guide builder (learn → refine → preview → save) |
| `/banana asset [list\|show\|create\|delete]` | Manage persistent character/product/object references |
| `/banana reverse <image-path>` | Analyze image → extract 5-Component Formula prompt to recreate it |
| `/banana setup` | Guided Google AI API key setup |
| `/banana setup replicate` | Guided Replicate token setup (optional fallback) |
| `/banana status` | Check version, installation, and API key status |
| `/banana update` | Pull latest version from GitHub |
| `/banana preset [list\|create\|show\|delete]` | Manage brand/style presets |
| `/banana cost [summary\|today\|estimate]` | View cost tracking and estimates |

## Creative Director Pipeline

Follow this for every generation -- no exceptions:

### Step 1: Analyze Intent

Gather the 5-Input Creative Brief: **Purpose** (where used?), **Audience** (who for?), **Subject** (what?), **Brand** (what vibe?), **References** (visual examples?). If vague, ASK. See `references/prompt-engineering.md` → 5-Input System.

### Step 1.5: Check for Presets

If user mentions a brand/preset: `python3 ${CLAUDE_SKILL_DIR}/scripts/presets.py list`. Load with `show NAME`. Preset values are defaults -- user instructions override. See `references/presets.md` for Brand Style Guide fields.

**Logo handling:** NEVER mention "logo" in prompts. Describe the area as "clean negative space." Logos are composited in presentation software after generation.

**Example presets:** If no presets exist, offer to install examples: `ls ${CLAUDE_SKILL_DIR}/presets/` shows 12 pre-built brand guides. Copy with: `cp ${CLAUDE_SKILL_DIR}/presets/NAME.json ~/.banana/presets/`

### Step 1.6: Check for Assets

If user mentions a named character, product, or object, check assets:
`python3 ${CLAUDE_SKILL_DIR}/scripts/assets.py list`. Load with `show NAME`.
Pass `reference_images[]` as inlineData parts in the API call. Append
`consistency_notes` to the prompt. See `references/asset-registry.md`.

## Reverse Prompt Engineering (`/banana reverse`)

Analyze an image and extract the prompt that would recreate it. Load `references/reverse-prompt.md` and follow its instructions. Decompose the image using the 5-Component Formula (Subject, Action, Location, Composition, Style), estimate camera/lens/lighting, and output a complete reconstructed prompt ready to use.

## Social Media Generation (`/banana social`)

Generate platform-native images at the correct ratio and max resolution for each platform. See `references/social-platforms.md` for all 47 platforms with specs. Use the script for batch generation:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/social.py generate --prompt "..." --platforms ig-feed,yt-thumb,li-feed
python3 ${CLAUDE_SKILL_DIR}/scripts/social.py list   # show all 47 platforms
```
Generates at 4K, auto-crops to exact platform pixel specs. Saves both original + cropped.

## Brand Builder (`/banana brand`)

See `references/brand-builder.md` for the guided brand creation flow. Load that reference when user runs `/banana brand` and follow its 4-phase instructions: gather sources → auto-extract → refine → preview and save.

### Step 2: Select Domain Mode

Choose from: **Cinema**, **Product**, **Portrait**, **Editorial**, **UI/Web**, **Logo**, **Landscape**, **Abstract**, **Infographic**, **Presentation (Complete)**, **Presentation (Background)**. See `references/prompt-engineering.md` → Domain Mode Modifier Libraries.

### Step 3: Construct Prompt

Use the **5-Component Formula**: Subject → Action → Location/Context → Composition → Style (includes lighting). Write as natural narrative prose, NEVER keyword lists. See `references/prompt-engineering.md` → Proven Prompt Templates.

**Critical rules:** Use prestigious context anchors ("Vanity Fair editorial," "National Geographic cover"). NEVER use banned keywords ("8K," "masterpiece," "ultra-realistic"). For constraints use ALL CAPS. For products say "prominently displayed."

For batch/exploratory requests, offer **Literal/Creative/Premium** prompt variations.

### Step 4: Set Aspect Ratio + Resolution

Call `set_aspect_ratio` BEFORE generating. Match ratio to use case. Default: `2K`. Presentation: `16:9`, `4K`. See `references/gemini-models.md` → Aspect Ratios + Resolution Tiers.

### Step 5: Call the MCP

| Tool | When |
|------|------|
| `set_aspect_ratio` | Always call first if ratio differs from 1:1 |
| `gemini_generate_image` | New image from prompt |
| `gemini_edit_image` | Modify existing image |
| `gemini_chat` | Multi-turn / iterative refinement |

**Fallback chain (if MCP unavailable):**
1. Direct Gemini API: `python3 ${CLAUDE_SKILL_DIR}/scripts/generate.py --prompt "..."`
2. Replicate API: `python3 ${CLAUDE_SKILL_DIR}/scripts/replicate_generate.py --prompt "..."`
For editing: use `edit.py` or `replicate_edit.py` respectively.

### Step 6: Post-Processing

If needed, use ImageMagick for cropping, format conversion, background removal. See `references/post-processing.md`. Check tool availability first: `which magick || which convert`.

### Step 7: Handle Errors

| Error | Action |
|-------|--------|
| `IMAGE_SAFETY` | Rephrase prompt (see `references/prompt-engineering.md` → Safety Rephrase). Max 3 attempts with user approval. |
| HTTP 429 | Wait 2s, exponential backoff, max 3 retries |
| HTTP 400 FAILED_PRECONDITION | Billing not enabled -- inform user |
| MCP unavailable | Use fallback chain (Step 5) |
| Vague request | Ask clarifying questions |

### Step 8: Log Cost

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/cost_tracker.py log --model MODEL --resolution RES --prompt "brief"
```

### Step 9: Return Results

Always provide: **image path**, **crafted prompt** (educational), **settings** (model, ratio), **suggestions** (1-2 refinements).

Quality check (internal): resolution correct, no artifacts, all elements present, text legible, mood matches brief, brand guidelines satisfied.

## Editing Workflows

For `/banana edit`, enhance the instruction -- don't pass raw text. "Remove background" becomes "Remove the existing background entirely, replacing with clean transparent or solid white. Preserve all edge detail and fine features like hair strands." See `references/prompt-engineering.md` for edit transformation patterns.

## Multi-turn Chat (`/banana chat`)

1. Generate initial concept with full prompt
2. Refine with specific, targeted changes (not full re-descriptions)
3. Session maintains character/style consistency across turns
4. Use Progressive Enhancement: Composition → Lighting → Details → Polish

## Slide Deck Pipeline (`/banana slides`)

Three-step pipeline for generating slide images from content:

**Step 1 -- Plan** (`/banana slides plan`): Read content, divide into slides, write detailed design brief (markdown) with timestamps, transcript references, background styles, visual concepts.

**Step 2 -- Prompts** (`/banana slides prompts`): Convert plan to Nano Banana prompts using Presentation mode + brand preset.

**Step 3 -- Generate** (`/banana slides generate`):
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/slides.py generate --prompts slide-prompts.md --output ~/slides/
python3 ${CLAUDE_SKILL_DIR}/scripts/slides.py estimate --prompts slide-prompts.md
```
Default: 16:9, 4K. Use `--mode background` or `--mode complete`.

## Model Routing

| Scenario | Model | Resolution |
|----------|-------|-----------|
| Quick draft | `gemini-2.5-flash-image` | 512/1K |
| Standard | `gemini-3.1-flash-image-preview` | 2K |
| Quality/Print | `gemini-3.1-flash-image-preview` | 4K |
| Text-heavy | `gemini-3.1-flash-image-preview` | 2K, thinking: high |

Default: `gemini-3.1-flash-image-preview`. See `references/gemini-models.md` for full specs.

## Response Format

After generating, always provide:
1. **The image path** -- where it was saved
2. **The crafted prompt** -- show the user what you sent
3. **Settings used** -- model, aspect ratio, resolution
4. **Suggestions** -- 1-2 refinement ideas

## Reference Documentation

Load on-demand -- do NOT load all at startup:
- `references/prompt-engineering.md` -- 5-Component Formula, 11 domain modes, templates, PEEL strategy, character consistency, multilingual, brand guide integration
- `references/gemini-models.md` -- Model specs, resolution tables, input limits, rate limits, pricing
- `references/mcp-tools.md` -- MCP tool parameters, error taxonomy
- `references/replicate.md` -- Replicate backend API reference
- `references/post-processing.md` -- ImageMagick/FFmpeg pipelines, green screen
- `references/cost-tracking.md` -- Pricing table, usage guide
- `references/presets.md` -- Brand Style Guide schema (17 fields)
- `references/social-platforms.md` -- 47 social media platform specs, ratios, pixel targets, negative space
- `references/brand-builder.md` -- Guided brand creation flow (learn → refine → preview → save)
- `references/asset-registry.md` -- Persistent asset registry (characters, products, objects, environments)
- `references/reverse-prompt.md` -- Image analysis → 5-Component Formula prompt extraction
- `references/setup.md` -- Guided API key configuration flow

## Setup, Status & Update

See `references/setup.md` for guided flows. When user runs `/banana setup`, `/banana status`, or `/banana update`, load that reference and follow its instructions.
