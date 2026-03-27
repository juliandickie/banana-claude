# CLAUDE.md -- Development context for banana-claude

This file is read by Claude Code when working inside this repository.

## What this repo is

`banana-claude` is a Claude Code **plugin** that enables AI image generation
using Google's Gemini Nano Banana models via MCP. Claude acts as a Creative
Director: it interprets intent, selects domain expertise, constructs
optimized prompts, and orchestrates Gemini API calls.

## Plugin structure

This repo follows the official Claude Code plugin layout:
- `.claude-plugin/plugin.json` -- Plugin manifest
- `.claude-plugin/marketplace.json` -- Marketplace catalog for distribution
- `skills/banana/` -- The main skill (SKILL.md + references + scripts)
- `agents/` -- Subagents (brief-constructor)

## Model status (as of March 2026)

- `gemini-3.1-flash-image-preview` -- **Active default.** Nano Banana 2.
- `gemini-2.5-flash-image` -- **Active.** Nano Banana original. Budget/free tier.
- `gemini-3-pro-image-preview` -- **DEAD.** Shut down March 9, 2026. Do not use.

## How to test changes

1. Test as plugin: `claude --plugin-dir .`
2. Or install standalone: `bash install.sh`
3. Test basic generation: `/banana generate "a red apple on a white table"`
4. Test domain routing: `/banana generate "product shot for headphones"`
5. Test editing: `/banana edit [path] "make the background blurry"`
6. Verify output image files exist at the logged path
7. Check cost log if cost_tracker.py is active

## File responsibilities

| File | Purpose |
|---|---|
| `skills/banana/SKILL.md` | Main orchestrator. Edit to change Claude's behavior. |
| `skills/banana/references/gemini-models.md` | Model roster, routing table, resolution defaults. Update when Google releases new models. |
| `skills/banana/references/prompt-engineering.md` | The prompt construction system. Update when Google publishes new guidance. |
| `skills/banana/references/mcp-tools.md` | API parameter reference. Update when Google changes the API. |
| `skills/banana/scripts/generate.py` | Direct API fallback for generation. Uses urllib.request (stdlib). |
| `skills/banana/scripts/edit.py` | Direct API fallback for editing. Uses urllib.request (stdlib). |
| `agents/brief-constructor.md` | Subagent for prompt construction. |

## Scripts use stdlib only

The fallback scripts (`generate.py`, `edit.py`) use Python's `urllib.request`
to call the Gemini REST API directly. They have ZERO pip dependencies by design.
Do NOT add `google-genai` or `requests` as dependencies -- the stdlib approach
ensures the skill works on any system with Python 3.6+.

## Key constraints

- `imageSize` parameter values must be UPPERCASE: "1K", "2K", "4K". Lowercase fails silently.
- Gemini generates ONE image per API call. There is no batch parameter.
- No negative prompt parameter exists. Use semantic reframing in the prompt.
- `responseModalities` must explicitly include "IMAGE" or the API returns text only.
- NEVER use banned keywords in prompts: "8K", "masterpiece", "ultra-realistic", "high resolution" -- these degrade output quality. Use prestigious context anchors instead (see prompt-engineering.md).

## Distribution

### Plugin marketplace (primary)

Users install via:
```shell
/plugin marketplace add AgriciDaniel/banana-claude
/plugin install banana-claude@banana-claude-marketplace
```

### Official Anthropic marketplace

Submission pending via [claude.ai/settings/plugins/submit](https://claude.ai/settings/plugins/submit).
Once accepted, users install with:
```shell
/plugin install banana-claude@claude-plugins-official
```

### Standalone install (legacy)

Still supported via `install.sh` for users not on the plugin system.

## Versioning

Version must be bumped in ALL 4 files when releasing:
1. `.claude-plugin/plugin.json` -- `version` field (plugin system reads this)
2. `skills/banana/SKILL.md` -- `metadata.version` in frontmatter
3. `README.md` -- version badge
4. `CITATION.cff` -- `version` and `date-released`

Also add a new section in `CHANGELOG.md`.

Do NOT set version in `marketplace.json` -- it conflicts with `plugin.json` (plugin.json always wins silently per Anthropic docs).

## Plugin development notes

- `.claude-plugin/` contains ONLY `plugin.json` and `marketplace.json`. Never put skills, agents, or commands in this directory.
- `skills/` and `agents/` must be at plugin root (not inside `.claude-plugin/`).
- Plugin variable `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin cache directory. Use for hook commands and MCP configs.
- SKILL.md uses `${CLAUDE_SKILL_DIR}` for script paths -- this is a semantic marker Claude interprets based on context. Works in both plugin and standalone mode.
- Relative paths in SKILL.md (`references/`, `scripts/`) resolve relative to SKILL.md location. These work in both modes.
- Test locally with `claude --plugin-dir .` (loads plugin without installing).
- After changes, run `/reload-plugins` in Claude Code to pick up updates without restarting.
- Validate with `claude plugin validate .` or `/plugin validate .` before releasing.
