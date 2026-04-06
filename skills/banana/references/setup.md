# Setup, Install & Update Reference

> Load this when the user runs `/banana setup`, `/banana status`, `/banana update`,
> or asks how to install/share banana-claude.
>
> Guide conversationally. Do NOT run `setup_mcp.py` without arguments (the
> interactive `input()` prompt does not work in Claude Code's shell).

## `/banana setup` -- Google AI API Key (Primary)

Walk the user through this:

1. **Explain what they need:**
   "To generate images, you need a free Google AI API key. This lets Claude
   call Google's Gemini image generation models. No credit card required."

2. **Direct them to get the key:**
   "Go to https://aistudio.google.com/apikey and:
   - Sign in with your Google account
   - Click 'Create API Key'
   - Select any Google Cloud project (or create one -- it's free)
   - Copy the key (starts with `AIza...`)"

3. **Ask them to paste it:**
   "Paste your API key here and I'll configure everything."

4. **When they provide the key, run:**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/setup_mcp.py --key THE_KEY_THEY_GAVE
   ```

5. **Tell them to restart Claude Code** for the MCP server to load.

6. **Free tier info:** ~5-15 images/minute, ~20-500/day. Resets midnight Pacific.

## `/banana setup replicate` -- Replicate API (Optional Fallback)

1. **Explain the option:**
   "Replicate is an optional backup. If the primary Google API is unavailable,
   Banana Claude will automatically fall back to Replicate. It costs ~$0.05/image."

2. **Direct them to get the token:**
   "Go to https://replicate.com/account/api-tokens and:
   - Sign in (GitHub login works)
   - Click 'Create token'
   - Copy the token (starts with `r8_...`)"

3. **When they provide the token, run:**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/setup_mcp.py --replicate-key THE_TOKEN
   ```

## `/banana status` -- Check Installation & Keys

```bash
# Show version
grep 'version:' ${CLAUDE_SKILL_DIR}/SKILL.md | head -1

# Show git status (if in a git repo)
cd ${CLAUDE_SKILL_DIR}/../.. && git log --oneline -3 2>/dev/null

# Check API keys
python3 ${CLAUDE_SKILL_DIR}/scripts/setup_mcp.py --check
python3 ${CLAUDE_SKILL_DIR}/scripts/setup_mcp.py --check-replicate
```

## `/banana update` -- Pull Latest Version

```bash
cd ${CLAUDE_SKILL_DIR}/../.. && git pull origin main
```
Then tell the user to run `/reload-plugins` in Claude Code.

## Where Keys Are Stored

Both keys are saved to `~/.banana/config.json` (for fallback scripts) and the
Google key is also saved to `~/.claude/settings.json` (for the MCP server).
Keys never leave the user's machine.

## New User Guide

For first-time users, provide this quick start:

> **What is Banana Claude?**
> An AI image generation skill for Claude Code. You describe what you want,
> and Claude acts as Creative Director -- interpreting intent, selecting style,
> and generating images using Google's Gemini models.
>
> **Install in 3 steps:**
> ```bash
> git clone https://github.com/juliandickie/banana-claude.git ~/banana-claude
> claude --plugin-dir ~/banana-claude
> # Then in Claude Code: /banana setup
> ```
>
> **First image:** `/banana generate "a cozy coffee shop at golden hour"`

## Sharing with Friends

Copy-paste this message:

> **Want AI image generation in Claude Code?**
>
> 1. Get a free API key: https://aistudio.google.com/apikey
> 2. Run:
> ```bash
> git clone https://github.com/juliandickie/banana-claude.git ~/banana-claude
> claude --plugin-dir ~/banana-claude
> ```
> 3. In Claude Code: `/banana setup` (paste your API key)
> 4. Try it: `/banana generate "a sunset over mountains"`
>
> To update: `cd ~/banana-claude && git pull` then `/reload-plugins`
