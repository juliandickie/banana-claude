# Video Prompt Engineering Reference

> Load this when constructing video prompts or when the user asks about
> video prompting techniques. Do NOT load at startup.
>
> Based on Google's 2026 "Ultimate Prompting Guide for VEO 3.1."

## The 5-Part Video Prompt Framework

Write as natural narrative prose -- NEVER as keyword lists. Each video prompt should include all 5 parts.

### Part 1 -- CAMERA

Shot type and movement. Use professional cinematography language.

**Shot types:** establishing wide, medium shot, close-up, extreme close-up, over-the-shoulder, bird's-eye, worm's-eye, Dutch angle, POV

**Camera movements:**
- **Dolly:** Camera physically moves closer/farther ("slow dolly forward")
- **Tracking:** Camera follows moving subject laterally ("tracking shot alongside")
- **Pan:** Horizontal sweep ("slow pan left across skyline")
- **Tilt:** Vertical sweep ("tilt up from feet to face")
- **Crane:** Vertical arc with reveal ("crane shot rising above the crowd")
- **Zoom:** Lens focal change ("slow zoom into the subject's eyes")
- **Static:** No movement ("locked-off tripod shot")
- **Handheld:** Natural camera shake ("handheld following the action")

**Performance notes:** Zooms have higher success rates than dollies. Lateral tracking works 68% of the time. Start simple, iterate.

**Good:** "Slow dolly forward through the glass door, transitioning from exterior to interior in a single continuous take"
**Bad:** "camera moves"

### Part 2 -- SUBJECT

Who or what is in frame. Same specificity as image prompts. Include motion state.

**Good:** "A woman in her 30s with auburn hair in a loose bun, wearing a cream linen apron over a navy henley, flour-dusted hands shaping sourdough"
**Bad:** "a baker"

### Part 3 -- ACTION

What happens during the clip. Must be completable within 4-8 seconds. One dominant action per clip.

**Good:** "She lifts the shaped dough and places it gently into a banneton basket, pressing the surface smooth with her palm"
**Bad:** "she bakes bread" (too broad for 8 seconds)

**Timing rules:**
- 4s: Single gesture, reaction, or beat
- 6s: One action with follow-through
- 8s: One complete micro-story (setup + action + result)

### Part 4 -- SETTING

Location, atmosphere, time of day. Include environmental audio cues.

**Good:** "Inside a warm artisan bakery at dawn, golden light streaming through flour-dusted windows, wooden shelves stacked with cooling loaves"
**Bad:** "bakery, morning"

### Part 5 -- STYLE + AUDIO

Film style, lighting, color grade, AND audio elements. Audio is unique to video.

**Style anchors:** "Shot on ARRI Alexa 65 with Cooke S7/i lenses, warm Kodak Vision3 250D color science, shallow depth of field. Documentary-style like a Chef's Table episode."

**Audio elements (include at least one):**
- **Dialogue:** `She says, "Almost there."` (in quotes)
- **SFX:** `SFX: soft thud of dough hitting the counter, flour puffing into the air`
- **Ambient:** `Quiet hum of the oven, distant birdsong through an open window`
- **Music:** `Gentle acoustic guitar melody in the background`

## Proven Video Prompt Templates

### Product Reveal
```
A slow dolly-in shot revealing [PRODUCT] on [SURFACE], [LIGHTING SETUP].
The camera orbits 45 degrees as [DYNAMIC ELEMENT: steam rises / light
catches the surface / condensation forms]. [PRODUCT DETAIL prominently
visible]. SFX: [RELEVANT SOUND]. Shot on [CAMERA] with [LENS],
[COLOR GRADE]. In the style of an Apple product film.
```

### Story-Driven (Brand Narrative)
```
Medium tracking shot following [CHARACTER DESCRIPTION] as they
[ACTION] through [SETTING] at [TIME OF DAY]. [MICRO-DETAIL about
texture/expression/movement]. [CHARACTER] says, "[DIALOGUE]."
SFX: [ENVIRONMENTAL SOUNDS]. Ambient: [BACKGROUND ATMOSPHERE].
Shot on [CAMERA], [LENS SPEC], [LIGHTING]. Reminiscent of
[PUBLICATION/DIRECTOR] style with [COLOR GRADE].
```

### Social Short (4 seconds)
```
Dynamic handheld close-up of [SUBJECT] [QUICK ACTION] with
[ENERGETIC ELEMENT]. Fast rack focus from [FOREGROUND] to
[BACKGROUND]. SFX: [PUNCHY SOUND EFFECT]. Shot with [CAMERA]
at [HIGH FPS for slow-mo feel], [VIBRANT COLOR GRADE].
```

### Environment Reveal
```
Aerial drone shot descending slowly over [LOCATION], revealing
[ARCHITECTURAL DETAIL] as the camera pushes forward. Golden hour
light casting [SHADOW PATTERN] across [SURFACE]. Ambient:
[ENVIRONMENTAL SOUNDSCAPE]. Shot with [DRONE CAMERA], [WIDE LENS],
[CINEMATIC COLOR GRADE]. In the style of a [TRAVEL BRAND] campaign.
```

## Character Consistency Across Shots

For multi-shot sequences, repeat identity descriptors EXACTLY:

**Scene bible format:**
```
IDENTITY: Same 30-year-old woman with auburn bob, denim jacket, silver locket
SETTING: Same rainy neon-lit alley, wet cobblestones reflecting neon signs
CAMERA: 35mm, f/2.8
GRADE: Teal-and-magenta color grade, high contrast
```

Copy-paste the scene bible into every shot prompt. VEO maintains better consistency with identical phrasing than with paraphrased descriptions.

## Banned Keywords (Same as Image)

NEVER use: "8K," "masterpiece," "ultra-realistic," "high resolution"
These degrade output quality. Use prestigious context anchors instead.

## Safety Rephrase for Video

VEO has stricter frame-by-frame safety scanning. Common trigger words:
- "fire" → "flames" or "warm glow"
- "shot" → "filmed" or "captured"
- "strike" → "impact" or "contact"
- "gun" → describe the object differently
- "blood" → "red liquid" or avoid

If safety-blocked, rephrase using abstraction, artistic framing, or metaphor. Max 3 attempts with user approval.

## Discoveries and Tips from Real Sequence Production

This section collects prompt engineering insights discovered while producing actual video sequences. Each tip is labeled with its evidence level so you know which to trust and which still need testing.

**Evidence levels:**
- ✅ **Demonstrated** — observed in real generation output, bug or improvement reproducible
- 🔬 **Unverified** — reasonable guess from general knowledge or one-shot observation, not yet eval-tested
- 📊 **Measured** — backed by a formal eval run with multiple samples

### Scene bible anchors: lock language across prompts

✅ **Demonstrated** (coffee shop 30s sequence, April 2026)

When the same element must appear across multiple shots, use **identical phrasing, not paraphrases**. The model produces more consistent results when prompts share exact language than when they describe the same thing in different words.

**Example from the coffee shop sequence:**

Every shot that showed the finished coffee included the phrase `"cream-colored ceramic cup with thick curved handle"` — verbatim. The result was cup continuity across Shots 3 and 4 that would not have been possible with paraphrased descriptions like "ceramic mug" in one prompt and "coffee cup" in another.

**Recommended scene bible format** (copy-paste at the top of each shot prompt in a sequence):

```
SCENE BIBLE (identical across all shots):
- Character: same friendly barista, early 30s, short brown hair, charcoal apron over cream henley
- Product: cream-colored ceramic cup with thick curved handle, simple white saucer
- Location: Golden Bean Cafe interior, warm pendant lights overhead
- Grade: warm Kodak Vision3 250D color grade, shallow depth of field
- Camera package: RED V-Raptor
```

Then the shot-specific prompt below uses those exact phrases.

### Off-frame composition beats forcing all elements visible

✅ **Demonstrated** (coffee shop Shot 3 — three-hands bug and fix)

When a shot logically involves multiple hands or characters but the framing is tight, **explicitly permit elements to be out of frame** rather than demanding everything be visible. The model will invent extra limbs or actors to satisfy impossible framings.

**The bug we caught:**

Asking for a tight macro close-up of latte art being poured produced a frame with **three visible hands**: one pouring, one holding the cup, and a third hand cradling the cup from the left. The model could not fit the pour hand + cup hand into a tight macro frame without inventing extra anatomy.

**The fix:**

Rewrote the prompt to explicitly say: `"EXACTLY ONE VISIBLE HAND — the right hand holding the cup handle. The pitcher pouring milk is in frame but the hand holding it is off-frame above the top edge of the shot."` This gave the model permission to crop the pour hand out, and the resulting frame was anatomically correct.

**General principle:** If a shot description implies more visible elements than will fit in the framing, name which ones should be off-frame. Don't leave it ambiguous.

### Explicit percentage framing for camera moves

✅ **Demonstrated** (coffee shop Shot 1 — two attempts at the end frame)

Models interpret spatial language very conservatively. Vague instructions like "closer" or "zoomed in" produce minimal changes from the reference. Specific percentage claims produce dramatic changes.

**What didn't work (first attempt):**

Using image-to-image mode with the prompt `"the camera has dollied forward. We are now closer to the corner entrance"` produced a near-identical image with only the smallest apparent zoom.

**What worked (second attempt):**

Text-only generation with the prompt `"The heavy wooden double door DOMINATES THE FRAME, filling approximately 60-70% of the vertical space, centered in the composition"` produced a dramatic arrival shot with the door as the clear focal element.

**General principle:** When describing framing, give the model a percentage or a concrete spatial claim (e.g., "subject occupies the left third", "sky fills the upper half"). Avoid abstract qualifiers like "close", "wide", "more of the scene visible".

### Image-to-image has conservatism bias

✅ **Demonstrated** (coffee shop Shots 1, 3, 4)

When you pass an image as a reference alongside a text prompt, the model anchors heavily on the existing geometry and makes minimal changes — excellent for continuity, bad for dramatic camera moves. Use the right mode for the right job:

| Use image-reference generation when... | Use text-only generation when... |
|---|---|
| Character identity must persist across shots | Camera is moving dramatically within a shot |
| An object must look identical between frames | Framing is changing significantly (wide → close-up) |
| You want minor framing adjustments | Establishing → product reveal transitions |
| Matching color grade and lighting style | The end frame should feel like a different shot |
| Cross-shot prop continuity (e.g., the cup in Shot 3 end → Shot 4 start) | Opening/closing shots where end frame is uncommitted |

**Why:** image-reference mode is essentially answering "what small change can I make to this image?" while text-only is answering "what would this scene look like described from scratch?" Both are useful, but they're not interchangeable.

### ALL CAPS for anatomical and count constraints

🔬 **Unverified** — based on general knowledge of how LLMs interpret emphasis; not eval-tested in this plugin

When specifying constraints that must not be violated (number of hands, number of people, prohibited elements), ALL CAPS phrasing appears more likely to be respected than lowercase equivalents. Examples:

- "EXACTLY ONE VISIBLE HAND — NO additional hands or arms"
- "ONE PERSON in the frame, no background extras"
- "NO text visible anywhere in the image"

**Caveat:** this has not been systematically tested in the nano-banana-studio plugin. It's included here as a common practice that worked in the coffee shop Shot 3 regeneration, but a single success is not evidence. Future eval work should compare ALL CAPS vs lowercase constraint phrasing on identical prompts and measure compliance rates.

### Real camera brand names anchor color and grade

✅ **Demonstrated** (coffee shop sequence)

Specifying a real camera body and lens produces more consistent color and depth-of-field results than generic qualifiers.

**What worked:**

Every shot in the coffee shop sequence used `"Shot on a RED V-Raptor with a 35mm lens at f/2.8"` (or 50mm, 100mm macro depending on the shot). Combined with `"warm Kodak Vision3 250D color grade"`, this produced a visually coherent look across shots generated minutes apart.

**What didn't work in earlier experiments:**

Generic phrases like "cinematic" or "shallow depth of field" produced wildly varying interpretations — sometimes hyper-stylized, sometimes flat, sometimes wrong aspect ratios for the requested lens.

**Recommended anchor vocabulary:**

| Element | Good | Bad |
|---|---|---|
| Camera body | RED V-Raptor, ARRI Alexa 65, Sony Venice 2 | "cinema camera", "pro video" |
| Lens | 35mm at f/2.8, 100mm macro at f/2.0, 50mm at f/1.4 | "wide shot", "close-up lens" |
| Film stock / color | Kodak Vision3 250D, Kodak Vision3 500T, Fuji Eterna | "warm tones", "cinematic grade" |
| Reference style | "Nespresso campaign aesthetic", "Chef's Table documentary" | "professional look", "high quality" |

### Audio is three distinct things, not one

✅ **Demonstrated** (this tip came from reviewing the sequence plan structure)

VEO 3.1 generates audio natively, but not all audio types are handled the same way. Separate these in your prompts:

- **Ambient** — background atmosphere (cafe murmur, birdsong, wind). VEO handles this reliably. Put it in your prompt as plain description: `"Ambient: quiet cafe murmur, soft customer conversation in the distance."`
- **SFX (Sound Effects)** — specific action-matched sounds (door closing, cup settling, milk pouring). VEO handles this reliably. Prefix with "SFX:" to signal the distinction: `"SFX: metallic tamping sound, firm click of portafilter locking into place."`
- **Dialogue** — characters speaking on camera. VEO generates this with lip-sync but with strict limits: 8-second max per clip, English only for reliable results, short phrases work best (3-8 words). Put the line in quotation marks: `'A woman says, "Welcome to our cafe," as she places the latte on the counter.'`
- **Narration/Voiceover** — **NOT** a VEO prompt element. Narration is added in post-production over the finished video. Don't include narration text in VEO prompts. Instead, decide narration strategy at the sequence level and add the audio track via FFmpeg after stitching.

### Architectural tip: not every shot needs an end frame

✅ **Demonstrated** (coffee shop Shot 1)

When a shot cuts directly to an unrelated next shot (e.g., exterior → interior), there's no continuity constraint on how the first shot ends. In that case, you don't need to generate an end frame for the storyboard at all. Let VEO interpolate its own end frame from the start frame + a motion description in the prompt.

**Advantages:**

- Avoids the continuity problem of trying to match two different framings of the same scene
- Frees VEO to execute dramatic camera moves that would be hard to hit a specific target frame for
- Saves one storyboard frame's cost ($0.08)
- Saves iteration time (no review round on the end frame)

**When to use start-frame-only mode:**

| Shot type | End frame needed? |
|---|---|
| Establishing shot that cuts to different scene | ❌ No — let VEO interpolate |
| Within-scene shot where next shot continues the action | ✅ Yes — anchor the cut point |
| Product reveal that cuts to finished product on table | ❌ No — the cut already breaks continuity |
| Close-up that cuts to wider shot of the same subject | ✅ Yes — the subject must be in the same state |
| Cinematic transition/fade shot | ❌ No — let VEO control the ending |

**How to invoke:** In `video_generate.py`, pass `--first-frame PATH` without `--last-frame`. VEO interpolates its own end frame from the motion description in the prompt.

### Hybrid storyboard generation: text-only for first frames, image-reference for continuations

✅ **Demonstrated** (coffee shop Shots 3 and 4)

Best practice for multi-shot sequence storyboards:

1. **First frame of each shot** — generate with text-only prompt (full control over composition, dramatic framing)
2. **End frame of same shot** — generate with image-reference prompt using the first frame as the reference (automatic style and geometry matching)
3. **First frame of a shot that continues from a previous shot** — generate with image-reference prompt using the previous shot's end frame (cross-shot prop/character continuity)

**Example from coffee shop:**

- Shot 3 start: text-only generation (full control over the cup composition, pitcher angle, hand position)
- Shot 3 end: image-reference from Shot 3 start (same cup, same hand, rosetta now completed, pitcher off-frame)
- Shot 4 start: image-reference from **Shot 3 end** (same cup persists across the cut — crucial handoff)
- Shot 4 end: image-reference from Shot 4 start (same cup on same table, camera pulled back)

The image-reference chaining across the Shot 3 → Shot 4 cut is the critical move — it guarantees the cup looks identical on both sides of an editorial cut, which is the hardest thing to achieve with text-only prompting.

---

*This section grows over time as more sequences are produced. When you discover a new tip, add it here with an evidence level. When you test an unverified tip, promote it to demonstrated or measured based on results.*
