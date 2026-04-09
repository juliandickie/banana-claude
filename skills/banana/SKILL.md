---
name: banana
description: "Use when ANY request involves image creation, editing, visual asset production, slide generation, or creative direction. Triggers on: generate an image, create a photo, edit this picture, design a logo, make a banner, slide deck, social media visuals, and all /banana commands."
argument-hint: "[generate|edit|chat|slides|social|brand|asset|reverse|book|batch|inspire|preset|cost|setup|status|update] <idea, path, or command>"
---

# Banana Claude -- Creative Director for AI Image Generation

<!-- MCP package: @ycse/nanobanana-mcp | Version managed in plugin.json -->

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
| `/banana book --preset <name> [--tier quick\|standard\|comprehensive]` | Generate visual brand book (markdown + pptx + html) |
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

### Step 2: Check for Presets

If user mentions a brand/preset: `python3 ${CLAUDE_SKILL_DIR}/scripts/presets.py list`. Load with `show NAME`. Preset values are defaults -- user instructions override. See `references/presets.md` for Brand Style Guide fields.

**Logo handling:** NEVER mention "logo" in prompts. Describe the area as "clean negative space." Logos are composited in presentation software after generation.

**Example presets:** If no presets exist, offer to install examples: `ls ${CLAUDE_SKILL_DIR}/presets/` shows 12 pre-built brand guides. Copy with: `cp ${CLAUDE_SKILL_DIR}/presets/NAME.json ~/.banana/presets/`

### Step 3: Check for Assets

If user mentions a named character, product, or object, check assets:
`python3 ${CLAUDE_SKILL_DIR}/scripts/assets.py list`. Load with `show NAME`.
Pass `reference_images[]` as inlineData parts in the API call. Append
`consistency_notes` to the prompt. See `references/asset-registry.md`.

### Step 4: Select Domain Mode

Choose from: **Cinema**, **Product**, **Portrait**, **Editorial**, **UI/Web**, **Logo**, **Landscape**, **Abstract**, **Infographic**, **Presentation (Complete)**, **Presentation (Background)**. See `references/prompt-engineering.md` → Domain Mode Modifier Libraries.

### Step 5: Construct Prompt

Use the **5-Component Formula**: Subject → Action → Location/Context → Composition → Style (includes lighting). Write as natural narrative prose, NEVER keyword lists. See `references/prompt-engineering.md` → Proven Prompt Templates.

**Critical rules:** Use prestigious context anchors ("Vanity Fair editorial," "National Geographic cover"). NEVER use banned keywords ("8K," "masterpiece," "ultra-realistic"). For constraints use ALL CAPS. For products say "prominently displayed."

For batch/exploratory requests, offer **Literal/Creative/Premium** prompt variations.

### Step 6: Set Aspect Ratio + Resolution

Call `set_aspect_ratio` BEFORE generating. Match ratio to use case. Default: `2K`. Presentation: `16:9`, `4K`. See `references/gemini-models.md` → Aspect Ratios + Resolution Tiers.

### Step 7: Call the MCP

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

### Step 8: Post-Processing

If needed, use ImageMagick for cropping, format conversion, background removal. See `references/post-processing.md`. Check tool availability first: `which magick || which convert`.

### Step 9: Handle Errors

| Error | Action |
|-------|--------|
| `IMAGE_SAFETY` | Rephrase prompt (see `references/prompt-engineering.md` → Safety Rephrase). Max 3 attempts with user approval. |
| HTTP 429 | Wait 2s, exponential backoff, max 3 retries |
| HTTP 400 FAILED_PRECONDITION | Billing not enabled -- inform user |
| HTTP 5xx | Server error -- wait 5s, retry with backoff, max 3 retries. Common during model rollouts. |
| Invalid API key | Inform user, suggest running `/banana setup` to reconfigure |
| MCP unavailable | Use fallback chain (Step 7) |
| Vague request | Ask clarifying questions |

### Step 10: Log Cost

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/cost_tracker.py log --model MODEL --resolution RES --prompt "brief"
```

### Step 11: Return Results

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

## /banana reverse

Analyze an image and extract the prompt that would recreate it. See `references/reverse-prompt.md` for the full 5-Component decomposition methodology.

## /banana social

Generate platform-native images at correct ratios for 47 platforms. See `references/social-platforms.md` for specs. Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/social.py generate --prompt "..." --platforms ig-feed,yt-thumb`

## /banana brand

Guided brand creation: gather sources → auto-extract → refine → preview → save. See `references/brand-builder.md`.

## /banana inspire

Browse prompt ideas by category. Load `references/prompt-engineering.md` → Proven Prompt Templates section. Present 3-5 templates from the requested category (or random if none specified). Show the template prompt and suggest how to customize it.

## /banana book

Generate a complete visual brand book from a preset in three formats. See `references/brand-book.md` for tier details and options.
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/brandbook.py generate --preset NAME --output ~/brand-book/ --tier standard
```

## Setup, Status & Update

See `references/setup.md` for guided flows. When user runs `/banana setup`, `/banana status`, or `/banana update`, load that reference and follow its instructions.

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
- `references/brand-book.md` -- Brand book generator (tiers, formats, color specs)
- `references/setup.md` -- Guided API key configuration flow
