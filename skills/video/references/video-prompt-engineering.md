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
