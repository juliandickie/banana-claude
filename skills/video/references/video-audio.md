# Video Audio Prompting Reference

> Load this when the user asks about audio in video generation or when
> constructing prompts that need specific audio design.

## Overview

VEO 3.1 generates synchronized audio natively. Every video prompt should include at least one audio element. Audio is generated alongside the video — no separate audio synthesis step needed.

## Audio Types

### Dialogue

Use quotation marks around spoken words. Best for short phrases (under 10 words per clip).

```
A barista says, "Your latte is ready."
The narrator whispers, "Watch carefully."
A child exclaims, "Look at that!"
```

**Tips:**
- English only for reliable results
- Short sentences work best (3-8 words)
- Specify tone: "says warmly," "whispers urgently," "announces confidently"
- For conversations, separate into individual clips (one speaker per clip)
- Avoid multiple speakers in the same clip

### Sound Effects (SFX)

Prefix with "SFX:" for explicit sound design.

```
SFX: glass shattering on tile floor, sharp metallic echo
SFX: soft click of a camera shutter, film advance whir
SFX: heavy wooden door creaking open, hinges groaning
SFX: coffee beans pouring into a grinder, ceramic rattling
SFX: keyboard typing rapid bursts, mechanical key clicks
```

**Tips:**
- Be specific about material and surface (metal on concrete, glass on wood)
- Include reverb/echo context (empty warehouse echo, intimate room dampening)
- SFX timing auto-syncs to visual action
- Multiple SFX can layer: "SFX: footsteps on wet cobblestones, distant thunder"

### Ambient Sound

Describe the background soundscape naturally in the setting.

```
Quiet hum of the oven, distant birdsong through an open window
City traffic below, muffled through double-pane glass
Forest at dawn — crickets fading, first birds calling
Busy restaurant murmur, clinking glasses, jazz piano in the background
```

**Tips:**
- Ambient sets emotional tone — match to visual mood
- Layer: near sounds + distant sounds for depth
- Silence is valid: "Near-silence, only the faint hum of fluorescent lights"

### Music

Describe style, not specific songs. VEO generates original music.

```
Soft piano melody in the background, melancholic and sparse
Upbeat electronic beat with deep bass, building energy
Gentle acoustic guitar fingerpicking, warm and inviting
Orchestral swell building to a crescendo
Minimal ambient synth pads, ethereal and spacious
```

**Tips:**
- Describe mood + instrument + tempo
- "Building" or "fading" describe progression within the clip
- Music works best as background layer, not foreground
- Don't reference specific songs or artists

## Audio Design Patterns by Domain Mode

| Mode | Primary Audio | Secondary | Avoid |
|------|--------------|-----------|-------|
| **Product Reveal** | Subtle SFX on interaction | Ambient hum, music bed | Heavy dialogue |
| **Story-Driven** | Dialogue | Ambient, emotional music | Competing SFX |
| **Environment Reveal** | Rich ambient soundscape | Distant music | Close-up SFX |
| **Social Short** | Punchy SFX, hook dialogue | Trending music style | Ambient silence |
| **Cinematic** | Score + atmospheric SFX | Minimal dialogue | Busy ambient |
| **Tutorial/Demo** | Narration, click/tap SFX | Subtle music bed | Environmental noise |

## Audio Across Sequences

For multi-shot sequences, maintain audio consistency:
- **Same ambient base** across shots in the same location
- **Music bed** described identically in each shot (or omitted and added in post)
- **Dialogue** limited to the specific shot — don't carry conversations across cuts
- **Transition SFX** (whoosh, impact) only in transition shots

## Limitations

- English dialogue only for reliable quality
- Long dialogue (10+ words) may be truncated or garbled
- Music quality varies — consider adding music in post-production for important pieces
- Audio cannot be independently controlled after generation (it's baked into the MP4)
- If audio quality is critical, consider generating video without audio emphasis and adding audio in post
