<!-- Updated: 2026-04-17 -->
<!-- Originally forked from: https://github.com/AgriciDaniel/banana-claude -->

![Creators Studio](screenshots/cover-image.webp)

# Creators Studio

> **Imagine · Direct · Generate** — Creative Engine for Claude Code

**You shouldn't have to be an AI prompt engineer to make on-brand content.** Most AI image tools hand you a text box and a generic model — you spend more time wrangling prompts than creating, and the output never quite matches your brand voice. Creators Studio flips the script: **Claude becomes your Creative Director**, interpreting your intent, selecting the right domain expertise, and orchestrating the best-in-class AI models for every shot — images, video, audio, and lip-sync — all from inside Claude Code.

Let an AI that's been trained on the best practices for every model write the prompts for you, instead of spending hours teaching yourself to prompt-engineer a moving target.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/claude-code)
[![Version](https://img.shields.io/badge/version-4.0.0-coral)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<details>
<summary><b>📑 Table of Contents</b></summary>

- [The Problem](#the-problem)
- [Meet Your Creative Director](#meet-your-creative-director)
- [The Plan](#the-plan)
- [What You Can Make](#what-you-can-make)
  - [📷 Images](#-images)
  - [🎬 Video](#-video)
  - [🎙️ Audio](#-audio)
- [Installation & Setup](#installation--setup)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [How It Works](#how-it-works)
- [The 5-Component Prompt Formula](#the-5-component-prompt-formula)
- [Domain Modes](#domain-modes)
- [Models](#models)
- [Architecture](#architecture)
- [Release History](#release-history)
- [Requirements](#requirements)
- [License](#license)

</details>

## The Problem

**Generic AI tools cost you hours and give you work that doesn't look like your brand.** If you've tried producing visual content with AI, you already know the pattern:

- 🎯 **Prompt fatigue** — you spend more time tuning the wording than creating the thing
- 🎨 **Brand drift** — the output looks like "AI art," not your product, your tone, or your aesthetic
- 🔄 **Model lock-in** — you pick a tool, learn its quirks, and a better model ships six weeks later

The AI race is emphatically **not finished**. Kling beat VEO to become the video default. ElevenLabs beat Lyria to become the music default. Fabric opened lip-sync that Kling can't do. The next swap is coming. Anchoring your workflow to any one model will cost you.

## Meet Your Creative Director

Creators Studio installs a **Creative Director skill** into Claude Code. Claude isn't just calling a model API — it's reading your intent, consulting the locked reference guides for every model (*"describe the scene, don't just list keywords"* for Gemini 3.1; character-matching start_image prompts for Kling; audio-duration-calibrated line lengths for ElevenLabs voices), selecting the right provider, constructing the optimized prompt, and orchestrating the result. You describe what you want. Claude figures out how.

**The model-agnostic philosophy is deliberate.** When a new model wins a head-to-head bake-off, it becomes the new default — without you having to relearn the prompting rules. v3.8.0 made Kling v3 the video default after a 94-generation bake-off against VEO. v3.8.3 made ElevenLabs Music the music default after a 12-genre blind A/B test. The underlying `/create-image` and `/create-video` commands don't change. Your brand presets don't change. Your existing workflow doesn't change.

![How It Works](screenshots/pipeline-flow.webp)

## The Plan

Three steps. No prompt engineering required.

| 1 | 2 | 3 |
|---|---|---|
| **Install the plugin** — one `claude plugin install` command, guided API-key setup | **Describe your intent** — "a product launch hero for wireless earbuds" or "30-second narrated explainer video" | **Claude directs best-in-class AI** — selects domain mode, constructs optimized prompts, orchestrates generation, hands you the result |

## What You Can Make

Three creative surfaces, one Creative Director.

### 📷 Images

**Brand-native visual assets across 46 social platforms, presentations, brand books, and product assets.** Claude reads your intent, picks a domain lens (Cinema, Product, Editorial, UI/Web, Logo, Landscape, etc.), applies your brand style guide if you have one, and generates at the correct aspect ratio and resolution for the target surface.

![5-Input Creative Brief](screenshots/creative-brief.webp)

![Asset Registry](screenshots/asset-registry.webp)

![Brand Guide Builder](screenshots/brand-builder.webp)

![Platform-Native Generation](screenshots/social-platforms.webp)

![Deck Builder](screenshots/deck-builder-new.webp)

![A/B Testing](screenshots/ab-testing.webp)

![Content Pipeline](screenshots/content-pipeline.webp)

**Key features:** 5-Input Creative Brief · 11 Domain Modes · 5-Component Prompt Formula · Edit-First refinements · Brand Style Guides · Asset Registry (save once, reuse everywhere) · Platform-native generation (46 platforms) · Slide decks and brand books · A/B prompt variation testing · Multi-format output · Session history with gallery export.

### 🎬 Video

**Cinematic sequences with character cohesion, professional audio, and lip-synced narration.** From a one-line idea to a 30-second shipped video: plan the shot list, approve the storyboard frames before burning video budget, generate the clips with the character locked across every shot, and stitch the final with a full audio bed.

![Character Consistency](screenshots/character-consistency.webp)

![Idea to Final](screenshots/video-idea-to-final.webp)

![Video Pipeline](screenshots/video-pipeline.webp)

![Video Domain Modes](screenshots/video-domain-modes.webp)

![Sequence Production](screenshots/sequence-production.webp)

![Storyboard Workflow](screenshots/storyboard-workflow.webp)

**Key features:** Kling v3 Std default (1080p, $0.02/s, 1:1 Instagram-square native) · VEO 3.1 opt-in backup · Character consistency via `start_image` + matched prompt · Multi-shot sequence pipeline (plan → storyboard → generate → stitch) · Mandatory review gate before expensive clip generation · Fabric 1.0 lip-sync (any face + any audio → talking-head MP4) · Image-to-video (animate a still from `/create-image`) · FFmpeg stitch/concat/trim utilities.

### 🎙️ Audio

**Narration, music, and mixed audio beds — designed to replace VEO's emergent audio on stitched sequences.** Custom voice design from plain-English descriptions. Instant Voice Cloning. Multi-provider music with negative-prompt support. Side-chain ducking. End-to-end audio-bed replacement in one command.

![Audio Pipeline](screenshots/audio-pipeline.webp)

**Key features:** ElevenLabs TTS narration (custom voice design + IVC) · ElevenLabs Music (default, won 12-0 blind bake-off vs Lyria) · Lyria 2 alternative ($0.06/clip, negative-prompt support) · Side-chain ducking (music dips under narration automatically) · Auto-measured per-voice WPM for duration-calibrated line lengths · Client-side stripping of copyrighted-creator triggers (so Lyria/Eleven Music don't reject your prompt) · Full audio-bed replacement pipeline for stitched video sequences.

---

**The whole system is the product.** Brand presets feed into images AND video. Asset registry entries appear in both. A custom voice designed once plays in every narrated video. The workflows are deliberately connected.

## Installation & Setup

### Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed and working
- [Git](https://git-scm.com/) installed
- [Node.js 18+](https://nodejs.org/) installed (for the MCP server)

### Install

```bash
git clone https://github.com/juliandickie/creators-studio.git ~/creators-studio
claude --plugin-dir ~/creators-studio
```

### Configure your Google AI API key

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey), then in Claude Code:

```
/create-image setup
```

Claude walks you through the key setup conversationally. Your key is saved to `~/.claude/settings.json` (for the MCP server) and `~/.banana/config.json` (for fallback scripts). Keys never leave your machine and are never sent to GitHub.

> **Free tier:** ~5-15 images per minute, ~20-500 per day. No credit card required.
>
> **Video generation (paid):** Kling v3 Std at $0.02/s via Replicate ($0.16 per 8s clip). VEO 3.1 opt-in backup requires Google Cloud billing.

### Test it

```
/create-image generate "a golden banana wearing a beret"
```

If you see an image path and the file exists, you're all set.

### Updating

```bash
cd ~/creators-studio && git pull
```

Then in Claude Code type `/reload-plugins` to pick up changes.

<details>
<summary><b>🔧 Optional: Replicate as fallback backend</b></summary>

Replicate provides an alternative API backend using `google/nano-banana-2` for images and is the required backend for Kling v3 video and Fabric 1.0 lip-sync. Useful when the MCP server isn't available, or if you prefer simpler auth.

1. Get a token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
2. In Claude Code: `/create-image setup replicate`
3. Paste the token when prompted

The image fallback chain is automatic: MCP → Direct Gemini API → Replicate. Video always uses Replicate for Kling/Fabric.

</details>

<details>
<summary><b>🎬 Optional: VEO 3.1 video (Vertex AI, paid)</b></summary>

VEO is the opt-in backup for video. For full VEO capabilities (Lite at $0.05/s, image-to-video, Scene Extension v2, GA `-001` IDs) you need a Vertex AI API key. Add three fields to `~/.banana/config.json`:

```json
{
  "vertex_api_key": "...",
  "vertex_project_id": "my-project-123",
  "vertex_location": "us-central1"
}
```

Invoke via `/create-video generate "..." --provider veo --tier {lite|fast|standard}`.

</details>

## Quick Start

```bash
# --- Images ---
/create-image generate "a hero image for a coffee shop website"
/create-image social "product launch hero" --platforms ig-feed,yt-thumb,li-feed,tt-feed
/create-image slides plan --content ~/transcripts/ --preset my-brand
/create-image brand                                                        # conversational brand-guide builder
/create-image asset create "my-product" --reference ~/photos/item.jpg      # save for reuse
/create-image batch "landing page hero for fintech app" 3                  # Literal + Creative + Premium variations

# --- Video ---
/create-video generate "product reveal of wireless earbuds on dark surface"
/create-video animate ~/image.png "slow orbit revealing the product"
/create-video sequence plan --script "30-second product launch ad" --target 30
/create-video sequence storyboard --plan shot-list.json
/create-video sequence review --plan shot-list.json --storyboard ~/storyboard/
/create-video sequence generate --storyboard ~/storyboard/
/create-video sequence stitch --clips ~/clips/ --output final.mp4

# --- Audio + Lip-sync ---
/create-video voice design --description "warm baritone with a slight British accent"
/create-video audio pipeline --video final.mp4 --text "Meet the new..." --music-prompt "cinematic swell"
/create-video lipsync --image face.jpg --audio narration.mp3

# --- Utilities ---
/create-image cost summary
/create-image status
```

Claude acts as Creative Director for every call — selecting domain modes, constructing optimized prompts, and managing brand/asset consistency across media.

## Commands

### 📷 Image Commands

| Command | Description |
|---------|-------------|
| `/create-image` | Interactive — Claude detects intent and guides you |
| `/create-image generate <idea>` | Full Creative Director pipeline |
| `/create-image edit <path> <instructions>` | Intelligent image editing |
| `/create-image chat` | Multi-turn visual session (character/style consistent) |
| `/create-image slides [plan\|prompts\|generate]` | Slide deck pipeline: content → design brief → prompts → batch images |
| `/create-image inspire [category]` | Browse prompt database for ideas |
| `/create-image batch <idea> [N]` | Generate N variations (default: 3) |
| `/create-image social <idea> --platforms <list>` | Platform-native image generation (46 platforms, 4K, auto-crop) |
| `/create-image brand` | Conversational brand guide builder (learn → refine → preview → save) |
| `/create-image asset [list\|show\|create\|delete]` | Manage persistent character/product/object references |
| `/create-image reverse <image-path>` | Analyze image → extract 5-Component Formula prompt |
| `/create-image book --preset <name> [--tier quick\|standard\|comprehensive]` | Generate visual brand book (markdown + pptx + html) |
| `/create-image setup` | Guided Google AI API key setup |
| `/create-image setup replicate` | Guided Replicate token setup (optional fallback) |
| `/create-image status` | Check version, installation, and API key status |
| `/create-image update` | Pull latest version from GitHub |
| `/create-image preset [list\|create\|show\|delete]` | Manage brand/style presets |
| `/create-image cost [summary\|today\|estimate]` | View cost tracking and estimates |
| `/create-image formats <path> [--formats] [--sizes]` | Convert image to multiple formats/sizes |
| `/create-image history [list\|show\|export\|sessions]` | View session generation history and export gallery |
| `/create-image ab-test <idea> [--count N]` | Generate Literal/Creative/Premium variations and track preferences |
| `/create-image deck --images DIR --output PATH` | Assemble slide images into editable .pptx with brand styling |
| `/create-image analytics [--format html\|json]` | Usage analytics dashboard (cost trends, domain usage, quota) |
| `/create-image content <idea> --outputs hero,social,email` | Multi-modal content pipeline from a single idea |

### 🎬 Video Commands

| Command | Description |
|---------|-------------|
| `/create-video generate <idea>` | Text-to-video with full Creative Director pipeline |
| `/create-video animate <image> <motion>` | Animate a still image (from /create-image or uploaded) |
| `/create-video sequence plan --script "..." --target Ns [--shot-types ...]` | Break a script into a shot list with shot-type defaults |
| `/create-video sequence storyboard --plan PATH [--shots 1,3-5]` | Generate start/end frame pairs (optionally a subset) |
| `/create-video sequence review --plan PATH --storyboard DIR` | Generate REVIEW-SHEET.md — mandatory approval gate in v3.6.3+ |
| `/create-video sequence generate --storyboard PATH [--skip-review]` | Batch-generate clips from approved storyboard frames |
| `/create-video sequence stitch --clips DIR --output PATH` | Assemble clips into final sequence via FFmpeg |
| `/create-video extend <clip> [--to Ns]` | Extend a clip (+7s per hop, max 148s) — **DEPRECATED in v3.8.0**, requires `--acknowledge-veo-limitations` |
| `/create-video lipsync --image FACE --audio AUDIO [--resolution 480p\|720p]` | **v3.8.1** lip-sync a face image to audio via Fabric 1.0 — pairs with `/create-video audio narrate` custom voices |
| `/create-video stitch <clips...>` | Concat, trim, convert video via FFmpeg |
| `/create-video audio pipeline --video V --text "..." --music-prompt "..." [--music-source lyria\|elevenlabs]` | **v3.7.1+v3.8.3** end-to-end: parallel TTS + music (ElevenLabs default, Lyria alt), mix, swap into video |
| `/create-video audio narrate --text "..." [--voice ROLE]` | **v3.7.1** generate ElevenLabs TTS narration only |
| `/create-video audio music --prompt "..." [--source lyria\|elevenlabs] [--negative-prompt "..."]` | **v3.8.3** background music — ElevenLabs default, Lyria alt ($0.06/clip, supports negative-prompt) |
| `/create-video audio mix --narration N --music M` | **v3.7.1** mix existing narration + music with side-chain ducking |
| `/create-video audio swap --video V --audio A` | **v3.7.1** swap an audio file into a video (lossless video) |
| `/create-video voice design --description "..."` | **v3.7.1** generate 3 voice previews from a text description |
| `/create-video voice promote --generated-id ID --name N --role R` | **v3.7.1** save a chosen preview as a permanent custom voice |
| `/create-video voice list` | **v3.7.1** list saved custom voices from `~/.banana/config.json` |
| `/create-video cost [estimate]` | Video cost estimation |
| `/create-video status` | Check VEO API access and FFmpeg availability |
| `/create-video audio status` | **v3.7.1** check ElevenLabs API key + ffmpeg + custom voices |

## How It Works

Every generation follows the same Creative Director pipeline:

1. **Intent** — Claude reads your request and gathers the 5-Input Creative Brief (Purpose, Audience, Subject, Brand, References)
2. **Domain** — Claude selects the right creative lens (Cinema, Product, Portrait, Editorial, UI/Web, Logo, Landscape, Abstract, Infographic, Presentation)
3. **Prompt** — Claude constructs the prompt using the model's native strengths (Gemini 3.1's narrative understanding, Kling's multi_prompt shot list, ElevenLabs' audio-tag vocabulary)
4. **Generate** — Claude calls the best-in-class model for the task with the optimized parameters
5. **Deliver** — Save the asset, log the cost, offer refinement suggestions

Every reference guide (`references/prompt-engineering.md`, `references/kling-models.md`, `references/audio-pipeline.md`, etc.) is loaded on demand — Claude only reads what's relevant to the current task. The references are revised against the official model docs every time a new model version ships; that's the "AI writes for AI" loop in practice.

## The 5-Component Prompt Formula

![Prompt Formula](screenshots/reasoning-brief.webp)

Instead of sending "a cat in space" to the API, Claude constructs:

> A medium shot of a tabby cat floating weightlessly inside the cupola module of the International Space Station, paws outstretched toward a floating droplet of water, Earth visible through the circular windows behind. Soft directional light from the windows illuminates the cat's fur with a blue-white rim light, while the interior has warm amber instrument panel glow. Captured with a Canon EOS R5, 35mm f/2.0 lens, slight barrel distortion emphasizing the curved module interior. Sharp documentary clarity.

**Components used:** Subject (tabby cat, physical detail) → Action (floating, paw gesture) → Location/Context (ISS cupola, Earth visible) → Composition (medium shot, curved framing) → Style (Canon R5, directional window light + amber instruments)

## Domain Modes

![Domain Modes](screenshots/domain-modes.webp)

| Mode | Best For | Example |
|------|----------|---------|
| **Cinema** | Dramatic, storytelling | "A noir detective scene in a rain-soaked alley" |
| **Product** | E-commerce, packshots | "Photograph my handmade candle for Etsy" |
| **Portrait** | People, characters | "A cyberpunk character portrait for my game" |
| **Editorial** | Fashion, lifestyle | "A fashion shot for my brand's lookbook" |
| **UI/Web** | Icons, illustrations | "A set of onboarding illustrations" |
| **Logo** | Branding, identity | "A minimalist logo for a tech startup" |
| **Landscape** | Backgrounds, wallpapers | "A misty mountain sunrise for my desktop" |
| **Infographic** | Data, diagrams | "Visualize our Q1 sales growth" |
| **Abstract** | Generative art, textures | "Voronoi tessellation in neon gradients" |
| **Presentation (Complete)** | Finished slides with text | "Title slide with 'DIGITAL INNOVATION' headline" |
| **Presentation (Background)** | Slide backgrounds for layering | "Dark premium background for keynote deck" |

## Models

Creators Studio is model-agnostic — models are swapped in and out based on empirical bake-offs, not brand loyalty. The current roster reflects tried-and-tested winners as of v4.0.0.

| Surface | Default | Alternative | Specialist |
|---|---|---|---|
| **Image** | Gemini 3.1 Flash (free tier) | Gemini 2.5 Flash · Replicate `google/nano-banana-2` | — |
| **Video** | Kling v3 Std ($0.02/s, 1080p) | VEO 3.1 Lite/Fast/Standard (opt-in, `--provider veo`) | DreamActor M2.0 (deferred to v4.1.x) |
| **Music** | ElevenLabs Music (won 12-0 bake-off) | Lyria 2 ($0.06/clip, supports negative-prompt) | — |
| **Voice/TTS** | ElevenLabs (custom design + cloning) | — | — |
| **Lip-sync** | — | — | VEED Fabric 1.0 ($0.15/s output, 720p max) |

## What Makes This Different

- **5-Input Creative Brief** — Gathers Purpose, Audience, Subject, Brand, References before generating
- **Domain Expertise** — Selects the right creative lens per the 11 modes above
- **5-Component Prompt Formula** — Subject + Action + Location + Composition + Style
- **Start with Intent, Refine with Specs** — Two-phase prompting with the PEEL strategy (Position, Expression, Environment, Lens)
- **Edit-First Workflow** — 90% of refinements edit the image rather than regenerating
- **Brand Style Guides** — Rich preset system with background styles, motifs, keywords, do's/don'ts, and prompt suffixes
- **Asset Registry** — Save characters, products, equipment, environments once; reuse forever across sessions
- **Presentation Mode** — Complete slides with rendered text, or clean backgrounds for layering
- **Multi-Provider Fallback** — MCP → Direct Gemini API → Replicate for maximum availability
- **Session Consistency** — Character/style maintained across multi-turn chat with progressive enhancement
- **4K Output · 14 Aspect Ratios** — Including ultra-wide 21:9 and extreme 8:1 banners

## Architecture

<details>
<summary><b>🗂 Full plugin tree</b></summary>

```
creators-studio/                       # Claude Code Plugin
├── .claude-plugin/
│   ├── plugin.json                    # Plugin manifest
│   └── marketplace.json               # Marketplace catalog
├── skills/create-image/               # Image skill
│   ├── SKILL.md                       # Creative Director orchestrator (~270 lines)
│   ├── references/                    # 19 reference guides, loaded on demand
│   │   ├── prompt-engineering.md      # 5-component formula, 11 domain modes, PEEL
│   │   ├── gemini-models.md           # Model specs, resolution tables, input limits
│   │   ├── mcp-tools.md               # MCP tool parameters and responses
│   │   ├── replicate.md               # Replicate backend API reference
│   │   ├── social-platforms.md        # 46 platform specs and ratios
│   │   ├── brand-builder.md           # Conversational brand guide flow
│   │   ├── asset-registry.md          # Persistent asset system
│   │   ├── reverse-prompt.md          # Image → prompt extraction
│   │   ├── brand-book.md              # Brand book generator
│   │   ├── post-processing.md         # ImageMagick/FFmpeg pipelines
│   │   ├── cost-tracking.md           # Pricing table + ledger
│   │   ├── presets.md                 # Brand Style Guide schema (17 fields)
│   │   ├── content-pipeline.md        # Multi-modal output orchestration
│   │   ├── analytics.md               # Analytics dashboard
│   │   ├── deck-builder.md            # Deck assembly + brand styling
│   │   ├── ab-testing.md              # A/B variation styles
│   │   ├── session-history.md         # Session tracking + gallery export
│   │   ├── multi-format.md            # PNG/WebP/JPEG multi-size conversion
│   │   └── setup.md                   # Guided API key configuration
│   ├── presets/                       # 12 example brand guide JSONs
│   └── scripts/                       # 20 stdlib-only Python scripts (no pip deps)
├── skills/create-video/               # Video skill
│   ├── SKILL.md                       # Video Creative Director orchestrator (~295 lines)
│   ├── scripts/
│   │   ├── video_generate.py          # Async video API with --backend/--provider routing
│   │   ├── _vertex_backend.py         # Vertex AI helper (Lite, i2v, Scene Ext v2)
│   │   ├── _replicate_backend.py      # Kling + Fabric HTTP plumbing
│   │   ├── video_sequence.py          # Multi-shot pipeline + review gate
│   │   ├── video_lipsync.py           # Fabric 1.0 standalone runner
│   │   ├── video_extend.py            # DEPRECATED in v3.8.0 (hard-gated)
│   │   ├── audio_pipeline.py          # TTS + music + mix + swap
│   │   └── video_stitch.py            # FFmpeg concat/trim/convert
│   └── references/                    # 8 video reference guides
│       ├── kling-models.md            # Kling v3 Std default, Seedance verdict
│       ├── lipsync.md                 # Fabric 1.0 2-step workflow
│       ├── veo-models.md              # VEO backup specs + Vertex constraints
│       ├── video-prompt-engineering.md
│       ├── video-domain-modes.md      # 6 video domain modes + shot types
│       ├── video-sequences.md         # Multi-shot production
│       ├── audio-pipeline.md          # Full audio architecture
│       └── image-to-video.md          # Animate-a-still
└── agents/
    ├── brief-constructor.md           # Image prompt subagent
    └── video-brief-constructor.md     # Video prompt subagent
```

</details>

## Release History

<details>
<summary><b>📜 v4.0.0 (current) — Rebrand to Creators Studio · 2026-04-17</b></summary>

Full rebrand from `nano-banana-studio` to **Creators Studio** — *Imagine · Direct · Generate. Creative Engine for Claude Code.* The old name anchored the plugin to a single Google model at a moment when Kling, ElevenLabs Music, and Fabric had already become best-in-class for their respective surfaces; the new identity is model-agnostic so future swaps don't require a rebrand. Commands change to `/create-image` and `/create-video`. Your `~/.banana/` config, API keys, custom voices, and presets carry forward unchanged — zero config loss on upgrade.

</details>

<details>
<summary><b>📦 v3.8.4 — Replicate Cost Tracking + Strip-List Config · 2026-04-16</b></summary>

Replicate video costs now land in your cost ledger. Kling ($0.02/s), DreamActor ($0.05/s), and Fabric ($0.15/s) pricing is registered in `cost_tracker.py`, and every successful `/create-video generate` or `/create-video lipsync` run auto-logs. Also: extend the named-creator strip-list via `named_creator_triggers` in `~/.banana/config.json`, and wrapper phrases (*"in the style of"*, *"inspired by"*) are cleaned up after the creator name is removed.

</details>

<details>
<summary><b>🎵 v3.8.3 — ElevenLabs Music as Default Provider · 2026-04-16</b></summary>

A 12-genre blind A/B bake-off found ElevenLabs Music decisively outperforms Lyria 2 across every genre tested. ElevenLabs is now the default `--music-source`; Lyria remains available via `--music-source lyria` for its unique `negative_prompt` feature.

</details>

<details>
<summary><b>🎬 v3.8.2 — Character Consistency via start_image · 2026-04-16</b></summary>

Kling's `start_image` feature serves as a character identity lock for multi-clip brand work: generate a reference image once, then pass it as `--first-frame` on every Kling call with a character-matching prompt — and the character persists across separate generations at full 1080p. DreamActor M2.0 deferred to v4.1.x for real-footage-to-avatar workflows.

</details>

<details>
<summary><b>🎤 v3.8.1 — Fabric Lip-Sync + Defensive Hardening · 2026-04-15</b></summary>

New `/create-video lipsync` command pairs any face image with any audio file (including custom-designed ElevenLabs voices from `/create-video audio narrate`) via VEED Fabric 1.0. Also includes Cloudflare User-Agent hardening on the image-gen Replicate path, `_vertex_backend smoke-test` subcommand, and the Seedance 2.0 retest verdict: **permanently rejected** (E005 filter triggers on every human subject tested).

</details>

<details>
<summary><b>🎥 v3.8.0 — Kling v3 as Default Video Model · 2026-04-15</b></summary>

v3.8.0 switches the default video model from VEO 3.1 to Kling v3 Std (via Replicate) after a 15-shot-type head-to-head bake-off. Kling wins 8 of 15 playback-verified shot types (VEO 0), is 7.5× cheaper per 8s clip, natively supports 1:1 Instagram-square aspect ratio, and produces coherent 30-second narratives where VEO's extended workflow produces glitches. VEO remains available as an opt-in backup via `--provider veo`.

</details>

<details>
<summary><b>📚 Older releases (v1.4.2 → v3.7.4)</b></summary>

### Audio & Video era (v3.x)

**v3.7.4** — Audio polish bundle: real stereo narration mix, Instant Voice Cloning, auto-measured per-voice WPM, multi-call Lyria with FFmpeg crossfade, shared client-side creator stripping across Lyria + ElevenLabs Music.

**v3.7.3** — Prompt-engineering reference refreshed against Google's official Gemini 3.1 Flash Image guide. Leads with *"describe the scene, don't just list keywords"*.

**v3.7.2** — Google Lyria 2 made the (then-)default music source after 5-way bake-off (Lyria > ElevenLabs > MusicGen > MiniMax > Stable Audio). Script renamed `elevenlabs_audio.py` → `audio_pipeline.py`.

**v3.7.1** — ElevenLabs Audio Replacement Pipeline + Custom Voice Design. One command replaces the entire audio bed on stitched VEO sequences. Design a voice from plain-English description, save under a semantic role name.

**v3.6.3** — Review Gate Enforcement + Smarter Plans. Mandatory review gate before any video generation call, catching the expensive failure mode of generating a $12 clip against a silently-regenerated frame.

**v3.6.2** — Sequence Production Polish from the first real shoot: review subcommand, `use_veo_interpolation` per-shot flag, partial storyboard regeneration via `--shots 1,3-5`.

**v3.6.1** — First+last frame interpolation + reference images on Vertex.

**v3.6.0** — Vertex AI Backend. A new backend using bound-to-service-account API-key auth (no OAuth, no service account JSON, no `gcloud`) unlocks VEO 3.1 Lite at $0.05/sec, image-to-video via `--first-frame`, Scene Extension v2, and GA `-001` model IDs.

**v3.5.0** — VEO 3.1 Model Variants & Draft Workflow. Lite/Fast/Standard tiers, `--quality-tier` flag, model routing infrastructure, corrected VEO pricing.

**v3.4.x → v3.0.0** — Video skill launch: VEO 3.1 text-to-video, image-to-video, first/last frame, multi-shot sequences, extension + stitching toolkit, domain modes + audio prompting, cross-skill integration with image generation.

### Image expansion era (v2.x)

**v2.7.0** — Multi-Modal Content Pipeline. Single idea → hero image + social pack + email header + format pack + video clip.

**v2.6.0** — Analytics Dashboard (HTML with SVG charts).

**v2.5.0** — Deck Builder (.pptx with brand styling, 3 layouts).

**v2.4.0** — Smart A/B Testing with preference tracking.

**v2.3.0** — Session History with gallery export.

**v2.2.0** — Multi-format output (PNG/WebP/JPEG at 4K/2K/1K/512).

**v2.0.0** — Visual Brand Book Generator (markdown + pptx + html).

**v1.9.0** — Reverse Prompt Engineering.

**v1.8.0** — Asset Registry — persistent characters/products/objects.

**v1.7.0** — Social Media Generation (46 platforms) + Brand Guide Builder + 12 example presets.

**v1.6.0** — Slide Deck Pipeline.

**v1.5.0** — Presentation Mode + Brand Style Guides + logo exclusion rule.

### Origin (v1.4.2)

**v1.4.2** — Original fork: Replicate backend, 5-Input Creative Brief, PEEL strategy, Edit-First principle, Three Prompt Variations (Literal/Creative/Premium), Progressive Enhancement, expanded character consistency, multilingual support, resolution pixel tables. Forked from [AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude) at v1.4.1.

</details>

See [CHANGELOG.md](CHANGELOG.md) for the full release notes including technical details, research findings, and cost-breakdown tables.

## Requirements

- [Claude Code](https://claude.ai/claude-code)
- [Git](https://git-scm.com/)
- [Node.js 18+](https://nodejs.org/) (for the MCP server)
- [Python 3.6+](https://www.python.org/) — system Python is fine; all scripts use `urllib.request` with zero pip dependencies
- [FFmpeg](https://ffmpeg.org/) — optional, for audio pipeline and video stitching
- [ImageMagick](https://imagemagick.org/) — optional, for image post-processing

## Uninstall

```bash
rm -rf ~/creators-studio
rm -rf ~/.banana                       # removes API keys, custom voices, presets, cost ledger
```

Then remove the MCP server entry from `~/.claude/settings.json`.

## License

MIT — see [LICENSE](LICENSE).
