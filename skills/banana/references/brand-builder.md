# Brand Builder Reference -- `/banana brand`

> Load this when the user runs `/banana brand`. Guide them conversationally
> through building a Brand Style Guide preset. Do NOT create the preset JSON
> manually -- use `presets.py create` with the appropriate flags.

## Overview

The brand builder creates a full 17-field Brand Style Guide preset through
a 4-phase conversational flow: gather sources → auto-extract → refine → preview and save.

## Phase 1: Gather Sources

Ask the user what brand materials they have available:

"Let's build your brand guide. Do you have any of these?"

1. **Website URL** -- "Share a URL and I'll analyze the visual style"
   - Navigate to the site using browser tools
   - Take screenshots of the homepage, an interior page, and any about/contact page
   - Extract colors from visible elements (headers, buttons, backgrounds, accents)
   - Note typography patterns (serif vs sans-serif, weight hierarchy)
   - Observe the overall visual style and mood

2. **Brand guidelines PDF or document** -- "Upload or share the file path"
   - Read the document
   - Extract specific hex colors, font names, spacing rules
   - Note any explicit do's/don'ts or brand voice guidelines

3. **Reference images or mood board** -- "Share image files or a folder"
   - Analyze dominant colors, lighting patterns, composition style
   - Identify recurring visual motifs or textures
   - Note the overall mood and energy level

4. **Start from scratch** -- "I'll ask some questions to build your brand guide"
   - Skip to Phase 3

Analyze ALL provided sources before moving to Phase 2. Combine findings from multiple sources.

## Phase 2: Auto-Extract

From whatever sources were provided, extract values for the 17-field schema.
Build a draft preset mentally (do not save yet). For each field:

| Field | How to extract |
|-------|---------------|
| `colors` | Pick 3-5 dominant hex values (primary, secondary, accent, background, text) |
| `style` | Describe the overall visual approach in one sentence |
| `typography` | Identify font weight hierarchy (headlines vs body) |
| `lighting` | Bright/dark, warm/cool, dramatic/subtle |
| `mood` | 2-4 emotional keywords |
| `visual_motifs` | Recurring patterns or textures with opacity suggestion |
| `background_styles` | 2-3 named variants (e.g., dark-premium, light-clean, gradient) |
| `prompt_keywords` | Categorize into aesthetic, mood, and photography keywords |
| `prompt_suffix` | Write a condensed 1-sentence brand description |
| `do_list` | 3-5 rules inferred from what the brand DOES |
| `dont_list` | 3-5 rules inferred from what the brand AVOIDS |
| `logo_placement` | Note where logos appear (e.g., "bottom-left, 15% of width") |
| `technical_specs` | Default ratio, resolution, color space |

If a field can't be determined from the source, mark it as "needs input" for Phase 3.

## Phase 3: Show & Refine

Present the extracted brand guide to the user in a clear format:

"Here's what I built from [your website / your documents / your images]:"

Show each field with its value. For fields marked "needs input", ask targeted questions:

Example questions (adapt based on what's missing):
- "I found these colors: #1A1A1A, #FFC000, #FFFFFF. Are there others?"
- "The style looks premium and editorial. Is that the right direction?"
- "For presentations, do you prefer dark backgrounds, gradients, or light?"
- "What visual elements are off-brand? Things to always avoid?"
- "What's a short phrase that captures this brand's visual identity?"

Let the user adjust any field. Continue until they confirm everything looks right.

## Phase 4: Preview & Save

1. **Generate a preview image** using the brand guide:
   - Use the constructed preset values to build a prompt
   - Generate a sample image (e.g., a product shot or presentation background)
   - Show the user: "Here's what images will look like with this brand guide"

2. **Get approval:**
   - If user approves → proceed to save
   - If user wants changes → adjust the values and regenerate

3. **Save the preset** using `presets.py create` with ALL fields:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/presets.py create BRAND_NAME \
     --colors "hex1,hex2,hex3" \
     --style "style description" \
     --typography "typography description" \
     --lighting "lighting description" \
     --mood "mood description" \
     --description "Brief brand description" \
     --ratio "16:9" \
     --resolution "2K" \
     --visual-motifs "motif description" \
     --prompt-suffix "Brand prompt suffix" \
     --do-list "rule1,rule2,rule3" \
     --dont-list "rule1,rule2,rule3"
   ```

   For JSON fields, use separate commands or construct inline:
   ```bash
   # If background-styles, prompt-keywords, or technical-specs are needed
   --background-styles '{"dark-premium":{"bg":"#000","text":"#FFF","accent":"#FFC000"}}'
   --prompt-keywords '{"aesthetic":["premium"],"mood":["confident"]}'
   --technical-specs '{"color_space":"sRGB","min_dpi":150}'
   ```

4. **Confirm:** Show the saved preset JSON and tell the user how to use it:
   "Your brand guide 'BRAND_NAME' is saved. It will be applied automatically
   when you mention it, or you can use it explicitly:
   `/banana generate 'product shot for headphones' (Claude will detect your brand)
   or reference it by name in your request."

## Example Presets

Example brand guide presets are bundled with the skill:
```bash
ls ${CLAUDE_SKILL_DIR}/presets/
```

To install an example as a starting point:
```bash
cp ${CLAUDE_SKILL_DIR}/presets/luxury-dark.json ~/.banana/presets/
```

Then run `/banana brand` to customize it, or use it as-is.

## Tips

- **Logo handling:** The `logo_placement` field records WHERE the logo goes, but
  it is NEVER mentioned in image prompts. The area is described as "clean negative
  space" instead. Logos are composited in presentation software.
- **prompt_suffix is the most powerful field** — it's appended verbatim to every
  prompt, ensuring consistent brand language without interpretation.
- **Start broad, refine narrow** — it's easier to edit a preset than to get
  everything perfect on the first try. Save it, generate some images, then
  run `/banana brand` again to refine.
