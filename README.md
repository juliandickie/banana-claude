<!-- Updated: 2026-04-06 -->
<!-- Forked from: https://github.com/AgriciDaniel/banana-claude -->

![Banana Claude](screenshots/cover-image.webp)

# Banana Claude

AI image generation skill for Claude Code where **Claude acts as Creative Director** using Google's Gemini Nano Banana models.

Unlike simple API wrappers, Claude interprets your intent, selects domain expertise, constructs optimized prompts using Google's official 5-component formula, and orchestrates Gemini for the best possible results.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/claude-code)
[![Version](https://img.shields.io/badge/version-1.5.0-coral)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Upstream](https://img.shields.io/badge/upstream-AgriciDaniel%2Fbanana--claude-gray)](https://github.com/AgriciDaniel/banana-claude)

> **Blog:** [See banana-claude in action](https://agricidaniel.com/blog/banana-claude-ai-image-generation)

<details>
<summary>Table of Contents</summary>

- [What's New in This Fork](#whats-new-in-this-fork)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [How It Works](#how-it-works)
- [What Makes This Different](#what-makes-this-different)
- [The 5-Component Prompt Formula](#the-5-component-prompt-formula)
- [Domain Modes](#domain-modes)
- [Presentation Mode](#presentation-mode)
- [Brand Style Guides](#brand-style-guides)
- [Replicate Backend](#replicate-backend)
- [Models](#models)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Upstream Tracking](#upstream-tracking)
- [Changelog](CHANGELOG.md)
- [License](#license)

</details>

## What's New in This Fork

This fork extends [AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude) with features driven by production use and research analysis of Google's prompting guidance:

### Presentation Mode (v1.5.0)
Two generation options for slide visuals:
- **Complete Slide** -- Nano Banana 2 renders headline and body text directly in the image, producing finished slides
- **Background Only** -- Clean backgrounds with intentional negative space, designed for layering text and logos in Keynote/PowerPoint/Google Slides

Logos are never mentioned in prompts (the model generates unwanted artifacts). Instead, logo areas are described as "clean negative space" and logos are composited in presentation software.

### Brand Style Guides (v1.5.0)
Enhanced preset system with 8 new optional fields for project-wide visual consistency:
- `background_styles` -- Named background variants (dark-premium, gradient, split-layout)
- `visual_motifs` -- Pattern overlays with opacity (e.g., "geometric network at 30%")
- `prompt_suffix` -- Appended verbatim to every prompt for brand consistency
- `prompt_keywords` -- Categorized keywords woven naturally into prompts
- `do_list` / `dont_list` -- Brand guardrails checked before generation
- `logo_placement` -- Records where logos go in post-production (not in prompts)
- `technical_specs` -- Default color space, DPI, and other technical standards

Fully backward-compatible -- existing simple presets continue to work unchanged.

### Replicate Backend (v1.4.2)
`google/nano-banana-2` on Replicate as an alternative API backend. Fallback chain: MCP (primary) -> Direct Gemini API -> Replicate. Includes `replicate_generate.py` and `replicate_edit.py` (stdlib-only, zero pip deps).

### Research-Driven Improvements (v1.4.2)
Based on analysis of Google's official prompting guides and two research documents:
- **5-Input Creative Brief** -- Purpose, Audience, Subject, Brand, References
- **"Start with Intent, Refine with Specs"** -- Two-phase prompting with PEEL strategy (Position, Expression, Environment, Lens)
- **Edit-First Principle** -- 90% of refinements should edit, not regenerate
- **Progressive Enhancement** -- 4-phase workflow for multi-turn chat sessions
- **Expanded character consistency** -- Identity-locked patterns, group photos (up to 5 people), sequential storytelling
- **Multilingual support** -- Translation within images, cultural adaptation
- **Official spec corrections** -- Output tokens (2,520 not 1,290), HEIC/HEIF input, resolution pixel tables

## Installation

### Plugin Install (Recommended)

Add the marketplace and install:

```shell
/plugin marketplace add AgriciDaniel/banana-claude
/plugin install banana-claude@banana-claude-marketplace
```

Or test locally:

```bash
git clone --depth 1 https://github.com/AgriciDaniel/banana-claude.git
claude --plugin-dir ./banana-claude
```

<details>
<summary>Standalone Install (without plugin system)</summary>

```bash
git clone --depth 1 https://github.com/AgriciDaniel/banana-claude.git
bash banana-claude/install.sh
```

**One-liner (curl):**

```bash
curl -fsSL https://raw.githubusercontent.com/AgriciDaniel/banana-claude/main/install.sh | bash
```

**With MCP Setup:**

```bash
git clone --depth 1 https://github.com/AgriciDaniel/banana-claude.git
cd banana-claude
./install.sh --with-mcp YOUR_API_KEY
```

</details>

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).

## Quick Start

```bash
# Start Claude Code
claude

# Generate an image
/banana generate "a hero image for a coffee shop website"

# Edit an existing image
/banana edit ~/photo.png "remove the background"

# Multi-turn creative session
/banana chat

# Browse 2,500+ prompt database
/banana inspire
```

Claude will ask about your brand, select the right domain mode (Cinema, Product, Portrait, Editorial, UI, Logo, Landscape, Infographic, Abstract, Presentation), construct a detailed prompt with lighting and composition, set the right aspect ratio, and generate.

![Banana Claude in action](screenshots/banana-claude-skillcommand.gif)

## Commands

| Command | Description |
|---------|-------------|
| `/banana` | Interactive -- Claude detects intent and guides you |
| `/banana generate <idea>` | Full Creative Director pipeline |
| `/banana edit <path> <instructions>` | Intelligent image editing |
| `/banana chat` | Multi-turn visual session (maintains consistency) |
| `/banana inspire [category]` | Browse 2,500+ prompt database |
| `/banana batch <idea> [N]` | Generate N variations (default: 3) |
| `/banana setup` | Configure MCP and API key |
| `/banana setup replicate` | Configure Replicate API token (alternative backend) |
| `/banana preset [list\|create\|show\|delete]` | Manage brand/style presets |
| `/banana cost [summary\|today\|estimate]` | View cost tracking and estimates |

## How It Works

![Creative Director Pipeline](screenshots/pipeline-flow.webp)

## What Makes This Different

- **5-Input Creative Brief** -- Gathers Purpose, Audience, Subject, Brand, and References before generating
- **Domain Expertise** -- Selects the right creative lens (Cinema, Product, Portrait, Editorial, UI, Logo, Landscape, Infographic, Abstract, Presentation)
- **5-Component Prompt Formula** -- Constructs prompts with Subject + Action + Location/Context + Composition + Style (includes lighting)
- **Start with Intent, Refine with Specs** -- Two-phase prompting using the PEEL strategy for iterative refinement
- **Edit-First Workflow** -- 90% of refinements edit the image rather than regenerating from scratch
- **Brand Style Guides** -- Rich preset system with background styles, motifs, keywords, do's/don'ts, and prompt suffixes
- **Presentation Mode** -- Two options: complete slides with rendered text, or clean backgrounds for layering
- **Prompt Adaptation** -- Translates patterns from a 2,500+ curated prompt database to Gemini's natural language format
- **Post-Processing** -- Crops, removes backgrounds, converts formats, resizes for platforms
- **Batch Variations** -- Generates N variations with Literal/Creative/Premium prompt styles
- **Session Consistency** -- Maintains character/style across multi-turn conversations with progressive enhancement
- **Triple Fallback** -- MCP -> Direct Gemini API -> Replicate for maximum availability
- **4K Resolution Output** -- Up to 4096×4096 with `imageSize` control
- **14 Aspect Ratios** -- Including ultra-wide 21:9 and extreme 8:1 for banners

## The 5-Component Prompt Formula

![Prompt Formula](screenshots/reasoning-brief.webp)

Instead of sending "a cat in space" to Gemini, Claude constructs:

> A medium shot of a tabby cat floating weightlessly inside the cupola module
> of the International Space Station, paws outstretched toward a floating
> droplet of water, Earth visible through the circular windows behind. Soft
> directional light from the windows illuminates the cat's fur with a
> blue-white rim light, while the interior has warm amber instrument panel
> glow. Captured with a Canon EOS R5, 35mm f/2.0 lens, slight barrel
> distortion emphasizing the curved module interior. In the style of a
> National Geographic cover story on the ISS, with the sharp documentary
> clarity of NASA mission photography.

**Components used:** Subject (tabby cat, physical detail) → Action (floating, paw gesture) → Location/Context (ISS cupola, Earth visible) → Composition (medium shot, curved framing) → Style (Canon R5, National Geographic documentary, directional window light + amber instruments)

## Domain Modes

![Domain Modes](screenshots/domain-modes.webp)

| Mode | Best For | Example |
|------|----------|---------|
| **Cinema** | Dramatic, storytelling | "A noir detective scene in a rain-soaked alley" |
| **Product** | E-commerce, packshots | "Photograph my handmade candle for Etsy" |
| **Portrait** | People, characters | "A cyberpunk character portrait for my game" |
| **Editorial** | Fashion, lifestyle | "Vogue-style fashion shot for my brand" |
| **UI/Web** | Icons, illustrations | "A set of onboarding illustrations" |
| **Logo** | Branding, identity | "A minimalist logo for a tech startup" |
| **Landscape** | Backgrounds, wallpapers | "A misty mountain sunrise for my desktop" |
| **Infographic** | Data, diagrams | "Visualize our Q1 sales growth" |
| **Abstract** | Generative art, textures | "Voronoi tessellation in neon gradients" |
| **Presentation (Complete)** | Finished slides with text | "Title slide with 'DIGITAL INNOVATION' headline" |
| **Presentation (Background)** | Slide backgrounds for layering | "Dark premium background for keynote deck" |

## Presentation Mode

Presentation mode has two generation options designed for real-world slide workflows:

**Complete Slide** -- The model renders headline and body text directly in the image. Nano Banana 2's text rendering (94% accuracy under 25 characters) produces finished slides ready to use as-is. Best for title slides, quote slides, and simple content layouts.

**Background Only** -- Produces clean backgrounds with intentional negative space where text and logos will be added in Keynote, PowerPoint, or Google Slides. The prompt explicitly states "NO text, NO logos, NO labels" to prevent the model from generating unwanted artifacts.

> **Why no logos in prompts?** Gemini interprets every word literally. "Reserve space for logo" becomes "generate a logo here." The correct approach is describing the area as "clean negative space" or "simple uncluttered background," then compositing the logo as a separate layer in your presentation software where you have pixel-perfect control.

## Brand Style Guides

Enhanced presets for project-wide visual consistency. Create a brand style guide once, and every generated image inherits the brand's visual language:

```bash
# Create a brand style guide
/banana preset create premium-brand \
  --colors "#000000,#FFC000,#FFFFFF" \
  --style "premium dark photography, dramatic lighting, gold accents" \
  --mood "confident, innovative, premium" \
  --visual-motifs "geometric network pattern in silver at 30% opacity" \
  --prompt-suffix "Premium dark aesthetic with gold accents, dramatic lighting." \
  --do-list "Use negative space,High contrast,Keep patterns subtle" \
  --dont-list "No busy backgrounds,No more than 2 accent colors"

# Use it
/banana generate "title slide for digital innovation keynote"
# Claude automatically loads the brand guide and applies it
```

Brand Style Guide fields are all optional -- simple presets (just colors + style) continue to work exactly as before.

## Replicate Backend

An alternative API backend using `google/nano-banana-2` on Replicate. Useful when:
- MCP server is unavailable or not configured
- You prefer simpler auth (Replicate token vs. Google Cloud setup)
- You need webhook/async processing

```bash
# Configure Replicate
/banana setup replicate

# The fallback chain handles the rest automatically:
# 1. MCP (primary) -> 2. Direct Gemini API -> 3. Replicate
```

## Models

| Model | ID | Notes |
|-------|----|-------|
| Flash 3.1 (default) | `gemini-3.1-flash-image-preview` | Fastest, newest, 14 aspect ratios, up to 4K |
| Flash 2.5 | `gemini-2.5-flash-image` | Stable fallback |

## Architecture

```
banana-claude/                         # Claude Code Plugin
├── .claude-plugin/
│   ├── plugin.json                    # Plugin manifest
│   └── marketplace.json               # Marketplace catalog
├── skills/banana/                     # Main skill
│   ├── SKILL.md                       # Creative Director orchestration (v1.5)
│   ├── references/
│   │   ├── prompt-engineering.md      # 5-component formula, domain modes, PEEL strategy
│   │   ├── gemini-models.md           # Model specs, resolution tables, input limits
│   │   ├── mcp-tools.md              # MCP tool parameters and responses
│   │   ├── replicate.md              # Replicate backend API reference
│   │   ├── post-processing.md        # ImageMagick/FFmpeg pipelines, green screen
│   │   ├── cost-tracking.md          # Pricing table, usage guide
│   │   └── presets.md                # Brand Style Guide schema and examples
│   └── scripts/
│       ├── setup_mcp.py              # Configure MCP + Replicate
│       ├── validate_setup.py         # Verify installation
│       ├── generate.py               # Direct Gemini API fallback -- generation
│       ├── edit.py                   # Direct Gemini API fallback -- editing
│       ├── replicate_generate.py     # Replicate API fallback -- generation
│       ├── replicate_edit.py         # Replicate API fallback -- editing
│       ├── cost_tracker.py           # Cost logging and summaries
│       ├── presets.py                # Brand Style Guide management
│       └── batch.py                  # CSV batch workflow parser
└── agents/
    └── brief-constructor.md           # Subagent for prompt construction
```

## Requirements

- [Claude Code](https://github.com/anthropics/claude-code)
- Node.js 18+ (for npx)
- Google AI API key (free tier: ~5-15 RPM / ~20-500 RPD, cut ~92% Dec 2025)
- ImageMagick (optional, for post-processing)

## Uninstall

**Plugin:**

```shell
/plugin uninstall banana-claude@banana-claude-marketplace
```

**Standalone:**

```bash
bash banana-claude/install.sh --uninstall
```

## Upstream Tracking

This fork extends [AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude). To check for upstream changes:

```bash
git fetch upstream
git diff upstream/main   # see what changed
git merge upstream/main  # integrate selectively
```

## License

MIT License -- see [LICENSE](LICENSE) for details.

---

Originally built for Claude Code by [@AgriciDaniel](https://github.com/AgriciDaniel). Extended with Replicate backend, Presentation mode, Brand Style Guides, and research-driven prompt improvements.
