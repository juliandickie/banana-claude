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
- Music quality varies — for important pieces, replace the audio with the v3.7.1 ElevenLabs pipeline (see below)
- Audio cannot be independently controlled after generation (it's baked into the MP4) — but it CAN be replaced wholesale via the v3.7.1 audio swap workflow
- If audio quality is critical, use the v3.7.1 audio replacement pipeline (`scripts/elevenlabs_audio.py pipeline`) which strips VEO's baked audio and substitutes a continuous TTS + Eleven Music + ducked mix track

---

## Discoveries from real production (v3.7.1+ — strategic reset session)

The following findings came from spikes 1-3 of the strategic reset session
(2026-04-14). Each is empirically verified and reproducible. The session also
shipped the `elevenlabs_audio.py` audio replacement pipeline (v3.7.1) which
solves the multi-clip stitching artifacts uncovered here. See
`references/audio-pipeline.md` for the full pipeline architecture.

### F1. VEO 3.1 voice character anchoring works across separate generations
<!-- verified: 2026-04-14 -->
When the same voice descriptor is included in multiple prompts (e.g.
`"a narrator with a warm baritone voice and a slight British accent"`),
VEO produces voices with consistent gender, age, accent, and emotional
register across all separately-generated clips. **Voice character drift is
NOT a real failure mode** when descriptors are locked. This invalidates
the early v3.7.0 ROADMAP assumption that voice-changer post-processing
was needed to fix multi-clip drift.

### F2. VEO has a "delivery mode drift" failure mode when narration is too short
<!-- verified: 2026-04-14 -->
When narration is too brief for the clip duration, VEO non-deterministically
chooses to fill the time by either (a) lengthening pauses with music silence
OR (b) **stretching delivery via singing**. Same voice character, different
mode of delivery. **The fix is line-length calibration**, not voice
replacement. Target ~75-100% fill of the clip duration at the target voice's
WPM:

```
target_word_count = duration_seconds × (voice_wpm / 60)
```

Reference WPM values (see F8 for measurement context):
- VEO native narrator: ~120 wpm → 16 words for 8s
- Daniel + eleven_v3: ~137 wpm → 18 words for 8s
- Nano Banana Narrator + eleven_v3: ~159 wpm → 21 words for 8s

### F3. VEO stitched sequences have music-bed seams at clip boundaries
<!-- verified: 2026-04-14 -->
Each separately-generated VEO clip produces its own music intro/outro
envelope independently. When clips are FFmpeg-concatenated, the music has
audible seams every clip-duration. **This is the real "multi-clip drift"
problem** — not voice drift, but musical envelope drift across separately-
generated clips. The v3.7.1 pipeline solves this by replacing the entire
audio bed with continuous TTS + music + ducked mix.

### F4. VEO automatically applies side-chain ducking to narrated clips
<!-- verified: 2026-04-14 -->
When a clip has both narration and emergent background music, VEO
automatically ducks the music under the speech and raises it during gaps.
This is sophisticated editing behavior performed without being asked. **For
cases where you want pure dry voiceover, prompt explicitly:**
`"dry voiceover, no music"` to suppress the emergent music bed.

### F5. ElevenLabs v3 audio tags are open-ended, not whitelisted
<!-- verified: 2026-04-14 -->
The documented audio tag list in ElevenLabs' best-practices doc is labeled
"Non-Exhaustive" with explicit instructions to "infer similar, contextually
appropriate tags." Empirical confirmation: undocumented `[reverent]`
produced a 20.7% slower delivery than the same line untagged, while
`[contemplative]` and `[wistful]` produced smaller but real variations.
**For prompt-construction:** accept any bracketed tag, don't validate
against a whitelist. Test undocumented tags before relying on them in production.

### F6. ElevenLabs Music API blocks named-creator/brand references
<!-- verified: 2026-04-14 -->
Prompts containing names like "Annie Leibovitz" or "BBC Earth" return HTTP
400 with `bad_prompt` error code and a `prompt_suggestion` field showing a
sanitized version. **This is music-API-specific** — image generation prompts
welcome creator names, music does not. **For v3.7.x music prompt-construction:
strip named-creator references before sending. Use generic descriptors only.**

### F7. ElevenLabs Voice Design produces more consistent results with `should_enhance=true`
<!-- verified: 2026-04-14 -->
Across two design runs (3 previews each, identical input description), the
enhanced run had ~50% less duration variance across the 3 candidates AND ran
~7% faster on average. **For voice design that needs to be reproducible:**
use `should_enhance=true`. **For voice design where you want maximum
interpretation freedom and slower documentary register:** use the default
`should_enhance=false`.

### F8. Voice character affects TTS pacing independently of content, tags, and model
<!-- verified: 2026-04-14 -->
The same script content (with identical `eleven_v3` model and identical
audio tags) ran at:
- Daniel (off-the-shelf): ~137 wpm
- Nano Banana Narrator (custom-designed): ~159 wpm

**16% pacing difference attributable purely to voice character.** For
v3.7.0 line-length calibration, the `narrator_wpm` constant must be
measured per voice, not just per model.

### F9. VEO 3.1 Lite tier is broadcast-quality for narrated documentary footage
<!-- verified: 2026-04-14 -->
All spike 1-3 VEO Lite clips were rated 5/5 by the user with "ship it"
verdicts. The previous `veo-models.md` framing of Lite as "draft only,
upgrade to Standard for hero shots" is overly conservative. **For nature
documentary, talking-head, and narration-focused content, Lite is
publishable.** Reserve Standard for shots with extreme detail.

### F10. The `[exhales]` audio tag produces an audible breath
<!-- verified: 2026-04-14 -->
Confirmed by listen-through. The exhale lands cleanly without being spoken
aloud as text. Pairs especially well with serious documentary register.

### F11. Selective capitalization in eleven_v3 produces audible emphasis
<!-- verified: 2026-04-14 -->
"COLD" in `"The river runs COLD here..."` was delivered with distinct
emphasis vs the lowercase version. Use sparingly — 1-2 capitalized words
per sentence at most.

### F12. Ellipses in eleven_v3 produce contemplative pauses
<!-- verified: 2026-04-14 -->
Five ellipses in a 32-second narration script slowed delivery from
~146 wpm (no ellipses) to ~137 wpm (with ellipses). The pauses sound
natural and deliberate. Use ellipses for "narrator beat" pacing in
documentary content.

### F13. Music model quality is uncorrelated with spec-sheet metrics at typical playback conditions
<!-- verified: 2026-04-14 -->
**Spike 4 (v3.7.2) tested 5 music providers** with the identical prompt:
Lyria 2, ElevenLabs Music, Stable Audio 2.5, MiniMax Music 1.5, Meta MusicGen.
The user listening verdict ranked them: **Lyria > ElevenLabs > MusicGen >
MiniMax > Stable Audio**. The most striking finding: Stable Audio had the
fastest generation (4.6s vs Lyria's 26s), competitive sample rate (44.1 kHz),
and the cleanest diffusion architecture, but was rated *worst* by the
listening test. Conversely, MusicGen (the 2-year-old open-source baseline)
beat the much newer MiniMax Music 1.5 because MusicGen was trained on
instrumental music while MiniMax was trained on songs with vocals — **domain
of training matters more than recency or spec sheets**.

**Generalizable principles:**
1. Audio gen model quality is NOT predictable from sample rate, bit rate, or
   model architecture — only subjective listening tests are valid evaluation.
2. Training data domain (instrumental vs vocal-song) matters more than model
   recency. A 2024 instrumental-trained model beats a 2025 song-trained model
   on instrumental tasks.
3. The spec-vs-quality decoupling means future model evaluations need empirical
   listening, not just benchmark comparisons. **Apply the strategic reset's
   "test before build" principle to every new music provider that gets added
   to the v3.7.x audio pipeline.**

v3.7.2 ships Lyria 2 as the default music source and ElevenLabs Music as the
alternative based on this empirical ranking. Stable Audio, MiniMax, and
MusicGen are NOT integrated. See `references/audio-pipeline.md` "Music sources"
section for the full bake-off table and decision matrix.

---

## v3.7.1 audio replacement pipeline (the recommended path for multi-clip sequences)

For multi-clip sequences where the seam issue from F3 matters, use the
v3.7.1 audio replacement pipeline instead of relying on VEO's emergent
audio. The pipeline strips the VEO audio entirely and replaces it with:

1. **Continuous TTS narration** (single ElevenLabs call, eleven_v3 model with audio tags)
2. **Continuous Eleven Music background bed** (single call, music_v1, instrumental)
3. **FFmpeg side-chain ducked mix** (apad pattern to extend narration to music length)
4. **Lossless audio swap into the video** (stream-copy video, AAC re-encode audio)

```bash
python3 skills/video/scripts/elevenlabs_audio.py pipeline \
  --video stitched-sequence.mp4 \
  --text "Each year... the seasons change across this valley, painting the forest in red and gold. [exhales] The river runs COLD here..." \
  --music-prompt "Cinematic nature documentary background score, slow contemplative warm orchestral strings with soft piano, instrumental only, no vocals, around 70 BPM" \
  --voice narrator \
  --out final.mp4
```

See `references/audio-pipeline.md` for the full architecture, voice design
flow, custom voice schema, FFmpeg parameter rationale, and prompt engineering
guidance for both TTS and Eleven Music.
