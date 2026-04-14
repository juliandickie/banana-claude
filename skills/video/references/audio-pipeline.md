# Audio Replacement Pipeline (v3.7.1 + v3.7.2)

This reference covers the multi-provider audio replacement architecture: why it
exists, how to use it, and the empirical findings from spikes 3 and 4 of the
strategic reset session that informed its design.

**Quick links:**
- Script: `skills/video/scripts/audio_pipeline.py` (renamed from `audio_pipeline.py` in v3.7.2)
- Slash commands: `/video audio narrate|music|mix|swap|pipeline`, `/video voice design|promote|list`
- Companion reference: `skills/video/references/video-audio.md` (VEO native audio)
- Findings: spike 3 + spike 4 results in `~/Desktop/spike3-elevenlabs-audio/` and `~/Desktop/spike4-lyria/`

**v3.7.2 update**: Google Lyria 2 is now the default music source after winning the 5-way bake-off in spike 4 (Lyria > ElevenLabs > MusicGen > MiniMax > Stable Audio per user listening verdict). ElevenLabs Music remains as the alternative via `--music-source elevenlabs`. Both are first-class providers.

---

## Why this exists

**The problem v3.7.1 solves:** when you stitch multiple separately-generated VEO clips into a longer sequence, each clip has its own emergent music intro/outro envelope. FFmpeg concatenation joins them losslessly but the *audio* still has audible seams every clip-duration — the music "restarts" at every cut. This is a structural artifact of independent generation, not a per-clip quality issue. **The fix is to replace the entire audio bed with a single continuous track**, eliminating clip boundaries from the audio dimension by construction.

**Empirical context:** spike 2 of the strategic reset session generated 4 VEO 3.1 Lite clips of the same autumn forest valley with identical voice descriptors and stitched them into a 32-second sequence. Voice character was perfectly consistent across all 4 clips (proving voice anchoring works), but the music bed had audible seams. Spike 3 then validated the audio-replacement architecture end-to-end with the v3.7.1 prototype, and the user confirmed the seams disappeared. **Spike 4 (v3.7.2) extended the music side with a 5-way bake-off across providers** to find the best music model — see "Music sources" below.

---

## Music sources (v3.7.2 multi-provider)

v3.7.2 supports two music providers, both first-class. Default is Lyria 2.

### Provider summary

| | **Lyria 2 (default)** | **ElevenLabs Music (alternative)** |
|---|---|---|
| **Provider** | Google Vertex AI | ElevenLabs |
| **Model** | `lyria-002` | `music_v1` |
| **API endpoint** | `POST {location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/lyria-002:predict` | `POST api.elevenlabs.io/v1/music` |
| **Auth** | Vertex API key (existing — same as VEO) | ElevenLabs API key (existing — same as TTS) |
| **Audio quality** | 48 kHz / 192 kbps stereo (highest of all 5 candidates tested) | 44.1 kHz / 128 kbps stereo |
| **Duration** | Fixed 32.768 seconds | 3,000–600,000 ms (configurable) |
| **Negative prompt** | ✅ Yes — actively excludes things | ❌ No |
| **Cost** | $0.06 per call (fixed) | Subscription quota (free on Creator+, ~$0.005/sec PAYG) |
| **Generation time** | ~26 seconds | ~22 seconds |
| **Output format** | base64-encoded WAV inline → transcoded to MP3 by the script | binary MP3 inline |

### When to use which

- **Use Lyria (default)** for:
  - Highest audio fidelity (the 48kHz advantage)
  - Predictable per-call cost — no quota anxiety
  - Prompts that benefit from explicit negative exclusions ("no vocals, no harsh percussion")
  - Cases where 32.768s clip duration is fine
  - Documentary, cinematic, score, ambient genres (the 5-way bake-off used a nature-doc prompt and Lyria won)
- **Use ElevenLabs** for:
  - Custom durations beyond 32.768s (Lyria has a hard cap)
  - High-volume usage on a Creator subscription (effectively free per call within quota)
  - Prompts that don't need negative exclusions (positive prompt is sufficient)
  - Cases where you've A/B tested both and prefer the ElevenLabs character for a specific genre

### Spike 4 5-way bake-off results (2026-04-14)

The strategic reset session tested 5 music providers with the **identical prompt** (`"Cinematic nature documentary background score, slow contemplative warm orchestral strings with soft piano, instrumental, around 70 BPM"`):

| Rank | Provider | Verdict |
|---|---|---|
| 🥇 1st | **Lyria 2** | "Definitely awesome", noticeable stereo on headphones, would ship |
| 🥈 2nd | **ElevenLabs Music** | Close second — quality very similar to Lyria |
| 🥉 3rd | Meta MusicGen (`stereo-large`) | Average, no vocal artifacts but volume fluctuations. Better than MiniMax despite being 2 years older — proves training data matters more than recency. |
| 4th | MiniMax Music 1.5 | Worse than MusicGen despite being newer — song-generation model fighting an instrumental prompt |
| 5th | Stable Audio 2.5 | Worst per the listening test, despite having the strongest spec sheet on paper |

**The most important finding** of the bake-off was the spec-vs-quality decoupling: Stable Audio had the fastest generation (4.6s vs Lyria's 26s), competitive sample rate (44.1 kHz), and a clean diffusion architecture, but the user heard it as the worst of the 5. **Audio gen model quality is uncorrelated with spec-sheet metrics at typical playback conditions** — see F13 in `references/video-audio.md`. Subjective listening is the only valid evaluation method.

### Lyria-specific prompt engineering

- **Positive prompts** work like ElevenLabs: genre, instrumentation, mood, tempo, style descriptors.
- **Negative prompts** are Lyria's unique advantage. Use them generously to actively exclude things you don't want: `"vocals, singing, dissonance, harsh percussion, electronic synths"` — Lyria honors negative prompts cleanly. ElevenLabs has no equivalent field.
- **Fixed 32.768 second duration** — there is no `duration_ms` parameter. If you need longer music for a long video, you must call Lyria multiple times and concatenate with FFmpeg (planned for v3.7.x as a `--length-ms` flag that auto-loops Lyria calls when source=lyria).
- **Same TOS guardrails as ElevenLabs Music**: avoid named copyrighted creators or brands in the prompt. Both APIs reject these (the rejection mechanism is different but the rule is the same — use generic descriptors).
- **`sample_count` parameter exists in the docs but appears non-functional** on the API-key auth path — spike 4 requested `sample_count=2` and got 1 prediction. Don't rely on batch generation; call Lyria once per output.

### Lyria dual output (v3.7.2): WAV master + MP3 preview

Lyria delivers a 6.29 MB base64-encoded **48 kHz / 16-bit stereo PCM WAV** in the API response. v3.7.2 preserves the lossless source by default and ALSO transcodes a 256 kbps MP3 alongside it:

```
~/Documents/nano-banana-audio/music_lyria_20260414_233623.wav   (6.0 MB — lossless 48kHz/16-bit/stereo PCM master)
~/Documents/nano-banana-audio/music_lyria_20260414_233623.mp3   (1.0 MB — 256 kbps preview/share/pipeline-mix)
```

**Why both?** The WAV is the canonical master for downstream editing (layering, EQ, mastering, additional FFmpeg processing). The MP3 is for preview, sharing, and the audio replacement pipeline's mix stage which runs at MP3-compatible quality. Storage cost is ~7 MB per Lyria call (vs ~1 MB MP3 alone) — cheap for what you gain in workflow flexibility, especially if you want to re-mix or master the music outside the plugin.

**MP3 quality default is 256 kbps** in v3.7.2 — psychoacoustically transparent for instrumental music. Most listeners cannot reliably distinguish 256 kbps MP3 from the source WAV in blind tests. v3.7.1 used 192 kbps for ElevenLabs music (which never has a lossless source available); v3.7.2 raised the Lyria default to 256 kbps because the lossless WAV is preserved as the master, so the MP3 is a *preview*, not a master, and benefits from higher quality.

**To opt out of WAV preservation** (e.g. tight disk budget, batch generation): pass `--no-wav` on the `music` subcommand. The MP3 will be created and the WAV bytes will be written through ffmpeg's stdin pipe rather than to disk.

**To override the MP3 bitrate**: pass `--mp3-bitrate 192k` (matches v3.7.1 ElevenLabs convention) or any other valid `libmp3lame` rate. Default is `256k`.

**ElevenLabs Music does NOT have a lossless source** — the API returns MP3 directly. There is no WAV to preserve. The dual-output behavior applies only to Lyria.

### Lyria auth caveat (important)

Lyria uses the **bound-to-service-account API key** path (the `AQ.*` format from Vertex Express Mode signup) — NOT OAuth or service account JSON. This is the **same auth pattern the plugin uses for VEO** and reuses the existing `vertex_api_key` + `vertex_project_id` + `vertex_location` fields in `~/.banana/config.json`. **No new credentials needed if you've already set up VEO.**

Google's official docs only document OAuth for Lyria, but spike 4 empirically verified that API-key auth works (similar to how VEO's docs only documented OAuth before our v3.6.0 backend work confirmed API-key auth was supported). This pattern of "API-key auth works on Vertex publisher models even when only OAuth is documented" is now load-bearing for the plugin's architecture and should be preserved when adding future Vertex models.

---

## Architecture

```
                     ┌───────────────────────────┐
                     │   VEO video (stitched,    │
                     │   audio will be replaced) │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
            ┌────────────────────────────────────────────────────┐
            │  Pipeline orchestrator (parallel calls, v3.7.2+)   │
            │                                                    │
            │   ┌──────────────┐    ┌────────────────────────┐  │
            │   │ ElevenLabs   │    │  Music (--music-source)│  │
            │   │ TTS          │    │  ┌──────────────────┐  │  │
            │   │ POST /v1/tts │    │  │ Lyria 2 (default)│  │  │
            │   │ eleven_v3    │    │  │ Vertex AI        │  │  │
            │   │ + audio tags │    │  │ POST .../predict │  │  │
            │   └──────┬───────┘    │  │ lyria-002        │  │  │
            │          │            │  └──────────────────┘  │  │
            │          │            │  ┌──────────────────┐  │  │
            │          │            │  │ ElevenLabs Music │  │  │
            │          │            │  │ POST /v1/music   │  │  │
            │          │            │  │ music_v1 (alt)   │  │  │
            │          │            │  └──────────────────┘  │  │
            │          │            └───────────┬────────────┘  │
            │          ▼                        ▼               │
            │     narration.mp3            music.mp3            │
            │     (continuous)             (continuous)         │
            └──────────────────┬─────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────┐
            │  FFmpeg sidechain compression    │
            │  apad narration → silence-pad    │
            │  to match music length           │
            │  threshold=0.04 ratio=10         │
            │  attack=15ms release=350ms       │
            │  weights=1.6:1.0 (voice louder)  │
            └──────────────┬───────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────┐
            │  FFmpeg audio-swap into video    │
            │  -map 0:v -map 1:a               │
            │  -c:v copy (lossless)            │
            │  -c:a aac -b:a 192k              │
            │  -shortest -movflags +faststart  │
            └──────────────┬───────────────────┘
                           │
                           ▼
                  Final MP4 (ship-ready)
```

The TTS call and the music call run in parallel via `concurrent.futures.ThreadPoolExecutor` because they're independent. This roughly halves the user-perceived latency from ~19s sequential to ~12s parallel.

---

## Quick start

### One-shot pipeline (the canonical command)

```bash
# v3.7.2: Lyria 2 is the default music source (no --music-source flag needed)
python3 skills/video/scripts/audio_pipeline.py pipeline \
  --video stitched-sequence.mp4 \
  --text "Each year... the seasons change across this valley, painting the forest in red and gold. [exhales] The river runs COLD here..." \
  --music-prompt "Cinematic nature documentary background score, slow and contemplative warm orchestral strings with soft piano, instrumental only, around 70 BPM" \
  --music-negative-prompt "vocals, dissonance, harsh percussion, electronic synths" \
  --voice narrator \
  --out final.mp4

# To use ElevenLabs Music instead (e.g. for custom durations >32.768s):
python3 skills/video/scripts/audio_pipeline.py pipeline \
  --music-source elevenlabs \
  --music-length-ms 60000 \
  --video v.mp4 --text "..." --music-prompt "..." --voice narrator --out final.mp4
```

This runs all four stages: parallel TTS + music, FFmpeg ducked mix, FFmpeg audio-swap into the source video. Output is a final MP4 with the new audio swapped in. **The `--music-negative-prompt` flag is Lyria-specific** — ElevenLabs ignores it. Use it generously to actively exclude things you don't want (vocals, percussion, etc.).

### Individual stages (for debugging or partial workflows)

```bash
# Just generate narration:
audio_pipeline.py narrate --text "..." --voice narrator --out narration.mp3

# Just generate music:
audio_pipeline.py music --prompt "..." --length-ms 32000 --out music.mp3

# Mix existing narration + music:
audio_pipeline.py mix --narration narration.mp3 --music music.mp3 --out mixed.mp3

# Audio-swap an arbitrary audio file into a video:
audio_pipeline.py swap --video v.mp4 --audio mixed.mp3 --out final.mp4
```

### Status check (do this first)

```bash
audio_pipeline.py status
```

Verifies your ElevenLabs API key, ffmpeg/ffprobe availability, and lists any custom voices saved in `~/.banana/config.json`.

---

## Voice management

### Designing a custom voice

ElevenLabs Voice Design generates a custom voice from a text description. Three previews per call (each ~20s of sample audio); pick one and promote it to a permanent saved voice.

```bash
# Step 1: design — generates 3 candidate previews
audio_pipeline.py voice-design \
  --description "A mature male documentary narrator with a warm baritone voice and slight British accent. Calm, measured, authoritative delivery, like a seasoned BBC wildlife narrator. Approximately 50-60 years old. Speaks with deliberate pacing, gentle gravitas, and quiet reverence." \
  --model eleven_ttv_v3 \
  --guidance-scale 5

# Output JSON includes paths to 3 preview MP3s. Listen to them, pick the best.
# Note the generated_voice_id of the chosen preview.

# Step 2: promote — saves the chosen preview as a permanent voice + stores in config
audio_pipeline.py voice-promote \
  --generated-id DGEKfN3sQ7BmtUUNKoyI \
  --name "Nano Banana Narrator" \
  --role narrator \
  --description "A mature male documentary narrator with..." \
  --notes "Designed for v3.7.1. Pacing ~159 wpm. Use ellipses and audio tags to slow."
```

### Listing saved voices

```bash
audio_pipeline.py voice-list
```

Returns the contents of `~/.banana/config.json` `custom_voices` section.

### Using a custom voice

Pass `--voice ROLE` to any subcommand that takes a voice. The pipeline will look up the role in `custom_voices` and use the saved `voice_id`. If no `--voice` is specified, the pipeline defaults to the `narrator` role.

```bash
audio_pipeline.py pipeline --voice narrator ...        # default
audio_pipeline.py pipeline --voice character_a ...    # different role
audio_pipeline.py pipeline --voice 21m00Tcm4TlvDq8ikWAM ...  # literal voice_id
```

### Custom voice schema (in `~/.banana/config.json`)

```json
{
  "custom_voices": {
    "narrator": {
      "voice_id": "DGEKfN3sQ7BmtUUNKoyI",
      "name": "Nano Banana Narrator",
      "description": "...",
      "source_type": "designed",
      "design_method": "text_to_voice",
      "model_id": "eleven_ttv_v3",
      "guidance_scale": 5,
      "should_enhance": false,
      "created_at": "2026-04-14",
      "provider": "elevenlabs",
      "notes": "..."
    }
  }
}
```

**`source_type`** is the discriminator that distinguishes voice creation paths:
- **`designed`**: created via `/v1/text-to-voice/design` from a text prompt (this is the path v3.7.1 ships)
- **`cloned`**: created via Instant Voice Cloning from an audio sample (planned future addition)
- **`library`**: a hand-picked voice from the ElevenLabs community library (always supported by passing the literal voice_id)

**`provider`** is currently always `"elevenlabs"` but enables future second-provider support without schema change.

---

## Prompt engineering — TTS narration

### Default model and settings

- **Model:** `eleven_v3` (most expressive, supports audio tags, ellipses, capitalization)
- **Stability:** 0.5 (Natural mode — honors audio tags but stays close to source text)
- **Similarity boost:** 0.75 (closer to reference voice character)
- **Style:** 0.0 (no extra stylistic exaggeration)
- **Speaker boost:** true

### Audio tags

Eleven v3 supports inline audio tags in the form `[tag-name]` placed immediately before the text they modify. The documented set is non-exhaustive — the model interprets unknown tags semantically via its training. Test with the tag flexibility experiment if you're unsure.

**Documented tags useful for narration:**
- `[exhales]`, `[sighs]`, `[exhales sharply]`, `[inhales deeply]` — natural breath pauses for emotional weight
- `[whispers]` — for hushed reverent moments
- `[thoughtful]` — closest documented register for contemplative narration
- `[short pause]`, `[long pause]` — explicit pause control

**Undocumented but empirically working tags for documentary register (verified spike 3):**
- `[contemplative]` — slight slowdown vs baseline
- `[reverent]` — produces ~20% slower delivery (largest measured effect of the undocumented set)
- `[wistful]` — similar to `[thoughtful]`

**Rule of thumb:** match the tag to the voice character. Daniel and Nano Banana Narrator both honor reverent/contemplative/wistful well because they're serious documentary voices. A bright energetic voice probably won't honor `[reverent]` strongly. Don't pile up tags — 1-2 per 30-second narration is plenty.

### Ellipses for pacing

Three dots (`...`) inside or between sentences create natural contemplative pauses. They're the lightest-weight pacing control — don't carry the same risk as audio tags but produce smaller effects. Use them generously for documentary narration.

```text
Each year... the seasons change across this valley, painting the forest in red and gold.
```

### Selective capitalization for emphasis

A single capitalized word in `eleven_v3` produces audible emphasis without affecting surrounding pacing. Use sparingly — 1-2 per sentence at most.

```text
The river runs COLD here, fed by mountain springs that have flowed for ten thousand years.
```

### Line length calibration

VEO 3.1 native narration has a "delivery mode drift" failure mode when narration is too short for the clip duration: the model non-deterministically sings the line to fill the time. **The fix is to write narration lines that fill the clip duration naturally** at the target voice's WPM:

```
target_word_count = duration_seconds × (voice_wpm / 60)
```

**Per-voice WPM reference (verified spike 3):**
- VEO native narrator: ~120 wpm → 16 words for 8s clip
- Daniel + eleven_v3: ~137 wpm → 18 words for 8s clip
- Nano Banana Narrator + eleven_v3: ~159 wpm → 21 words for 8s clip

Audio tags and ellipses slow delivery by ~5-10%; account for them when targeting precise durations.

### Banned content

ElevenLabs TTS does not have the same content restrictions as Eleven Music. You can use named creators, brands, locations, etc. in narration text without triggering guardrails. The restrictions only apply to the music generation API (see below).

---

## Prompt engineering — Music providers (Lyria + Eleven Music)

Both music providers respond to similar natural-language style prompts: genre, instrumentation, mood, tempo, and texture descriptors. The differences are in the available controls (Lyria has negative_prompt, ElevenLabs doesn't) and content restrictions (both block named creators/brands but with slightly different error patterns).

### Lyria-specific — leverage the negative prompt

Lyria's killer feature vs ElevenLabs is the `negative_prompt` field. Use it generously to actively exclude things you don't want, rather than relying on the positive prompt to imply absence:

```bash
# Positive prompt describes what you DO want
--music-prompt "Cinematic warm orchestral strings with soft piano, nature documentary, around 70 BPM"

# Negative prompt explicitly excludes what you DON'T want
--music-negative-prompt "vocals, singing, harsh percussion, electronic synths, dissonance"
```

Lyria honors both fields independently. The negative prompt is particularly valuable for instrumental work where vocals or percussion would break the use case — explicit exclusion is more reliable than hoping the positive prompt's "instrumental only" phrasing will be interpreted correctly.

### Both providers — TOS guardrails on named creators

## Prompt engineering — Eleven Music (alternative provider)

### Default model and settings

- **Model:** `music_v1`
- **Force instrumental:** `true` (always, for narration use cases — vocals would compete with the narrator)
- **Length:** 3,000ms minimum, 600,000ms (10 min) maximum

### Music prompt structure

Effective prompts include: genre/style, instrumentation, tempo (BPM), mood, and "instrumental only, no vocals" as an explicit constraint. Avoid named creators or brands — see banned content section below.

**Good example:**
```
Cinematic nature documentary background score. Slow and contemplative warm orchestral
strings with soft piano. Gentle and atmospheric, evoking autumn forests and quiet rivers.
Instrumental only, no vocals. Subtle textures, no heavy percussion. Around 70 BPM.
```

### ⚠️ Banned content (TOS guardrail)

The Eleven Music API **blocks prompts that name copyrighted creators or brands**. Empirically discovered in spike 3 v1: a prompt containing `"Annie Leibovitz / BBC Earth aesthetic"` returned HTTP 400 with code `bad_prompt` and a `prompt_suggestion` showing a sanitized version. The cleaned prompt (with the named-creator references removed) sailed through.

**This is music-API-specific.** Image generation prompts welcome creator names (`prompt-engineering.md` has many examples). Music prompts do not. Don't reuse image-gen prompt patterns for music.

**For v3.7.x prompt-construction logic:** strip named-creator references from music prompts before sending. Keep generic descriptors only (genre, mood, instrumentation, tempo).

### Audio bed continuity

ElevenLabs Music produces a single continuous track per call — there are no clip boundaries internal to the music. This is the entire reason v3.7.1 fixes the multi-clip seam problem: by replacing VEO's clip-locked audio with a single Eleven Music track, the seams literally cannot exist.

---

## FFmpeg pipeline details

### Stage 3: Sidechain compression (mix)

The mix stage uses FFmpeg's `sidechaincompress` filter with the narration as the side-chain trigger and the music as the audio being compressed. This produces "ducking" — the music drops in volume when the narrator is speaking and rises during gaps.

**Filter graph:**
```
[0:a]aformat=channel_layouts=stereo,apad=whole_dur=DURATION[narration_padded];
[1:a]volume=0.55[music_quiet];
[music_quiet][narration_padded]sidechaincompress=
    threshold=0.04:ratio=10:attack=15:release=350[ducked];
[narration_padded][ducked]amix=
    inputs=2:duration=longest:weights='1.6 1.0'[mixed]
```

**Key parameters:**
- **`apad whole_dur=DURATION`** — pads the narration with silence to match the music length. Critical: without this, the `sidechaincompress` filter inherits the narration's length and truncates the music tail.
- **`volume=0.55`** on the music — bring the music down before mixing so the narration sits above it cleanly.
- **`threshold=0.04`** — sensitivity of the side-chain trigger. Lower = more sensitive (ducks even on quiet narration parts).
- **`ratio=10`** — how much to compress the music when triggered. 10:1 is aggressive; 4:1 is gentle.
- **`attack=15ms`** — how fast the duck kicks in. Faster = more responsive, but very fast can sound pumpy.
- **`release=350ms`** — how fast the music returns to full volume after speech ends. 350ms is gentle and natural.
- **`amix weights='1.6 1.0'`** — narration is mixed 1.6× louder than the ducked music in the final output.

### Stage 4: Audio-swap (lossless video)

Replaces the audio track of an MP4 without re-encoding the video. The video is stream-copied (lossless, fast — ~65× realtime) and the new audio is re-encoded to AAC at 192 kbps for MP4 container compatibility.

```bash
ffmpeg -y \
  -i video_with_old_audio.mp4 \
  -i new_audio.mp3 \
  -map 0:v \
  -map 1:a \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  -movflags +faststart \
  output.mp4
```

**Key flags:**
- **`-map 0:v -map 1:a`** — explicitly map video from input 0 (the original video) and audio from input 1 (the new audio). Default mapping would pick whichever streams ffmpeg thinks are best; explicit mapping is unambiguous.
- **`-c:v copy`** — stream-copy the video. No re-encoding, no quality loss, blazing fast.
- **`-c:a aac -b:a 192k`** — re-encode the audio to AAC for MP4 compatibility (MP3 in MP4 works but AAC is more compatible across players). 192 kbps is broadcast-quality.
- **`-shortest`** — trim the output to the shorter of the two inputs. Handles minor video/audio duration mismatches (typically <100ms / 1 frame at 24fps).
- **`-movflags +faststart`** — moves the moov atom to the front of the file so social media uploaders can start processing the video as soon as the first byte arrives.

---

## Cost model

ElevenLabs is subscription-billed. For users on Creator tier or above, the per-call USD cost of a typical reel is effectively zero within the monthly quota.

**Approximate usage per 32-second reel:**
- TTS narration (~80 chars): negligible (~0.027% of monthly Creator quota)
- Eleven Music (32 seconds): negligible (under 1% of Creator quota for music ops)

**Creator tier quotas (April 2026):**
- 300,000 characters/month for TTS
- Additional credits for music and STS (separate from char quota)
- 100,000+ characters means ~3,750 30-second reels per month, all included in the subscription

`scripts/cost_tracker.py` includes nominal PAYG rates for ElevenLabs models so users can see the "credits-equivalent" cost of a generation, but these are not what's actually billed if the user is on a subscription tier.

---

## Empirical findings from spike 3 (carry-overs from `video-audio.md`)

These findings are documented in detail in `references/video-audio.md` "Discoveries from real production" section. Summary:

- **F2 (line-length):** narration must fill ~75-100% of clip duration to prevent VEO singing failure mode
- **F5 (tag flexibility):** v3 audio tags are open-ended, not whitelisted; undocumented tags work via semantic interpretation
- **F6 (music TOS):** Eleven Music blocks named creators/brands, image-gen does not
- **F7 (should_enhance):** Voice Design with `should_enhance=true` produces ~50% less variance and ~7% faster delivery
- **F8 (per-voice WPM):** voice character affects pacing independently of model and tags; calibrate line length per voice
- **F10 (`[exhales]`):** documented audio tag produces audible breath when placed before a sentence
- **F11 (capitalization):** single capitalized word produces emphasis without disturbing surrounding pacing
- **F12 (ellipses):** ellipses produce natural contemplative pauses, slowing delivery by ~5%

Each finding has a `<!-- verified: 2026-04-14 -->` marker in `video-audio.md` per the dated-verification principle from the strategic reset.

---

## Setup

1. **Get an ElevenLabs API key** at https://elevenlabs.io/app/settings/api-keys (Creator tier recommended for the music API)
2. **Add it to `~/.banana/config.json`:**
   ```bash
   python3 -c "import json,os; p=os.path.expanduser('~/.banana/config.json'); c=json.load(open(p)) if os.path.exists(p) else {}; c['elevenlabs_api_key']='YOUR_KEY_HERE'; json.dump(c, open(p,'w'), indent=2); os.chmod(p, 0o600)"
   ```
3. **Verify with status check:**
   ```bash
   python3 skills/video/scripts/audio_pipeline.py status
   ```
4. **Optionally design a custom narrator voice** (see Voice Management section above) or use any voice from your ElevenLabs library by passing the literal `voice_id`.

---

## Limitations and known issues

- **Stereo output collapses to mono in the mix stage.** The `amix` filter currently produces mono output despite the `aformat channel_layouts=stereo` directive on the narration branch. This is a polish issue — the audio is fully audible and high-quality — but the music's stereo image is lost in the mix. A future v3.7.x fix would route the narration through `pan=stereo|c0=c0|c1=c0` before mixing to force a stereo output.
- **Music TOS guardrails are runtime-discovered, not validated.** v3.7.1 does not pre-check music prompts for named creators before sending. If the API returns 400 with `bad_prompt`, the script surfaces the error message and the API's `prompt_suggestion`, but it doesn't auto-retry with a sanitized prompt. Users iterate manually.
- **Per-voice WPM is not auto-measured.** v3.7.1 uses a single default WPM constant for line-length math. A future v3.7.x fix would either probe each new custom voice with a calibration call or store an empirically-measured `wpm` field in the `custom_voices` schema.
- **Voice Design previews expire on ElevenLabs' side.** The `generated_voice_id` returned by `/v1/text-to-voice/design` is only valid for a limited time (exact TTL undocumented but appears to be hours, not days). Promote chosen previews promptly.
- **Voice cloning is not yet wired up.** The `source_type: cloned` schema field is reserved but no `voice-clone` subcommand exists in v3.7.1. Future addition.

---

## Related references

- `skills/video/references/video-audio.md` — VEO native audio capabilities (dialogue, ambient, SFX, narration before v3.7.1)
- `skills/video/references/veo-models.md` — VEO model specs and pricing
- `skills/video/references/video-prompt-engineering.md` — VEO prompt construction (different from ElevenLabs prompts)
- `skills/banana/references/post-processing.md` — FFmpeg patterns shared across image and video pipelines
- `skills/banana/scripts/cost_tracker.py` — pricing table including ElevenLabs entries
