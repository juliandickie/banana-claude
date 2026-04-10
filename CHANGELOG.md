# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.5.0] - 2026-04-10

### ⚠️ Backend Reality Check

Real-API verification during the v3.5.0 release surfaced a critical distinction: **VEO 3.1 is split across two backends**. The plugin uses the Gemini API (`generativelanguage.googleapis.com`, API-key auth), while Lite, Legacy 3.0, GA `-001` IDs for Standard/Fast, and Scene Extension v2 (`--video-input`) are **Vertex AI only** (`*-aiplatform.googleapis.com`, OAuth/service-account auth). The Gemini API returns HTTP 404 for every `-001` ID and rejects `--video-input` with "inlineData isn't supported by this model." Until the Vertex AI backend ships in v3.6.0, the plugin gates these features with clear error messages and remaps `--quality-tier draft` to Fast instead of Lite. See `skills/video/references/veo-models.md` → Backend Availability for full details. Vertex AI support is now tracked as the top v3.6.0 roadmap item.

### Fixed
- **VEO Lite model ID** — the plugin previously shipped `veo-3.1-generate-lite-preview` which does not exist as a real API endpoint. v3.5.0 ships the correct GA ID `veo-3.1-lite-generate-001` for users running against Vertex AI directly, and documents it for the Gemini API path with a clear error pointing at the v3.6.0 Vertex AI backend.
- **VEO pricing** — the cost tracker's Standard rate was incorrectly set to $0.15/sec. Corrected to the official $0.40/sec ($3.20 per 8s clip) matching Google Cloud Vertex AI pricing. Fast ($0.15/sec) and Lite ($0.05/sec) tiers are now listed separately rather than conflated.

### Added
- **VEO 3.1 model variants** in `video_generate.py` — Fast tier (`veo-3.1-fast-generate-preview` / `-001`), Lite tier (`veo-3.1-lite-generate-001`), and Legacy 3.0 (`veo-3.0-generate-001`). Both preview and GA (`-001`) IDs are accepted for Standard and Fast.
- **Model-aware parameter validation** — Lite supports 5–60 s durations and 1:1 square aspect ratio; Standard/Fast reject those. 4K is rejected on Lite and Legacy 3.0.
- **`--negative-prompt`** flag on `video_generate.py` with Google's official guidance (describe what you want; use negatives only for known failure modes).
- **`--seed`** flag on `video_generate.py` for reproducible generations.
- **`--video-input`** flag on `video_generate.py` — Scene Extension v2 mode, mutually exclusive with image inputs, forces 720p.
- **`--quality-tier {draft,fast,standard,lite,legacy}`** flag on `video_sequence.py generate` and `estimate` — enables the draft-then-final workflow. `draft` currently maps to Fast ($0.15/sec, 2.7× cheaper than Standard) on the Gemini API; `lite` and `legacy` fail fast with a clear pointer to the v3.6.0 Vertex AI backend. A 4-shot 30-second sequence costs $4.80 at Fast draft vs $12.80 at Standard.
- **Per-shot and sequence-level `model`/`resolution` fields** in the plan.json schema, with a 3-level cascade (CLI override → shot → plan → default) and graceful fallback for old plans.
- **`--method {video,keyframe}`** flag on `video_extend.py`. Default is `video` (Scene Extension v2: passes previous clip directly, preserves audio continuity at 720p). `keyframe` retains the legacy last-frame extraction path at any resolution.
- **`--model` flag on `video_extend.py`** with per-hop cost estimation using the selected model's actual rate.
- **Token-limit prompt validation** in `video_generate.py` — warns at ~950 tokens (3,800 chars), hard-rejects at ~1,125 tokens (4,500 chars) to prevent confusing API-layer failures.
- **`download_expires_at` timestamp** in `video_generate.py` JSON output and a stderr warning about Google's 48-hour video retention window.
- **New `_veo_cost(model, duration_seconds)` helper** in `cost_tracker.py` with per-second fallback for Lite's extended 5–60 s range.
- **README: "VEO 3.1 Model Variants & Draft Workflow (v3.5.0)"** section.

### Changed
- **`video_extend.py` default method** is `keyframe` (last-frame extraction, works on the Gemini API today at any resolution). `--method video` (Scene Extension v2, preserves audio continuity) is documented but errors with a clear Vertex-AI-required message until v3.6.0.
- **`video_sequence.py` cost estimation** now uses real per-tier rates instead of a flat $1.20/clip. Output includes a per-model breakdown.
- **Video SKILL.md Model Routing table** rewritten with 5 scenarios (draft / quick social / standard / hero / legacy) and a draft-first recommendation.

### Docs
- **Full rewrite of `skills/video/references/veo-models.md`** with the VEO release timeline, 3-tier comparison table, GA vs preview IDs, 4K-is-AI-upscaled clarification, capability matrix, known limitations (character drift, text rendering, 8 s ceiling, silent output failures), 48-hour video retention, regional availability (EEA/Swiss/UK), rate limits, competitive context (Arena Elo 1381), and audio quality comparison.
- **`skills/video/references/video-sequences.md`** — new draft-then-final workflow section with cost comparison table, Gemini + VEO as Google's officially recommended pattern, timestamp prompting as a cost-reduction technique, and character drift mitigation framing.
- **`skills/video/references/video-prompt-engineering.md`** — new sections for timestamp prompting (`[00:00-00:02]` syntax), lens focal length guidance (16 mm / 35 mm / 50 mm / 85 mm table), dialogue timing (words-per-clip by duration), recommended negative prompt boilerplate, text rendering warning, and 100–200 word prompt-length target.
- **README** version badge bumped, model comparison table updated with all four VEO variants and per-second pricing.

## [3.4.1] - 2026-04-09

### Fixed
- **VEO API integration** -- Three bug fixes discovered when first running against real API:
  - Removed unsupported `personGeneration: allow_adult` parameter (text-to-video only allows `allow_all` or omission)
  - Fixed image format from `bytesBase64Encoded` to `inlineData.data` (matches API spec for first/last frame and reference images)
  - Fixed response path from `response.generatedSamples` to `response.generateVideoResponse.generatedSamples` (with fallback for older API versions)
  - Added API key authentication to video URI downloads
- Verified end-to-end: 4s and 6s clips successfully generated and downloaded

### Added
- **8 new feature images** in README: video pipeline, video domain modes, sequence production, storyboard workflow, A/B testing, deck builder, analytics dashboard, content pipeline
- **2 sample video clips** in README: product reveal (6s/1080p) and banana spinning (4s/720p) — actual VEO 3.1 outputs

## [3.4.0] - 2026-04-09

### Added
- **`/video extend`** -- Extend a clip by chaining: extract last frame, generate next clip, concatenate. +7s per hop, max 148s
  - `scripts/video_extend.py` -- automated multi-hop extension with progress tracking
- **`/video stitch`** -- FFmpeg video toolkit: concat, trim, convert, info
  - `scripts/video_stitch.py` -- concat multiple clips, trim to duration, convert formats, get video info

## [3.3.0] - 2026-04-09

### Added
- **`/video sequence`** -- Multi-shot video sequence production pipeline
  - `scripts/video_sequence.py` -- plan, storyboard, estimate, generate, stitch subcommands
  - Storyboard approval workflow: generate frame pairs with /banana before committing to video
  - First/last frame chaining: end frame of shot N = start frame of shot N+1
  - Target durations: 15s, 30s, 60s, 90s, 2min+ with shot count recommendations
  - `references/video-sequences.md` -- shot list format, consistency rules, cost estimation

## [3.2.0] - 2026-04-09

### Added
- **Image-to-video pipeline** -- `/video animate` with `image-to-video.md` reference documenting cross-skill workflow (/banana → /video)
- **Content pipeline video support** -- `content_pipeline.py` now supports `"video"` output type using hero image as first frame
- **Session history video type** -- `history.py` now accepts `--type video` for video generation logging

## [3.1.0] - 2026-04-09

### Added
- **Video domain modes** -- 6 modes (Product Reveal, Story-Driven, Environment Reveal, Social Short, Cinematic, Tutorial/Demo) with camera vocabulary and modifier libraries
- **Video audio guide** -- Dialogue, SFX, ambient, and music prompting strategies with domain-specific patterns
- **video-brief-constructor agent** -- Subagent for video prompt construction using 5-Part Framework
- **Shot types for sequences** -- Establishing, medium, close-up, cutaway, B-roll, transition with editing rhythm guide
- `references/video-domain-modes.md`, `references/video-audio.md`, `agents/video-brief-constructor.md`

## [3.0.0] - 2026-04-09

### Added
- **`/video` skill** -- New separate video generation skill powered by Google VEO 3.1
  - `skills/video/SKILL.md` (~188 lines) -- Video Creative Director orchestrator
  - `skills/video/scripts/video_generate.py` (~317 lines) -- Async VEO API with polling, first/last frame, reference images
  - `skills/video/references/veo-models.md` -- VEO model specs, pricing ($0.15-0.40/sec), rate limits
  - `skills/video/references/video-prompt-engineering.md` -- 5-Part Video Framework (Camera, Subject, Action, Setting, Style+Audio)
  - Text-to-video, image-to-video, and first/last frame keyframe interpolation
  - Same API key as image generation, same brand preset and asset registry
  - Commands: generate, animate, sequence, extend, stitch, cost, status

### Changed
- Updated `cost_tracker.py` with VEO per-second pricing (duration-based keys)
- Added cross-reference in banana SKILL.md pointing to `/video` skill

## [2.7.0] - 2026-04-09

### Added
- **`/banana content`** -- Multi-modal content pipeline: one idea → hero, social, email, formats
  - `scripts/content_pipeline.py` (~420 lines) orchestrates existing scripts via subprocess
  - Two-phase workflow: plan (cost estimate) → generate (execute step-by-step)
  - Dependency handling (email/formats wait for hero)
  - Status tracking with plan.json and manifest.json
  - `references/content-pipeline.md` -- output types, dependencies, cost estimation

## [2.6.0] - 2026-04-09

### Added
- **`/banana analytics`** -- Self-contained HTML analytics dashboard
  - `scripts/analytics.py` (~490 lines) with inline SVG charts (no external JS)
  - Cost timeline, model/domain breakdown, resolution distribution, quota gauge
  - Aggregates data from cost tracker, session history, and A/B preferences
  - `references/analytics.md` -- dashboard sections and data sources

## [2.5.0] - 2026-04-09

### Added
- **`/banana deck`** -- Slide deck builder: assemble generated images into editable .pptx
  - `scripts/deckbuilder.py` (~590 lines) with 3 layout modes: fullbleed, standard, split
  - Brand preset integration (colors, typography, logo placement)
  - Title slide + content slides + closing slide
  - Slide notes contain original prompts from generation-summary.json
  - `references/deck-builder.md` -- layouts, preset integration, logo handling

## [2.4.0] - 2026-04-09

### Added
- **`/banana ab-test`** -- Smart A/B testing with Literal/Creative/Premium prompt variations
  - `scripts/abtester.py` (~340 lines) generates variations, tracks ratings and preferences
  - Rating system (1-5 scale) with aggregate preference learning
  - Commands: generate, rate, preferences, history
  - `references/ab-testing.md` -- variation styles, rating system, preferences tracking

## [2.3.0] - 2026-04-09

### Added
- **`/banana history`** -- Session generation history with visual gallery export
  - `scripts/history.py` (~180 lines) tracks all generations per session
  - Commands: log, list, show, export (markdown gallery), sessions
  - Automatic logging integrated into pipeline Step 10
  - Export as markdown with image paths for inline rendering
  - `references/session-history.md` -- session ID management, export formats

## [2.2.0] - 2026-04-09

### Added
- **`/banana formats`** -- Multi-format image converter: generate once, convert to PNG/WebP/JPEG at 4K/2K/1K/512
  - `scripts/multiformat.py` (~200 lines) with 3-tier backend: ImageMagick v7 → v6 → macOS sips
  - Auto-detects source aspect ratio, scales to correct pixel dimensions per size tier
  - Outputs organized directory with `manifest.json` for downstream tools
  - `references/multi-format.md` -- size tables, format specs, prerequisites

## [2.1.0] - 2026-04-09

### Changed
- **Renamed project** from `banana-claude` to `nano-banana-studio` — new independent identity
- **Detached from GitHub fork network** — `gh` CLI now resolves correctly to this repo
- Updated all repo URLs, plugin name, and documentation references
- Updated CITATION.cff title and repository URL
- Updated install.sh with pre-flight check for conflicting banana-claude installation

### Added
- **Migration guide** in README — instructions for users switching from banana-claude
- **Conflict detection** in install.sh — warns if banana-claude plugin is already installed

## [2.0.1] - 2026-04-09

### Fixed
- **SKILL.md frontmatter** -- removed unrecognized `metadata` block (version/author belong in plugin.json)
- **SKILL.md argument-hint** -- expanded from 7 to 16 subcommands so all commands appear in autocomplete
- **SKILL.md pipeline flow** -- renumbered fractional steps (1, 1.5, 1.6) to sequential 1-11; moved feature sections (reverse, social, brand) after pipeline to restore uninterrupted flow
- **SKILL.md MANDATORY section** -- removed contradictory "read before every call" that conflicted with on-demand loading strategy
- **SKILL.md duplicate Response Format** -- removed standalone section already covered by Step 11
- **SKILL.md error table** -- added HTTP 5xx and invalid API key error rows
- **SKILL.md `/banana inspire`** -- added missing implementation guidance pointing to Proven Prompt Templates
- **marketplace.json** -- updated owner/homepage/repository URLs to match fork (juliandickie)
- **brief-constructor agent** -- fixed fragile relative paths, reduced maxTurns from 5 to 3
- **CLAUDE.md** -- updated version checklist from 4 files to 3 (SKILL.md no longer carries version)

## [2.0.0] - 2026-04-09

### Added
- **`/banana book`** -- visual brand book generator with three output formats:
  - **Markdown + images** -- `brand-book.md` with color tables (Hex/RGB/CMYK/Pantone) + categorized image folder
  - **PowerPoint (.pptx)** -- professional slide deck with brand colors, swatches, typography, photo samples
  - **HTML** -- self-contained single file with base64-embedded images + print CSS (open → Print → PDF)
- Three tiers: `quick` (5 images), `standard` (16), `comprehensive` (25+)
- `scripts/brandbook.py` -- orchestrator with image generation + 3 output formatters (~590 lines)
- `scripts/pantone_lookup.py` -- Hex→RGB→CMYK→Pantone color conversion with 156 Pantone Coated colors
- `references/brand-book.md` -- tiers, formats, options, color spec guide

## [1.9.1] - 2026-04-08

### Changed
- **`/banana reverse`** now provides three perspectives: Claude's interpretation, Gemini's interpretation, and a blended best-of-both prompt
  - Sends the image to Gemini via `gemini_chat` for a second opinion
  - Compares how each AI notices different details (Claude: structured/technical, Gemini: atmospheric/textural)
  - Blended version combines Claude's precision with Gemini's natural observation
  - Includes "What You Can Learn" section highlighting interesting differences

## [1.9.0] - 2026-04-08

### Added
- **`/banana reverse`** -- image-to-prompt reverse engineering
  - Analyzes an image and extracts a structured 5-Component Formula prompt
  - Identifies domain mode, estimates camera/lens/lighting, suggests prestigious context anchor
  - Outputs a complete reconstructed prompt ready to copy and use for recreation
  - `references/reverse-prompt.md` with analysis methodology and output format

## [1.8.0] - 2026-04-08

### Added
- **`/banana asset`** -- persistent asset registry for characters, products, equipment, and environments
  - `scripts/assets.py` with list, show, create, delete, add-image subcommands
  - `references/asset-registry.md` with usage guide, API limits, and CLI reference
  - Assets save named references with images and descriptions to `~/.banana/assets/`
  - Reference images passed as `inlineData` parts in Gemini API calls for visual consistency
  - Validates image size (7MB max), format (JPEG/PNG/WebP/HEIC/HEIF), and count (14 max)
  - Step 1.6 added to Creative Director pipeline for automatic asset detection

## [1.7.0] - 2026-04-07

### Added
- **`/banana social`** -- platform-native image generation for 46 social media platforms
  - Generates at nearest native ratio at 4K, auto-crops to exact platform pixel specs
  - Groups platforms by ratio to avoid duplicate API calls (4 platforms at same ratio = 1 generation)
  - 46 platforms across 12 families: Instagram, Facebook, YouTube, LinkedIn, Twitter/X, TikTok, Pinterest, Threads, Snapchat, Google Ads, Spotify
  - Complete + Image Only modes, platform-aware negative space prompting
  - `scripts/social.py` with generate, list, info subcommands
  - `references/social-platforms.md` with full spec tables and shorthand names
- **`/banana brand`** -- conversational brand guide builder (4-phase: gather sources → auto-extract → refine → preview and save)
  - Learns from websites (via browser tools), PDFs, reference images, or from scratch
  - Auto-extracts into 17-field Brand Style Guide schema
  - Generates preview image before saving
  - `references/brand-builder.md` with full conversational flow
- **12 example brand preset files** in `skills/banana/presets/`:
  tech-saas, luxury-dark, organic-natural, startup-bold, corporate-professional,
  creative-agency, healthcare-clinical, fashion-editorial, food-lifestyle,
  real-estate-luxury, fitness-energy, education-friendly
- Merged banana-installer into main skill (`/banana status`, `/banana update`)
- Feature Completion Checklist strengthened with Command Sync Check + Script Checks
- Plugin validation fixes (agent frontmatter, slides.py permissions, manifest author)

### Changed
- SKILL.md: 15 commands in Quick Reference (was 14)
- Plugin validated and passes all checks

## [1.6.0] - 2026-04-07

### Added
- **`/banana slides` pipeline** -- three-step batch slide deck generation:
  - `plan` -- Claude analyzes content and writes detailed visual design briefs
  - `prompts` -- Claude converts briefs to Nano Banana Pro prompts
  - `generate` -- `slides.py` batch-generates all slide images from prompts markdown
- **`slides.py`** script with `generate`, `estimate`, and `template` subcommands
- 4 new slide-type prompt templates: quote, section divider, image feature, infographic process
- `references/setup.md` -- extracted setup instructions for lazy loading

### Changed
- **SKILL.md restructured as lean orchestrator** (496 → 170 lines, 66% reduction)
  - Detailed content moved to lazy-loaded reference files
  - Duplicated tables (domain modes, aspect ratios, resolutions) removed -- single source in references
  - Setup instructions extracted to `references/setup.md`
  - 330 lines of headroom for future features (social, brand builder, video)
- Version bumped across all 4 files (plugin.json, SKILL.md, README, CITATION.cff)

## [1.5.0] - 2026-04-06

### Added
- **Presentation domain mode** with two generation options:
  - **Complete Slide** -- model renders headline/body text directly (leverages Nano Banana 2's 94% text accuracy)
  - **Background Only** -- clean backgrounds with negative space for layering in Keynote/PPT/Slides
- **Brand Style Guides** -- 8 new optional preset fields for project-wide visual consistency:
  - `background_styles` -- named background variants (dark-premium, gradient, split-layout)
  - `visual_motifs` -- pattern overlays with opacity
  - `prompt_suffix` -- appended verbatim to every prompt
  - `prompt_keywords` -- categorized keywords woven into prompts
  - `do_list` / `dont_list` -- brand guardrails checked before generation
  - `logo_placement` -- records post-production logo position (never mentioned in prompts)
  - `technical_specs` -- default color space, DPI, etc.
- **Logo exclusion rule** -- logos are NEVER mentioned in prompts (model generates artifacts). Described as "clean negative space" instead; logos composited in presentation software
- Presentation mode modifier library in prompt-engineering.md (background styles, layout zones, typography, pattern overlays, slide types)
- 4 Presentation prompt templates (2 Complete, 2 Background-Only)
- Brand Style Guide Integration section in prompt-engineering.md
- Expanded merge rules (items 6-12) for brand guide fields in presets.md
- 8 new CLI args in presets.py for brand guide creation
- README updated with new feature documentation, rationale, and upstream tracking

### Changed
- Domain modes expanded from 9 to 11 (Presentation Complete + Background)
- presets.py `create` command accepts brand guide fields (backward-compatible)
- Logo handling rewritten: replaced "reserve space for logo" with negative-space approach

## [1.4.2] - 2026-03-27

### Added
- **Replicate backend** -- `google/nano-banana-2` as alternative to MCP and Direct Gemini API
  - `scripts/replicate_generate.py` -- stdlib-only generation script
  - `scripts/replicate_edit.py` -- stdlib-only editing script
  - `references/replicate.md` -- full reference doc with params, pricing, error handling
- **5-Input Creative Brief** system in SKILL.md (Purpose, Audience, Subject, Brand, References)
- **Edit-First principle** elevated to core principle with edit-vs-regenerate decision matrix
- **Three Prompt Variations** (Literal/Creative/Premium) for `/banana batch`
- **Quality Checklist** in response verification step
- **PEEL Strategy** for structured spec refinement (Position, Expression, Environment, Lens)
- **Progressive Enhancement** 4-phase workflow for `/banana chat` sessions
- **Multilingual & Localization** section in prompt-engineering.md
- **Expanded Character Consistency** (identity-locked patterns, group photos, storytelling)
- **5 new Common Pitfalls** (contradictory instructions, impossible physics, style mixing, etc.)
- **Expanded Search Grounding** with practical examples table
- **Resolution pixel dimension tables** for all aspect ratios at 512/1K/2K/4K
- **Input Limits section** in gemini-models.md (14 images, 7MB inline, 500MB total, HEIC/HEIF)
- **Watermark Behavior by Tier** table (SynthID, visible sparkle, C2PA)
- **Thinking Visibility** docs (`includeThoughts`, thought images)
- `setup_mcp.py` now supports `--replicate-key` and `--check-replicate`
- Replicate pricing in cost_tracker.py and cost-tracking.md

### Changed
- Prompt engineering approach: "Start with Intent, Refine with Specs" (PEEL strategy)
- Fallback chain: MCP → Direct Gemini API → Replicate
- Output tokens per image corrected to up to ~2,520 (was ~1,290)

### Fixed
- Free tier rate limits in cost-tracking.md corrected to ~5-15 RPM / ~20-500 RPD (was ~10 / ~500)

## [1.4.1] - 2026-03-27

### Changed
- Restructured as official Claude Code plugin (`.claude-plugin/plugin.json` manifest)
- Added marketplace catalog (`.claude-plugin/marketplace.json`) for distribution via `/plugin marketplace add`
- Moved `banana/` to `skills/banana/` (standard plugin layout)
- Moved `.claude/agents/` to `agents/` (standard plugin layout)
- Plugin install is now the primary installation method
- Updated CI workflow, README, CLAUDE.md, and install.sh for new structure

### Fixed
- Git remote URL corrected from `claude-banana` to `banana-claude`
- Removed `firebase-debug.log` from git tracking

## [1.4.0] - 2026-03-19

### Breaking Changes
- Removed `gemini-3-pro-image-preview` (Nano Banana Pro) -- shut down by Google March 9, 2026
- Replaced 6-component Reasoning Brief with Google's official 5-component formula (Subject → Action → Location/Context → Composition → Style)
- Default resolution changed from `1K` to `2K` in fallback scripts
- Banned prompt keywords: "8K", "masterpiece", "ultra-realistic", "high resolution" -- use prestigious context anchors instead

### Added
- Banned Keywords section in prompt-engineering.md (Stable Diffusion-era terms that degrade quality)
- Negative Prompts guidance (semantic reframing, ALL CAPS for constraints)
- Prompt Length Guide (20-60 words quick draft → 200-300 complex)
- Text Rendering section for Nano Banana 2
- Domain-to-model routing table in gemini-models.md
- Resolution defaults by domain mode
- Error response taxonomy in mcp-tools.md (429, 400 FAILED_PRECONDITION, IMAGE_SAFETY)
- Non-existent parameters warning in mcp-tools.md
- `.claude/agents/brief-constructor.md` subagent for prompt construction
- `CLAUDE.md` at repo root with development context and testing instructions
- Mandatory reference loading instruction at top of SKILL.md
- Full generation pipeline with retry logic and error handling in SKILL.md
- Exponential backoff retry logic (429 handling) in generate.py and edit.py
- FAILED_PRECONDITION billing error detection in fallback scripts
- Prestigious context anchors replacing banned quality keywords in all templates

### Changed
- SKILL.md version bumped to 1.4.0 with improved frontmatter
- gemini-models.md fully restructured with NB2/NB naming, updated pricing ($0.067/1K)
- Model routing table uses 5-component references instead of 6-component
- All prompt templates updated to use prestigious anchors instead of banned keywords
- Prompt adaptation rules updated to remove banned keywords

### Fixed
- gemini-3-pro-image-preview listed as "Active" when it was dead since March 9
- Pricing was stale ($0.039 for 3.1 Flash when actual is $0.067)
- Rate limits updated to reflect 92% cut (Free: ~5-15 RPM / ~20-500 RPD)

## [1.3.0] - 2026-03-14

### Added
- **Multi-model routing** -- task-based model selection table (draft/standard/quality/text-heavy/batch)
- **Cost tracking** -- `cost_tracker.py` with log, summary, today, estimate, and reset commands
- **Direct API fallback** -- `generate.py` and `edit.py` scripts for when MCP is unavailable (stdlib only)
- **Brand/style presets** -- `presets.py` for reusable brand identities (colors, style, typography, lighting, mood)
- **CSV batch workflow** -- `batch.py` parses CSV files into generation plans with cost estimates
- **Green screen transparency pipeline** -- workaround for Gemini's lack of transparent backgrounds
- **Safety filter rephrase strategies** -- 5 rephrase patterns, common trigger categories, example rephrases
- Cost tracking reference (`references/cost-tracking.md`) with pricing table and free tier limits
- Brand presets reference (`references/presets.md`) with schema, 3 example presets, merge behavior
- Abstract domain mode added to README
- Step 1.5 (Check for Presets) in Creative Director pipeline
- `/banana preset` and `/banana cost` commands in Quick Reference
- Expanded error handling for MCP unavailable and safety filter false positives

### Changed
- Quality Presets section replaced with Model Routing table
- Pro model status updated: may still be accessible for image generation
- Pricing note: research suggests NB2 pricing may be ~$0.067/img
- Architecture diagram updated to show all 7 scripts and 6 references
- install.sh creates `~/.banana/` directory for cost tracking and presets

### Removed
- Legacy `nano-banana/scripts/__pycache__/` (orphaned .pyc files)

## [1.2.0] - 2026-03-13

### Added
- 4K resolution output via `imageSize` parameter (512, 1K, 2K, 4K)
- 5 new aspect ratios: 2:3, 3:2, 4:5, 5:4, 21:9 (14 total)
- Thinking level control (minimal/low/medium/high)
- Search grounding with Google Search (web + image)
- Multi-image input support (up to 14 references)
- Image-only output mode
- Safety filter documentation with `finishReason` values
- Pricing table, content credentials section (SynthID + C2PA)
- Resolution selection step (Step 4.5) in pipeline
- Character consistency multi-image reference technique
- Cover image, pipeline diagram, reasoning brief diagram, domain modes diagram

### Changed
- Rate limits corrected: ~10 RPM / ~500 RPD (reduced Dec 2025)
- `NANOBANANA_MODEL` default: `gemini-3.1-flash-image-preview`
- Search grounding key: `googleSearch` (REST format)
- Quality presets now include resolution column

### Fixed
- SKILL.md markdown formatting bug on text-heavy template line
- Contradictory prompt engineering mistake #9 wording

## [1.0.0] - 2026-03-13

### Added
- Initial release of Banana Claude
- Creative Director pipeline with 6-component Reasoning Brief
- 8 domain modes, MCP integration, post-processing pipeline
- Batch variations, multi-turn chat, prompt inspiration
- Install script with validation

[3.4.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.4.1
[3.4.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.4.0
[3.3.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.3.0
[3.2.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.2.0
[3.1.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.1.0
[3.0.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.0.0
[2.7.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.7.0
[2.6.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.6.0
[2.5.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.5.0
[2.4.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.4.0
[2.3.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.3.0
[2.2.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.2.0
[2.1.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.1.0
[2.0.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.0.1
[2.0.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.0.0
[1.9.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.9.1
[1.9.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.9.0
[1.8.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.8.0
[1.7.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.7.0
[1.6.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.6.0
[1.5.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.5.0
[1.4.2]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.2
[1.4.1]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.1
[1.4.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.0
[1.3.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.3.0
[1.2.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.2.0
[1.0.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.0.0
