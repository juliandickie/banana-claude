# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.7.2] - 2026-04-14

### Headline

**Lyria 2 added as the new default music source after a 5-way bake-off.** Spike 4 of the strategic reset session tested 5 music providers with the identical "cinematic nature documentary" prompt: Google Lyria 2, ElevenLabs Music, Meta MusicGen (`stereo-large`), MiniMax Music 1.5, and Stability AI Stable Audio 2.5. **Lyria won decisively** with ElevenLabs as a close second; MusicGen was middle-of-the-pack despite being 2 years old; MiniMax (a song-generation model) was rated worse than MusicGen because it fought instrumental prompts; Stable Audio was rated worst despite having the strongest spec sheet. v3.7.2 ships Lyria as the new default and retains ElevenLabs as the alternative; the other 3 are NOT integrated.

### The most important finding from spike 4

**F13 (audio gen quality is uncorrelated with spec-sheet metrics).** Stable Audio 2.5 had the fastest generation (4.6s vs Lyria's 26s), competitive sample rate (44.1 kHz), and the cleanest diffusion architecture, but the user heard it as the worst of the 5. Conversely, MusicGen (the 2-year-old open-source baseline) beat the much newer MiniMax 1.5 because MusicGen was trained on instrumental music while MiniMax was trained on songs with vocals. **Domain of training matters more than recency or spec sheets.** This belongs in `references/video-audio.md` as F13 with a `<!-- verified: 2026-04-14 -->` marker, and the generalizable principle is captured in CLAUDE.md key constraints: always evaluate new audio providers via subjective listening, never via benchmarks.

### Added

- **Google Lyria 2 (`lyria-002`) as the default music source** in `audio_pipeline.py`. Reuses the existing `vertex_api_key` + `vertex_project_id` + `vertex_location` from VEO setup — no new credentials needed. Outputs 32.768 second 48kHz/192kbps stereo MP3 (transcoded by the script from base64 WAV in the API response). Cost: $0.06 per call.
- **`generate_music_lyria()` function** in `audio_pipeline.py` with full Lyria 2 API support including the `negative_prompt` field that ElevenLabs Music doesn't have. Empirically validated by spike 4 + a follow-up smoke test through the new Python wrapper.
- **`generate_music()` dispatcher function** that routes to either Lyria or ElevenLabs based on a `source` parameter (default `"lyria"`). Both providers remain first-class.
- **`--music-source {lyria,elevenlabs}` CLI flag** on both the `pipeline` and `music` subcommands. Default is `lyria`.
- **`--music-negative-prompt` CLI flag** on the `pipeline` subcommand for Lyria's negative-exclusion feature. Lyria honors it cleanly; ElevenLabs ignores it.
- **`vertex/lyria-002` pricing row** in `cost_tracker.py` with the fixed $0.06/call rate and a comment explaining the per-clip vs per-second billing model and the spike 4 5-way bake-off context.
- **F13 finding** in `references/video-audio.md` documenting the spec-vs-quality decoupling discovered in spike 4. Each music model's empirical ranking is captured with the generalizable principles for future model evaluations.
- **"Music sources (v3.7.2 multi-provider)" section** in `references/audio-pipeline.md` with the full provider comparison table (Lyria vs ElevenLabs across audio quality, duration, negative prompt support, cost, generation time, etc.), the 5-way bake-off results table, the "when to use which" decision matrix, the Lyria-specific prompt engineering tips, and the API-key auth caveat (Lyria's docs only document OAuth but spike 4 confirmed API-key auth works — same pattern as VEO).
- **Updated architecture diagram** in `references/audio-pipeline.md` showing the new multi-provider music branch (Lyria default, ElevenLabs alternative).

### Changed

- **Renamed `skills/video/scripts/elevenlabs_audio.py` → `skills/video/scripts/audio_pipeline.py`** via `git mv` (preserves blame history). The file was named after a single provider (ElevenLabs) when it shipped in v3.7.1 yesterday, but now serves multiple music providers — the v3.7.1 name is misleading post-Lyria-integration. 12-hour-old script, no external consumers, clean rename with no migration cost.
- **Renamed `skills/video/references/elevenlabs-audio.md` → `skills/video/references/audio-pipeline.md`** for the same reason. All cross-references in `video-audio.md`, SKILL.md, CLAUDE.md, and PROGRESS.md updated.
- **Default music source for the audio pipeline is now Lyria 2** (was ElevenLabs Music in v3.7.1). The `pipeline` subcommand uses Lyria by default. Users who want ElevenLabs explicitly pass `--music-source elevenlabs`.
- **`pipeline()` Python function signature** gained `music_source` and `music_negative_prompt` parameters with sensible defaults. Backward compat: existing v3.7.1 usage via the renamed script still works because the new parameters have defaults.
- **`status` subcommand now reports both music providers** — Lyria/Vertex credentials check + ElevenLabs key check + ffmpeg/ffprobe + custom voice library. Previously only checked ElevenLabs.
- **`mix_narration_with_music` is now called with the actual probed music duration** rather than the requested `music_length_ms`. This was a latent bug in v3.7.1: if ElevenLabs returned a slightly off-target duration, the apad would be wrong. With Lyria's fixed 32.768s clip ignoring `music_length_ms` entirely, the bug would have surfaced as a 768ms music-tail truncation. Now fixed.
- **`audio-pipeline.md` "Prompt engineering" section restructured** to cover both providers together, with a Lyria-specific subsection on negative prompts (the killer feature vs ElevenLabs) and a shared subsection on the named-creator TOS rule that applies to both providers.

### Spike 4 five-way bake-off results (full table)

| Rank | Provider | Listening verdict | Tech specs |
|---|---|---|---|
| 🥇 1st | **Lyria 2** | "Definitely awesome", noticeable stereo on headphones, ship-ready | 48kHz / 192kbps stereo, 32.768s, $0.06/call |
| 🥈 2nd | **ElevenLabs Music** | Close second, very similar quality to Lyria | 44.1kHz / 128kbps stereo, configurable, subscription |
| 🥉 3rd | Meta MusicGen `stereo-large` | Average, no vocal artifacts, slight volume fluctuations | 32kHz / 96kbps stereo, March 2024 model |
| 4th | MiniMax Music 1.5 | Worse than MusicGen despite being newer (Nov 2025) | 44.1kHz / 256kbps stereo, song model fighting instrumental prompts |
| 5th | Stability AI Stable Audio 2.5 | Worst per listening test, despite strongest spec sheet | 44.1kHz / 128kbps stereo, fastest generation (4.6s vs Lyria's 26s), Nov 2025 |

Total spike 4 cost: ~$0.30 (Lyria $0.06 × 2 spike calls + Eleven $0 subscription + MusicGen ~$0.12 + MiniMax ~$0.20 + Stable Audio ~$0.05). Cumulative session spend across all spikes (1+2+3+4): ~$4.83. Approved budget remaining: ~$15-20 for spike 6 (banned-keywords re-validation, deferred to v3.7.3).

### Deferred to v3.7.3+

- **Spike 6 — banned-keywords re-validation** ($1.50). Originally part of the v3.7.2 plan but deferred to keep this release focused on Lyria. Targets v3.7.3.
- **Multi-call Lyria for longer music** (auto-loop calls when `--music-length-ms > 32768`). Currently Lyria has a hard 32.768s cap; users needing longer music must use `--music-source elevenlabs`.
- **Lyria-vs-ElevenLabs genre bake-off** (user request from v3.7.2 listening session). Test both providers across electronic, classical, folk, ambient, jazz, and hip-hop genres to surface model-strength differences beyond the cinematic-orchestral case validated in spike 4. Targets a v3.7.x research release.
- **Stereo output in FFmpeg mix** (still mono — known v3.7.1 polish issue).
- **Auto-measured per-voice WPM** (still hardcoded — known v3.7.1 polish issue).
- **Voice cloning** (Instant Voice Clone, Professional Voice Clone — schema field reserved).

### Verification

- **Smoke-tested the new `audio_pipeline.py music --source lyria` command** end-to-end. Returned structured JSON with `source: "lyria"`, `model_id: "lyria-002"`, `duration_seconds: 32.768`, `elapsed_seconds: 25.13`, and a 788KB MP3 (transcoded from 6.29MB WAV). Identical output characteristics to the spike 4 raw API call — the new Python wrapper produces no regression vs the spike script.
- **Lyria authentication via Vertex API key confirmed working** through the `audio_pipeline.py` code path. Same `vertex_api_key` from `~/.banana/config.json` that the existing VEO calls use. No new credentials needed.
- **`audio_pipeline.py --help` and all subcommand `--help` outputs verified** — `music` subcommand correctly shows `--source {lyria,elevenlabs}`, `pipeline` subcommand correctly shows `--music-source {lyria,elevenlabs}` and `--music-negative-prompt`.
- **`git mv` preserved file history** for both renamed files — `git status --short` shows them as `R` (renamed), not `D` (deleted) + `??` (added).
- **Version consistency verified**: `3.7.2` appears in `plugin.json`, `README.md` badge, and `CITATION.cff` (date `2026-04-14`).
- **No new pip dependencies.** Lyria integration uses stdlib `urllib.request` + `base64` + `subprocess` for ffmpeg transcoding. Matches the plugin's existing fallback-script pattern.

## [3.7.1] - 2026-04-14

### Headline

**ElevenLabs audio replacement pipeline + custom voice design + strategic reset.** v3.7.1 ships the first non-VEO audio capability after a deep strategic reset session that questioned the entire v3.7.0 plan. Three empirical spike rounds invalidated the original "voice-changer post-pass" assumption, surfaced the real multi-clip music-bed seam problem, and validated a structural audio replacement architecture (continuous TTS + Eleven Music + FFmpeg ducked mix + lossless audio swap) end-to-end. The new `elevenlabs_audio.py` script + `references/elevenlabs-audio.md` ship as the canonical solution. Custom voice design via ElevenLabs Voice Design API is also wired in, with a nested `custom_voices.{role}` config schema designed for the multi-voice future already on the roadmap.

### Strategic reset session — what changed

The session was a deliberate "stop building, look up" checkpoint after 5 releases shipped in 48 hours. Three findings reshaped v3.7.0/v3.7.1:

1. **VEO 3.1 generates voiceover narration natively** via `"A narrator says, '...'"` — confirmed by Google's own Vertex AI prompt guide and verified empirically. The original v3.7.0 ROADMAP claim that VEO "doesn't generate voiceover; it's added in post" was wrong. The TTS subcommand originally scoped for v3.7.0 was solving a non-problem.
2. **VEO does NOT have voice character drift across separately-generated clips** when descriptors are locked. Spike 2 generated 4 clips of the same scene with the same voice descriptor and the user verified perfect voice consistency. The original v3.7.1 voice-changer scope was based on a false assumption.
3. **The real "multi-clip drift" problem is musical, not vocal**: each VEO clip generates its own emergent music intro/outro envelope independently, so stitched sequences have audible music seams every clip-duration. Spike 3 confirmed the fix is structural audio replacement, not voice changing.

The session also discovered Replicate's official MCP server (npm `replicate-mcp`), Vertex AI Model Garden's 200+ models including Lyria for music generation, and that Google ADK is architecturally incompatible with Claude Code's skill runtime (don't adopt). All of these are documented in the strategic reset plan and inform v3.7.2+ scope.

### Added

- **`skills/video/scripts/elevenlabs_audio.py`** — new ~720 line stdlib-only Python script implementing the v3.7.1 audio replacement pipeline. Subcommands:
  - `pipeline` — canonical end-to-end command. Parallel TTS + Eleven Music API calls, FFmpeg sidechain mix, lossless audio swap into video. Halves user-perceived latency by parallelizing the two API calls.
  - `narrate`, `music`, `mix`, `swap` — individual stage commands for debugging or partial workflows
  - `voice-design` — POST `/v1/text-to-voice/design` to generate 3 candidate voice previews from a text description (eleven_ttv_v3 model)
  - `voice-promote` — POST `/v1/text-to-voice` to save a chosen preview as a permanent custom voice, atomically write to `~/.banana/config.json` under the new `custom_voices.{role}` schema
  - `voice-list` — list custom voices from config
  - `status` — verify ElevenLabs API key + ffmpeg + custom voices
- **`skills/video/references/elevenlabs-audio.md`** — comprehensive new reference doc covering the v3.7.1 architecture (TTS + music + ducked mix + audio swap), voice management (design → promote → use), prompt engineering for both TTS narration and Eleven Music, FFmpeg parameter rationale, the per-voice WPM calibration model, and the cost model.
- **`custom_voices.{role}` config schema** in `~/.banana/config.json` — nested structure designed to support multiple semantic roles (narrator, character_a, brand_voice, etc.), three creation paths (designed, cloned, library), and per-voice metadata (model_id, source_type, design_method, guidance_scale, created_at, provider, notes). Forward-compatible for multi-provider future. Replaces the flat `custom_narrator_voice_id` field that briefly existed during the spike. **Lesson learned**: the flat field was a YAGNI miscall — when the user has *committed* future needs (multiple voices and clones), nested-now is correct.
- **`elevenlabs_api_key` field in `~/.banana/config.json`** alongside the existing Google AI / Replicate / Vertex keys. Resolved with the same precedence pattern: CLI flag → env var → config file.
- **12 empirical findings** in `references/video-audio.md` "Discoveries from real production" section, each with a `<!-- verified: 2026-04-14 -->` marker per the dated-verification principle. Findings cover: voice character anchoring (F1), delivery-mode drift / line-length calibration (F2), music seam problem (F3), VEO automatic ducking (F4), v3 audio tag flexibility / open-ended whitelist (F5), Eleven Music TOS guardrail on named creators (F6), Voice Design `should_enhance` behavior (F7), per-voice WPM differences (F8), Lite tier broadcast quality (F9), `[exhales]` audio tag (F10), capitalization emphasis (F11), ellipses pacing (F12).
- **New `/video audio ...` and `/video voice ...` slash command surface** documented in `skills/video/SKILL.md` Quick Reference table. Includes routing rules ("when to use VEO native narration vs the v3.7.1 pipeline") and prompt engineering guidance for the new audio pipeline.
- **ElevenLabs pricing rows in `cost_tracker.py`** for `eleven_v3`, `eleven_multilingual_v2`, `eleven_flash_v2_5`, `music_v1`, and `eleven_multilingual_sts_v2`. Subscription-billed users see negligible per-call cost; the entries support PAYG-equivalent estimates for users not on Creator tier.
- **`validate_setup.py` informational check for ElevenLabs config** (non-blocking — v3.7.1 is opt-in). Surfaces "ElevenLabs API key configured" + custom voice list when present.

### Changed

- **The v3.7.0 audio strategy split scope is fundamentally redefined.** The original plan was "split per-shot `audio` field into ambient/sfx/dialogue/narration + build a `/video sequence narration` TTS subcommand for multi-clip drift." After the strategic reset, the architecture is "use the v3.7.1 ElevenLabs replacement pipeline for sequences that need narration, custom voices, or seam-free music." The schema split work is deferred to v3.7.x as a refinement, not a v3.7.0 blocker.
- **`references/video-audio.md`** updated with the 12 empirical findings, the v3.7.1 audio replacement pipeline cross-reference, and a corrected "Limitations" section that points users to the audio swap workflow when audio quality is critical.
- **VEO Lite tier framing in `references/veo-models.md`** is informally re-evaluated based on F9: Lite is broadcast-quality for narrated documentary footage. The "draft only" framing is being relaxed in v3.7.1+ — Standard is reserved for shots with extreme detail (extras, complex character interactions, hero product shots), not the default for hero work.
- **`skills/video/SKILL.md`** Quick Reference table grew from 11 to 19 commands (new `/video audio ...` and `/video voice ...` subcommand groups). New "v3.7.1 Audio Replacement Pipeline" section in the body with routing rules, voice selection guidance, music TOS warning, and prompt engineering pointers for both TTS and music.

### Deferred to v3.7.2+

The strategic reset plan included three more spikes that were deferred when the user pivoted to shipping v3.7.1:

- **Spike 4 — Lyria 2 music smoke test** (~$0.50). Validates that Vertex AI Lyria 2/3 is callable through our existing Vertex API-key auth path. Lyria is Google's native music generation model and would be a complementary alternative to Eleven Music. Targets v3.7.2.
- **Spike 5 — Character consistency bake-off** (~$15-20). Generates 4-shot character sequences on VEO 3.1 Lite, Kling 2.6 (Replicate), and Runway Gen-4 (Replicate) for direct comparison. Informs whether v3.8.0 multi-provider abstraction is urgent or deferred. Targets v3.8.0.
- **Spike 6 — Banned-keywords re-validation** (~$1.50). Tests whether the 2025-era banned-keywords list (`"8K"`, `"masterpiece"`, `"ultra-realistic"`) still applies to Gemini 3.1 image generation. Quick, cheap, isolated. Targets v3.7.2 or v3.8.1.

### Verification

- **End-to-end empirical validation in spike 3 final prototype** at `~/Desktop/spike3-elevenlabs-audio/v3.7.1-final-prototype-veo-video-with-custom-voice.mp4`. The user verified the architecture produces ship-ready output: continuous narration, no music seams, natural ducking, custom-designed British baritone narrator voice. Quote: *"ok to proceed as is."*
- **Voice Design end-to-end flow** verified by promoting preview 3 (`DGEKfN3sQ7BmtUUNKoyI`) to the permanent voice "Nano Banana Narrator" and successfully calling TTS with the new voice.
- **Config schema migration** from flat `custom_narrator_voice_id` to nested `custom_voices.{role}` validated by atomic write + readback comparison.
- **No new Python pip dependencies.** `elevenlabs_audio.py` uses stdlib only (urllib.request, concurrent.futures, subprocess for FFmpeg). Matches the plugin's existing fallback-script pattern.
- **Total spike spend during the strategic reset session: $4.40 of VEO Lite generation** + ~0 ElevenLabs cost (subscription-billed within Creator tier quota).

### Known limitations (documented in `references/elevenlabs-audio.md`)

- Stereo output collapses to mono in the current FFmpeg mix graph (workaround possible in a v3.7.x patch — route narration through `pan=stereo|c0=c0|c1=c0`)
- Per-voice WPM is hardcoded rather than auto-measured on first use of a new voice
- Voice cloning (Instant Voice Clone, Professional Voice Clone) is not yet wired up — the `source_type: "cloned"` schema field is reserved for a future v3.7.x addition
- Music TOS guardrail is runtime-discovered, not validated pre-flight

## [3.6.3] - 2026-04-11

### Headline

**Review gate enforcement + smarter plans.** Five more items from the deferred-bucket, all thematically coupled: make the review gate that v3.6.2 shipped actually useful, detect frame drift between review and generate, pre-fill shots with cinematography defaults so Claude has less to remember, and pay off the 1080p Lite pricing TODO from the v3.5.0 research.

### Added

- **`video_sequence.py generate` mandatory review gate.** `cmd_generate` now checks for `REVIEW-SHEET.md` in the storyboard directory and validates its embedded frame hashes against current disk state before doing any work. Missing, unparseable, or stale reviews abort with a clear error listing the exact fix command (either "run `review`" or "run `review` again because shot N's frame changed"). Pass `--skip-review` to bypass for CI/automation — intentionally disables the safety net.
- **Plan hash tracking via embedded manifest block.** `_build_review_sheet` now appends a machine-readable manifest wrapped in HTML comments (`<!-- BEGIN REVIEW MANIFEST v1 --> ... <!-- END ... -->`) containing the plan path, storyboard dir, and per-shot frame SHA-256 hashes. The block is inside a ````json` fenced code block so it doesn't render in markdown previews. `_check_review_freshness` parses the manifest on every `generate` run and compares against current hashes; any drift returns `{"status": "stale", "drifted_shots": [N, ...]}` and the gate aborts.
- **New helpers in `video_sequence.py`:** `_sha256_file`, `_build_review_manifest`, `_parse_review_manifest`, `_load_review_manifest`, `_check_review_freshness`. All stdlib-only, all unit-tested.
- **Shot-type semantic defaults** — new `SHOT_TYPE_DEFAULTS` table with 8 types (`establishing`, `content`, `medium`, `closeup`, `product`, `transition`, `cutaway`, `broll`) each mapping to default duration, camera hint, and `use_veo_interpolation` flag. `cmd_plan` accepts `--shot-types establishing,medium,closeup,product` and pre-fills shots with sensible defaults; shot count is determined by the list length and durations rescale to hit `--target`. Establishing/transition/cutaway/broll default to first-frame-only (they cut to unrelated material); content/medium/closeup/product default to first+last frame interpolation.
- **`--reference-image` flag on banana `generate.py`** — up to 3 reference images passed as `inlineData` parts alongside the text prompt. Primary use case: cross-shot character/product continuity in video sequences. Different from `edit.py` — reference-guided generation is "generate a new image informed by these anchors" vs edit's "modify this existing image." New helper `_read_reference_image` with PNG/JPEG/WebP/GIF support and validation. Output JSON includes a note that reference-guided output is ~1K-ish regardless of `--resolution` request (known Gemini behavior).

### Changed

- **`cost_tracker.py` VEO 3.1 Lite comment** — the v3.5.0 TODO "verify 1080p Lite pricing" has been exercised empirically. 1080p Lite is callable via the Vertex AI backend with ~73 s generation time vs ~38 s for 720p. The rate is unchanged ($0.05/sec) pending a full billing cycle — flag in the comment that 1080p billing may differ and users should check their GCP console.
- **`cmd_plan` no longer hardcodes `type: "content"` for every shot.** When `--shot-types` is set, each shot's `type` field reflects the user's intent and the `camera`, `duration`, and `use_veo_interpolation` fields are pre-filled from `SHOT_TYPE_DEFAULTS`.
- **`cmd_plan` storyboard cost estimate** now accounts for `use_veo_interpolation` shots that skip the end frame (saves $0.08/frame). Previously the estimate assumed 2 frames per shot regardless.

### Docs

- **`video-sequences.md` Stage 3 (Review)** rewritten to describe the mandatory gate with frame hash tracking, the `--skip-review` bypass, and the design rationale (catching the most expensive category of mistake).
- **`video-sequences.md` Stage 1 (Shot List)** gets a new "Shot-type semantic defaults" subsection with the full 8-type table.
- **SKILL.md** Commands table and narrative section updated.
- **README.md** Commands table, What's New section, version badge.

### Verification

- All 6 scripts (`video_sequence.py`, `_vertex_backend.py`, `video_generate.py`, `video_extend.py`, banana `generate.py`, `cost_tracker.py`) compile clean.
- **8 new unit tests** via `python3 -c` import: `_shot_defaults` for all 8 types plus the unknown-type fallback; `_sha256_file` round-trip plus missing-file None; `_build_review_manifest` on a synthetic plan with interpolation and non-interpolation shots; review-sheet round-trip through `_load_review_manifest`; `_check_review_freshness` returns `ok` → `stale` (with correct `drifted_shots`) → `missing` as frames mutate; manifest parser handles raw JSON, `\`\`\`json` fenced, and bad/missing block cases.
- **Functional test of the gate** — ran `cmd_generate` against the coffee shop storyboard dir with REVIEW-SHEET.md deleted; pipeline correctly aborted with the "No REVIEW-SHEET.md found" error. Then ran with `--skip-review` to prove the bypass path works.
- **1080p Lite probe** ($0.40) — real 4-second clip generated via the Vertex AI backend at 1080p Lite, 73 seconds wall clock, 2.3 MB output at `/tmp/v363-pricing-probe/`. Confirms 1080p Lite is callable.

### Release-process honesty

**Unintended $0.40 spend during v3.6.3 verification.** When functionally testing the review gate's `--skip-review` path, I set `GOOGLE_AI_API_KEY=FAKE` expecting it to block any real API call. It didn't — the child `video_generate.py` process auto-routed Lite requests to the Vertex AI backend, which read real credentials from `~/.banana/config.json`, and generated one Shot 2 clip before I killed the pipeline. Total unintended spend: $0.40 (one 8-second Lite 1080p clip at `~/Documents/nano-banana-sequences/sequence_clips_20260411_223403/clip-02.mp4`). Root cause: non-hermetic test harness. Going forward, any functional test of `cmd_generate` must use a fixture storyboard directory where the child process cannot successfully hit a real API, not just an env-var block on one of two possible auth paths.

### Not in scope (still deferred)

Everything else from the v3.6.1/v3.6.2 deferred buckets: the `update-prompts` Gemini-vision subcommand (v3.6.4), the audio strategy split (narration/dialogue/ambient/sfx fields, v3.7.0), the `/video sequence narration` TTS subcommand (v3.7.0 paired with audio split), `output_gcs_uri` support, `--num-videos` batching, parallel batch execution in `video_sequence.py`, object insertion support, and regional restrictions awareness. Each still needs its own dedicated release.

## [3.6.2] - 2026-04-11

### Headline

**Sequence production polish.** Five small-but-high-value improvements surfaced by the coffee shop demo that shipped earlier today — the ones you notice the moment you run a real 4-shot sequence end-to-end. Zero new VEO API calls to verify; everything tested against fixture plans.

### Added

- **`video_sequence.py review` subcommand** — generates `REVIEW-SHEET.md` from a plan + storyboard directory. Each shot block shows frames inline, the full VEO prompt, resolved model + cost for the selected `--quality-tier`, and a ✅/⚠️ status badge. Sequence totals and any gaps blocking `generate` appear in the footer. Pure markdown, regenerated on demand, opens in Quick Look. This is the human approval gate between `storyboard` and `generate` that was previously an undocumented hand-written step. v3.6.2 ships it as a standalone subcommand; a `--skip-review` mandatory-gate integration is v3.6.3 scope.
- **5-stage pipeline**: `plan → storyboard → **review** → generate → stitch`. The review stage is now first-class in the docs, the SKILL.md routing table, the README Commands table, and the Quick Start example.
- **`use_veo_interpolation: true` per-shot flag in plan.json** — shots that should let VEO pick their own ending (establishing shots cutting away to unrelated material, transitions, etc.) can set this. The storyboard stage skips the end frame for those shots (saves $0.08/frame) and the generate stage drops `--last-frame` from the VEO call. Empirically validated by the coffee shop demo's Shot 1 where we used first-frame-only to let VEO execute a dramatic push-in. The field defaults to False so existing plans keep the strict first+last frame behavior.
- **`video_sequence.py storyboard --shots 1,3-5` partial regeneration** — new `--shots` flag accepts a comma-separated list of shot numbers and/or hyphen ranges. When set, the storyboard stage only regenerates the selected shots instead of rebuilding the whole storyboard. Critical for iteration when one frame has a bug but others are approved.
- **`_parse_shots_filter()` helper** in `video_sequence.py` — accepts `"1,3,5"`, `"2-4"`, `"1,3-5,7"`, or any mix. Validates and fails fast with a clear error on garbled input.
- **`_sanitize_project_name()` helper** — builds filesystem-safe slugs for per-project output subdirs. `"Golden Bean Cafe — 30s"` becomes `"golden-bean-cafe-30s"`.

### Changed

- **Default output location** is now `~/Documents/nano-banana-sequences/` (was `~/Documents/nanobanana_generated/`). Visible from Finder, works with Quick Look (Space key), per-project subdirs when a project name is provided. `LEGACY_OUTPUT_BASE` still points at the old path for documentation continuity.
- **`_default_output(suffix, project_name=None)`** now accepts an optional `project_name` argument. With a project name, the layout becomes `~/Documents/nano-banana-sequences/<project-slug>/<suffix>/` so all stages of one project cluster together.
- **Storyboard stage cost accounting** — shots with `use_veo_interpolation=true` only charge for one frame ($0.08) instead of two ($0.16). The estimate subcommand and the review sheet both reflect this.
- **`cmd_storyboard()` missing-frame error messages** now distinguish "missing start frame" (always fatal) from "missing end frame" (fatal only when `use_veo_interpolation=false`). The error text also points users at the flag they can set to unblock themselves.

### Docs

- **`video-sequences.md`** section "The 4-Stage Pipeline" renamed to "The 5-Stage Pipeline" with a new Stage 3 (Review) block describing the review subcommand, its cost-free nature, and the decision not to hard-enforce the gate in v3.6.2.
- **`SKILL.md`** Commands table and narrative section updated with the review subcommand, partial regeneration flag, and `use_veo_interpolation` option.
- **`README.md`** Commands table, Quick Start example, and What's New section all updated.

### Verification

- All 4 video scripts still compile clean.
- `_parse_shots_filter` unit test covers the four supported syntaxes (None, `"1,3,5"`, `"2-4"`, `"1,3-5,7"`).
- Real-data test: ran `video_sequence.py review --plan /tmp/coffee-shop-demo/plan.json --storyboard /tmp/coffee-shop-demo/storyboard --quality-tier draft` against the coffee shop demo fixture from earlier today. With Shot 1 marked `use_veo_interpolation=true` and filename symlinks in place, the review sheet reports 4/4 ready, $0.55 storyboard cost, $1.50 video cost (Lite draft), $2.05 total, and the Shot 1 block correctly shows "first-frame-only (VEO interpolates ending)" with no end-frame slot.
- **Zero new VEO spend this release** — all testing used fixtures from earlier v3.6.1 work.

### Not in scope for v3.6.2 (deferred to v3.6.3+)

Everything else in the original v3.6.1 deferred bucket: plan hash tracking with SHA-256, the `update-prompts` Gemini-vision subcommand, the review-as-mandatory-gate enforcement with `--skip-review`, the audio strategy split (narration/dialogue/ambient/sfx fields), the `/video sequence narration` TTS subcommand, shot-type semantic effects, `/banana` skill improvements (`--reference-image` flag on `generate.py`, conservatism bias docs), and the v3.6.0-research batch (`--num-videos`, object insertion, parallel execution, `output_gcs_uri`, regional detection, 1080p Lite pricing verification). These items need their own dedicated releases with proper plans — especially the audio strategy split which is a real product decision, not a code change.

## [3.6.1] - 2026-04-11

### Headline

**First+last frame interpolation and reference images now work on the Vertex AI backend.** v3.6.0 shipped the Vertex backend with `--first-frame` support but deferred `--last-frame` and `--reference-image` to v3.6.1 because the field names weren't empirically verified. Two authoritative Google doc pages published in the [Vertex first/last frame reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames) and the [Gemini API video guide](https://ai.google.dev/gemini-api/docs/video) confirmed the field names as `lastFrame` (camelCase, nested at the instance level alongside `image`) and `referenceImages` (an array of `{image, referenceType: "asset"}` entries). Wiring them in took ~40 lines in `_vertex_backend.build_vertex_request_body` plus removing the `_error_exit` stubs in `_submit_vertex_ai`. Verified end-to-end with a Lite first+last frame smoke test ($0.20) using coffee shop Shot 2's storyboard frames — real 2.27 MB MP4 produced in 42 seconds.

### Added
- **`last_frame_path` parameter** on `_vertex_backend.build_vertex_request_body`. Builds the `lastFrame` field as a sibling of `image` at the instance level with `bytesBase64Encoded` + `mimeType`. Same camelCase field name used by both the Vertex AI REST reference and the Gemini API docs.
- **`reference_image_paths` parameter** on `_vertex_backend.build_vertex_request_body`. Builds the `referenceImages` array (up to 3 entries) with each entry as `{image: {bytesBase64Encoded, mimeType}, referenceType: "asset"}`. Matches the structure shown in the official Google Veo 3 notebook and the Gemini API bash curl example.
- **Four new mutual-exclusion checks** in `build_vertex_request_body`: (1) `video_input` cannot combine with any image inputs, (2) `last_frame` requires `image` (since `lastFrame` is always paired), (3) `reference_images` cannot combine with `image` or `last_frame` (separate Vertex code paths), (4) `reference_images` capped at 3 entries.

### Fixed
- **`--last-frame` on the Vertex AI backend** — v3.6.0 raised `_error_exit("--last-frame is not yet supported on the Vertex AI backend")`. v3.6.1 lets it through to the wire. Works for all five VEO 3.1 model IDs (Standard/Fast/Lite, both preview and GA `-001`). VEO 3.0 does not support first+last frame per Vertex docs; the API will reject it with a clear error if a user tries.
- **`--reference-image` on the Vertex AI backend** — same deferred-error was removed. Vertex supports reference images for all VEO 3.1 tiers except Lite per Google's parameter table; Lite requests with reference images will be rejected by the API.

### Docs
- **`_vertex_backend.py` docstring** on `build_vertex_request_body` rewritten with the full list of input modes (text-to-video, image-to-video, first+last interpolation, reference-guided, Scene Extension v2) and their mutual exclusions.
- **`_submit_vertex_ai` docstring** updated to note the v3.6.1 additions and link to the source docs.

### Verification
- 8 new unit checks on `build_vertex_request_body` covering last_frame, reference_images, and all 4 new mutual-exclusion rules. The original 18 commit-1 checks still pass.
- Real API ($0.20): Lite first+last frame on coffee shop Shot 2 storyboard frames, 42s wall clock, 2.27 MB MP4 saved to `/tmp/v361-smoke/`.

## [3.6.0] - 2026-04-11

### Headline

**Vertex AI backend with API-key auth — unblocks the full VEO 3.1 capability surface.** The Gemini API surface (`generativelanguage.googleapis.com`) the plugin had been using only serves text-to-video on two preview model IDs. v3.5.0 documented every other VEO feature as "Vertex AI only — gated until v3.6.0" — image-to-video, Lite, Legacy 3.0, GA `-001` IDs, and Scene Extension v2 all returned clear errors instead of silent HTTP 404s. v3.6.0 wires up the Vertex AI backend with a stdlib-only request translator using bound-to-service-account API key auth (no OAuth, no service account JSON, no `gcloud` install required), un-gates everything, and re-points `--quality-tier draft` from the v3.5.0 Fast stopgap back to Lite for the full **8× cost reduction**.

### Fixed
- **Image-to-video / `--first-frame` / `--last-frame` / `--reference-image`** — the Gemini API surface stopped serving image-to-video for VEO when the GA `-001` IDs shipped on Vertex AI in March 2026. v3.6.0's Vertex backend handles all of these. `video_generate.py --first-frame` works again.
- **`video_extend.py --method video` (Scene Extension v2)** — re-enabled as the default. The Vertex API accepts inline base64 video input via `instances[0].video.bytesBase64Encoded` (despite Google's docs only showing the `gcsUri` path). Verified end-to-end with a 1.69 MB → 4.5 MB MP4 generation.
- **Lite duration constraint** — v3.5.0 documented Lite as supporting 5–60 second durations based on unverified docs. Real-API testing during v3.6.0 showed the API explicitly rejects 5-second Lite requests with `"supported durations are [8,4,6] for feature text_to_video"`. Lite is `{4, 6, 8}` like every other tier. The error message and argparse help text are corrected.
- **1:1 aspect ratio claim for Lite** — v3.5.0 documented `1:1` as a Lite-only special-case based on unverified docs. The Vertex docs and the official Google Veo 3 notebook both list only `16:9` and `9:16`. v3.6.0 removes the special-case from `_valid_ratios()` and `video_generate.py`, and adds defense-in-depth validation in the Vertex request body builder.
- **`video_extend.py GENERATE_DURATION` for Scene Extension v2** — was hardcoded to `8` (correct for the keyframe path) but Vertex's `feature=video_extension` accepts only `durationSeconds=7`. Replaced with two named constants `GENERATE_DURATION_KEYFRAME=8` and `GENERATE_DURATION_VIDEO=7`, dispatched via `_hop_duration_for_method()`.

### Added
- **`skills/video/scripts/_vertex_backend.py`** (NEW, ~650 lines) — pure data translation helper module for the Vertex AI VEO surface. Handles URL composition (regional + global endpoints, hard-coded `/v1/` to avoid SDK [issue #2079](https://github.com/googleapis/python-genai/issues/2079) routing bug), request body construction (`instances`/`parameters` wrapper with `bytesBase64Encoded` image/video parts, resolution normalization `4K → 4k`, defense-in-depth aspect ratio + Scene Extension v2 duration validation), submit + poll response parsing (handles all three known response shapes including the Vertex `cloud.ai.large_models.vision.GenerateVideoResponse` payload), and a `--diagnose` CLI for verifying the auth setup against a free Gemini text-gen sanity check.
- **`--backend {auto,gemini-api,vertex-ai}` flag** on `video_generate.py`, default `auto`. Routes Vertex-only features through Vertex automatically and keeps text-to-video on Gemini API for v3.4.x compat. Zero breaking changes for existing users.
- **`--vertex-api-key` / `--vertex-project` / `--vertex-location` flags** on `video_generate.py` with the same precedence as `--api-key`: CLI flag → env var → `~/.banana/config.json`.
- **`vertex_api_key` / `vertex_project_id` / `vertex_location` fields** in `~/.banana/config.json`. Backward compat: existing configs without these fields continue to work for the Gemini API path.
- **Service-agent provisioning auto-retry** — the first Scene Extension v2 call against a fresh Vertex project returns a transient `"Service agents are being provisioned"` error (gRPC code 9) that auto-resolves in ~60-90 s. `video_generate.py` detects this specific error and retries once after a 90-second sleep, with a clear progress event explaining the wait. Subsequent failures surface to the user with a pointer to the Vertex AI service-agents doc.
- **Scene Extension v2 duration auto-override** — `video_generate.py` auto-overrides `--duration` to `7` when `--video-input` routes to Vertex (matches the auto-720p-downgrade pattern v3.5.0 added).
- **`backend` field in output JSON** — every successful generation now reports which backend produced it (`"backend": "gemini-api"` or `"backend": "vertex-ai"`).

### Changed
- **`--quality-tier draft` re-pointed from Fast to Lite** in `video_sequence.py`. The v3.5.0 stopgap mapped `draft` to Fast ($0.15/sec, 2.7× cheaper than Standard) because Lite was unreachable. v3.6.0 restores the original mapping to Lite ($0.05/sec, **8× cheaper**). On a 4-shot 30-second sequence, the draft pass cost drops from $4.80 to $1.60.
- **`video_extend.py --method` default flipped from `keyframe` back to `video`** (Scene Extension v2). The legacy keyframe path remains available via `--method keyframe` for users who need 1080p extension.
- **`download_expires_at` is now backend-scoped** — only emitted on the Gemini API path (where the 48-hour URI expiry actually applies). The Vertex AI path returns video bytes inline in the poll response, so there's no URI and no expiry. The stderr 48-hour warning is also Gemini-only.
- **`_submit_operation`, `_poll_operation`, `_save_video`** in `video_generate.py` are now backend-aware dispatchers. The Gemini API code paths are preserved byte-identical for backward compat; the Vertex paths call into the new `_vertex_backend` module.

### Docs
- **Full rewrite of `skills/video/references/veo-models.md`** Backend Availability section. Removes the v3.5.0 "Vertex AI only — gated" warnings, documents the 3-minute auth setup, explains why API-key auth works for Vertex (bound-to-service-account keys carry a service account principal), corrects the Lite duration and aspect ratio claims, lists the canonical protobuf type names from the REST reference (`VideoGenerationModelInstance`, `VideoGenerationModelParams`, `cloud.ai.large_models.vision.GenerateVideoResponse`), and explains that video retention only applies to the Gemini API path.
- **`skills/video/references/video-sequences.md` draft-then-final cost table** restored to the 8× story. The v3.5.0 "Gemini API today vs Vertex AI later" two-table workaround is gone — there's now one cost comparison and Lite is the default draft tier.
- **`skills/video/SKILL.md` Model Routing table** is back to 5 rows (draft / quick social / standard / hero / image-to-video / legacy) with a Backend column showing where each routes. The "Vertex AI only — gated" callout is gone.
- **README "What's New" section** rewritten with the v3.6.0 backend story.
- **CLAUDE.md** updated with the new helper script in the file responsibilities table and a new key-constraint about Vertex resolution case (`4k` lowercase) vs Gemini convention (`4K` uppercase).
- **ROADMAP** marks v3.6.0 as shipped, removes the "Vertex AI backend" line from the top, and promotes the deferred sequence production improvements to v3.6.1.

### Verification
- **Real API:** $0.55 spent across three smoke tests during research ($0.20 Lite text-to-video, $0.20 Lite image-to-video, $0.35 Lite Scene Extension v2 with retry) plus $0.20 for the commit 2 integration smoke test. Real MP4 artifacts saved to `/tmp/v360-verify/` and `/tmp/v360-commit2/` for inspection.
- **Zero-cost:** all 4 modified scripts compile clean, 18 unit checks via import on `_vertex_backend.py`, backend routing tested for all 4 combinations (auto + Gemini path, auto + Vertex path, explicit Gemini, explicit Vertex), 1:1 aspect rejection verified, Lite duration 4 acceptance verified, draft tier cost calculation confirmed at $1.11 for the test plan (down from $2.71).

## [3.5.0] - 2026-04-10

### ⚠️ Backend Reality Check

Real-API verification during the v3.5.0 release surfaced a critical distinction: **VEO 3.1 is split across two backends**. The plugin uses the Gemini API (`generativelanguage.googleapis.com`, API-key auth), while Lite, Legacy 3.0, GA `-001` IDs for Standard/Fast, and Scene Extension v2 (`--video-input`) are **Vertex AI only** (`*-aiplatform.googleapis.com`, OAuth/service-account auth). The Gemini API returns HTTP 404 for every `-001` ID and rejects `--video-input` with "inlineData isn't supported by this model." Until the Vertex AI backend ships in v3.6.0, the plugin gates these features with clear error messages and remaps `--quality-tier draft` to Fast instead of Lite. See `skills/video/references/veo-models.md` → Backend Availability for full details. Vertex AI support is now tracked as the top v3.6.0 roadmap item.

### Fixed
- **VEO Lite model ID** — the plugin previously shipped `veo-3.1-generate-lite-preview` which does not exist as a real API endpoint. v3.5.0 ships the correct GA ID `veo-3.1-lite-generate-001` for users running against Vertex AI directly, and documents it for the Gemini API path with a clear error pointing at the v3.6.0 Vertex AI backend.
- **VEO pricing** — the cost tracker's Standard rate was incorrectly set to $0.15/sec. Corrected to the official $0.40/sec ($3.20 per 8s clip) matching Google Cloud Vertex AI pricing. Fast ($0.15/sec) and Lite ($0.05/sec) tiers are now listed separately rather than conflated.

### Added
- **VEO 3.1 model variants** in `video_generate.py` — Fast tier (`veo-3.1-fast-generate-preview` / `-001`), Lite tier (`veo-3.1-lite-generate-001`), and Legacy 3.0 (`veo-3.0-generate-001`). Both preview and GA (`-001`) IDs are accepted for Standard and Fast.
- **Model-aware parameter validation** — Lite supports 5–60 s durations and 1:1 square aspect ratio; Standard/Fast reject those. 4K is rejected on Lite and Legacy 3.0.
- **`--negative-prompt`** flag on `video_generate.py` with Google's official guidance (describe what you want; use negatives only for known failure modes).
- **`--seed`** flag on `video_generate.py` for reproducible generations.
- **`--video-input`** flag on `video_generate.py` — Scene Extension v2 mode, mutually exclusive with image inputs, forces 720p.
- **`--quality-tier {draft,fast,standard,lite,legacy}`** flag on `video_sequence.py generate` and `estimate` — enables the draft-then-final workflow. `draft` currently maps to Fast ($0.15/sec, 2.7× cheaper than Standard) on the Gemini API; `lite` and `legacy` fail fast with a clear pointer to the v3.6.0 Vertex AI backend. A 4-shot 30-second sequence costs $4.80 at Fast draft vs $12.80 at Standard.
- **Per-shot and sequence-level `model`/`resolution` fields** in the plan.json schema, with a 3-level cascade (CLI override → shot → plan → default) and graceful fallback for old plans.
- **`--method {video,keyframe}`** flag on `video_extend.py`. Default is `video` (Scene Extension v2: passes previous clip directly, preserves audio continuity at 720p). `keyframe` retains the legacy last-frame extraction path at any resolution.
- **`--model` flag on `video_extend.py`** with per-hop cost estimation using the selected model's actual rate.
- **Token-limit prompt validation** in `video_generate.py` — warns at ~950 tokens (3,800 chars), hard-rejects at ~1,125 tokens (4,500 chars) to prevent confusing API-layer failures.
- **`download_expires_at` timestamp** in `video_generate.py` JSON output and a stderr warning about Google's 48-hour video retention window.
- **New `_veo_cost(model, duration_seconds)` helper** in `cost_tracker.py` with per-second fallback for Lite's extended 5–60 s range.
- **README: "VEO 3.1 Model Variants & Draft Workflow (v3.5.0)"** section.

### Changed
- **`video_extend.py` default method** is `keyframe` (last-frame extraction, works on the Gemini API today at any resolution). `--method video` (Scene Extension v2, preserves audio continuity) is documented but errors with a clear Vertex-AI-required message until v3.6.0.
- **`video_sequence.py` cost estimation** now uses real per-tier rates instead of a flat $1.20/clip. Output includes a per-model breakdown.
- **Video SKILL.md Model Routing table** rewritten with 5 scenarios (draft / quick social / standard / hero / legacy) and a draft-first recommendation.

### Docs
- **Full rewrite of `skills/video/references/veo-models.md`** with the VEO release timeline, 3-tier comparison table, GA vs preview IDs, 4K-is-AI-upscaled clarification, capability matrix, known limitations (character drift, text rendering, 8 s ceiling, silent output failures), 48-hour video retention, regional availability (EEA/Swiss/UK), rate limits, competitive context (Arena Elo 1381), and audio quality comparison.
- **`skills/video/references/video-sequences.md`** — new draft-then-final workflow section with cost comparison table, Gemini + VEO as Google's officially recommended pattern, timestamp prompting as a cost-reduction technique, and character drift mitigation framing.
- **`skills/video/references/video-prompt-engineering.md`** — new sections for timestamp prompting (`[00:00-00:02]` syntax), lens focal length guidance (16 mm / 35 mm / 50 mm / 85 mm table), dialogue timing (words-per-clip by duration), recommended negative prompt boilerplate, text rendering warning, and 100–200 word prompt-length target.
- **README** version badge bumped, model comparison table updated with all four VEO variants and per-second pricing.

## [3.4.1] - 2026-04-09

### Fixed
- **VEO API integration** -- Three bug fixes discovered when first running against real API:
  - Removed unsupported `personGeneration: allow_adult` parameter (text-to-video only allows `allow_all` or omission)
  - Fixed image format from `bytesBase64Encoded` to `inlineData.data` (matches API spec for first/last frame and reference images)
  - Fixed response path from `response.generatedSamples` to `response.generateVideoResponse.generatedSamples` (with fallback for older API versions)
  - Added API key authentication to video URI downloads
- Verified end-to-end: 4s and 6s clips successfully generated and downloaded

### Added
- **8 new feature images** in README: video pipeline, video domain modes, sequence production, storyboard workflow, A/B testing, deck builder, analytics dashboard, content pipeline
- **2 sample video clips** in README: product reveal (6s/1080p) and banana spinning (4s/720p) — actual VEO 3.1 outputs

## [3.4.0] - 2026-04-09

### Added
- **`/video extend`** -- Extend a clip by chaining: extract last frame, generate next clip, concatenate. +7s per hop, max 148s
  - `scripts/video_extend.py` -- automated multi-hop extension with progress tracking
- **`/video stitch`** -- FFmpeg video toolkit: concat, trim, convert, info
  - `scripts/video_stitch.py` -- concat multiple clips, trim to duration, convert formats, get video info

## [3.3.0] - 2026-04-09

### Added
- **`/video sequence`** -- Multi-shot video sequence production pipeline
  - `scripts/video_sequence.py` -- plan, storyboard, estimate, generate, stitch subcommands
  - Storyboard approval workflow: generate frame pairs with /banana before committing to video
  - First/last frame chaining: end frame of shot N = start frame of shot N+1
  - Target durations: 15s, 30s, 60s, 90s, 2min+ with shot count recommendations
  - `references/video-sequences.md` -- shot list format, consistency rules, cost estimation

## [3.2.0] - 2026-04-09

### Added
- **Image-to-video pipeline** -- `/video animate` with `image-to-video.md` reference documenting cross-skill workflow (/banana → /video)
- **Content pipeline video support** -- `content_pipeline.py` now supports `"video"` output type using hero image as first frame
- **Session history video type** -- `history.py` now accepts `--type video` for video generation logging

## [3.1.0] - 2026-04-09

### Added
- **Video domain modes** -- 6 modes (Product Reveal, Story-Driven, Environment Reveal, Social Short, Cinematic, Tutorial/Demo) with camera vocabulary and modifier libraries
- **Video audio guide** -- Dialogue, SFX, ambient, and music prompting strategies with domain-specific patterns
- **video-brief-constructor agent** -- Subagent for video prompt construction using 5-Part Framework
- **Shot types for sequences** -- Establishing, medium, close-up, cutaway, B-roll, transition with editing rhythm guide
- `references/video-domain-modes.md`, `references/video-audio.md`, `agents/video-brief-constructor.md`

## [3.0.0] - 2026-04-09

### Added
- **`/video` skill** -- New separate video generation skill powered by Google VEO 3.1
  - `skills/video/SKILL.md` (~188 lines) -- Video Creative Director orchestrator
  - `skills/video/scripts/video_generate.py` (~317 lines) -- Async VEO API with polling, first/last frame, reference images
  - `skills/video/references/veo-models.md` -- VEO model specs, pricing ($0.15-0.40/sec), rate limits
  - `skills/video/references/video-prompt-engineering.md` -- 5-Part Video Framework (Camera, Subject, Action, Setting, Style+Audio)
  - Text-to-video, image-to-video, and first/last frame keyframe interpolation
  - Same API key as image generation, same brand preset and asset registry
  - Commands: generate, animate, sequence, extend, stitch, cost, status

### Changed
- Updated `cost_tracker.py` with VEO per-second pricing (duration-based keys)
- Added cross-reference in banana SKILL.md pointing to `/video` skill

## [2.7.0] - 2026-04-09

### Added
- **`/banana content`** -- Multi-modal content pipeline: one idea → hero, social, email, formats
  - `scripts/content_pipeline.py` (~420 lines) orchestrates existing scripts via subprocess
  - Two-phase workflow: plan (cost estimate) → generate (execute step-by-step)
  - Dependency handling (email/formats wait for hero)
  - Status tracking with plan.json and manifest.json
  - `references/content-pipeline.md` -- output types, dependencies, cost estimation

## [2.6.0] - 2026-04-09

### Added
- **`/banana analytics`** -- Self-contained HTML analytics dashboard
  - `scripts/analytics.py` (~490 lines) with inline SVG charts (no external JS)
  - Cost timeline, model/domain breakdown, resolution distribution, quota gauge
  - Aggregates data from cost tracker, session history, and A/B preferences
  - `references/analytics.md` -- dashboard sections and data sources

## [2.5.0] - 2026-04-09

### Added
- **`/banana deck`** -- Slide deck builder: assemble generated images into editable .pptx
  - `scripts/deckbuilder.py` (~590 lines) with 3 layout modes: fullbleed, standard, split
  - Brand preset integration (colors, typography, logo placement)
  - Title slide + content slides + closing slide
  - Slide notes contain original prompts from generation-summary.json
  - `references/deck-builder.md` -- layouts, preset integration, logo handling

## [2.4.0] - 2026-04-09

### Added
- **`/banana ab-test`** -- Smart A/B testing with Literal/Creative/Premium prompt variations
  - `scripts/abtester.py` (~340 lines) generates variations, tracks ratings and preferences
  - Rating system (1-5 scale) with aggregate preference learning
  - Commands: generate, rate, preferences, history
  - `references/ab-testing.md` -- variation styles, rating system, preferences tracking

## [2.3.0] - 2026-04-09

### Added
- **`/banana history`** -- Session generation history with visual gallery export
  - `scripts/history.py` (~180 lines) tracks all generations per session
  - Commands: log, list, show, export (markdown gallery), sessions
  - Automatic logging integrated into pipeline Step 10
  - Export as markdown with image paths for inline rendering
  - `references/session-history.md` -- session ID management, export formats

## [2.2.0] - 2026-04-09

### Added
- **`/banana formats`** -- Multi-format image converter: generate once, convert to PNG/WebP/JPEG at 4K/2K/1K/512
  - `scripts/multiformat.py` (~200 lines) with 3-tier backend: ImageMagick v7 → v6 → macOS sips
  - Auto-detects source aspect ratio, scales to correct pixel dimensions per size tier
  - Outputs organized directory with `manifest.json` for downstream tools
  - `references/multi-format.md` -- size tables, format specs, prerequisites

## [2.1.0] - 2026-04-09

### Changed
- **Renamed project** from `banana-claude` to `nano-banana-studio` — new independent identity
- **Detached from GitHub fork network** — `gh` CLI now resolves correctly to this repo
- Updated all repo URLs, plugin name, and documentation references
- Updated CITATION.cff title and repository URL
- Updated install.sh with pre-flight check for conflicting banana-claude installation

### Added
- **Migration guide** in README — instructions for users switching from banana-claude
- **Conflict detection** in install.sh — warns if banana-claude plugin is already installed

## [2.0.1] - 2026-04-09

### Fixed
- **SKILL.md frontmatter** -- removed unrecognized `metadata` block (version/author belong in plugin.json)
- **SKILL.md argument-hint** -- expanded from 7 to 16 subcommands so all commands appear in autocomplete
- **SKILL.md pipeline flow** -- renumbered fractional steps (1, 1.5, 1.6) to sequential 1-11; moved feature sections (reverse, social, brand) after pipeline to restore uninterrupted flow
- **SKILL.md MANDATORY section** -- removed contradictory "read before every call" that conflicted with on-demand loading strategy
- **SKILL.md duplicate Response Format** -- removed standalone section already covered by Step 11
- **SKILL.md error table** -- added HTTP 5xx and invalid API key error rows
- **SKILL.md `/banana inspire`** -- added missing implementation guidance pointing to Proven Prompt Templates
- **marketplace.json** -- updated owner/homepage/repository URLs to match fork (juliandickie)
- **brief-constructor agent** -- fixed fragile relative paths, reduced maxTurns from 5 to 3
- **CLAUDE.md** -- updated version checklist from 4 files to 3 (SKILL.md no longer carries version)

## [2.0.0] - 2026-04-09

### Added
- **`/banana book`** -- visual brand book generator with three output formats:
  - **Markdown + images** -- `brand-book.md` with color tables (Hex/RGB/CMYK/Pantone) + categorized image folder
  - **PowerPoint (.pptx)** -- professional slide deck with brand colors, swatches, typography, photo samples
  - **HTML** -- self-contained single file with base64-embedded images + print CSS (open → Print → PDF)
- Three tiers: `quick` (5 images), `standard` (16), `comprehensive` (25+)
- `scripts/brandbook.py` -- orchestrator with image generation + 3 output formatters (~590 lines)
- `scripts/pantone_lookup.py` -- Hex→RGB→CMYK→Pantone color conversion with 156 Pantone Coated colors
- `references/brand-book.md` -- tiers, formats, options, color spec guide

## [1.9.1] - 2026-04-08

### Changed
- **`/banana reverse`** now provides three perspectives: Claude's interpretation, Gemini's interpretation, and a blended best-of-both prompt
  - Sends the image to Gemini via `gemini_chat` for a second opinion
  - Compares how each AI notices different details (Claude: structured/technical, Gemini: atmospheric/textural)
  - Blended version combines Claude's precision with Gemini's natural observation
  - Includes "What You Can Learn" section highlighting interesting differences

## [1.9.0] - 2026-04-08

### Added
- **`/banana reverse`** -- image-to-prompt reverse engineering
  - Analyzes an image and extracts a structured 5-Component Formula prompt
  - Identifies domain mode, estimates camera/lens/lighting, suggests prestigious context anchor
  - Outputs a complete reconstructed prompt ready to copy and use for recreation
  - `references/reverse-prompt.md` with analysis methodology and output format

## [1.8.0] - 2026-04-08

### Added
- **`/banana asset`** -- persistent asset registry for characters, products, equipment, and environments
  - `scripts/assets.py` with list, show, create, delete, add-image subcommands
  - `references/asset-registry.md` with usage guide, API limits, and CLI reference
  - Assets save named references with images and descriptions to `~/.banana/assets/`
  - Reference images passed as `inlineData` parts in Gemini API calls for visual consistency
  - Validates image size (7MB max), format (JPEG/PNG/WebP/HEIC/HEIF), and count (14 max)
  - Step 1.6 added to Creative Director pipeline for automatic asset detection

## [1.7.0] - 2026-04-07

### Added
- **`/banana social`** -- platform-native image generation for 46 social media platforms
  - Generates at nearest native ratio at 4K, auto-crops to exact platform pixel specs
  - Groups platforms by ratio to avoid duplicate API calls (4 platforms at same ratio = 1 generation)
  - 46 platforms across 12 families: Instagram, Facebook, YouTube, LinkedIn, Twitter/X, TikTok, Pinterest, Threads, Snapchat, Google Ads, Spotify
  - Complete + Image Only modes, platform-aware negative space prompting
  - `scripts/social.py` with generate, list, info subcommands
  - `references/social-platforms.md` with full spec tables and shorthand names
- **`/banana brand`** -- conversational brand guide builder (4-phase: gather sources → auto-extract → refine → preview and save)
  - Learns from websites (via browser tools), PDFs, reference images, or from scratch
  - Auto-extracts into 17-field Brand Style Guide schema
  - Generates preview image before saving
  - `references/brand-builder.md` with full conversational flow
- **12 example brand preset files** in `skills/banana/presets/`:
  tech-saas, luxury-dark, organic-natural, startup-bold, corporate-professional,
  creative-agency, healthcare-clinical, fashion-editorial, food-lifestyle,
  real-estate-luxury, fitness-energy, education-friendly
- Merged banana-installer into main skill (`/banana status`, `/banana update`)
- Feature Completion Checklist strengthened with Command Sync Check + Script Checks
- Plugin validation fixes (agent frontmatter, slides.py permissions, manifest author)

### Changed
- SKILL.md: 15 commands in Quick Reference (was 14)
- Plugin validated and passes all checks

## [1.6.0] - 2026-04-07

### Added
- **`/banana slides` pipeline** -- three-step batch slide deck generation:
  - `plan` -- Claude analyzes content and writes detailed visual design briefs
  - `prompts` -- Claude converts briefs to Nano Banana Pro prompts
  - `generate` -- `slides.py` batch-generates all slide images from prompts markdown
- **`slides.py`** script with `generate`, `estimate`, and `template` subcommands
- 4 new slide-type prompt templates: quote, section divider, image feature, infographic process
- `references/setup.md` -- extracted setup instructions for lazy loading

### Changed
- **SKILL.md restructured as lean orchestrator** (496 → 170 lines, 66% reduction)
  - Detailed content moved to lazy-loaded reference files
  - Duplicated tables (domain modes, aspect ratios, resolutions) removed -- single source in references
  - Setup instructions extracted to `references/setup.md`
  - 330 lines of headroom for future features (social, brand builder, video)
- Version bumped across all 4 files (plugin.json, SKILL.md, README, CITATION.cff)

## [1.5.0] - 2026-04-06

### Added
- **Presentation domain mode** with two generation options:
  - **Complete Slide** -- model renders headline/body text directly (leverages Nano Banana 2's 94% text accuracy)
  - **Background Only** -- clean backgrounds with negative space for layering in Keynote/PPT/Slides
- **Brand Style Guides** -- 8 new optional preset fields for project-wide visual consistency:
  - `background_styles` -- named background variants (dark-premium, gradient, split-layout)
  - `visual_motifs` -- pattern overlays with opacity
  - `prompt_suffix` -- appended verbatim to every prompt
  - `prompt_keywords` -- categorized keywords woven into prompts
  - `do_list` / `dont_list` -- brand guardrails checked before generation
  - `logo_placement` -- records post-production logo position (never mentioned in prompts)
  - `technical_specs` -- default color space, DPI, etc.
- **Logo exclusion rule** -- logos are NEVER mentioned in prompts (model generates artifacts). Described as "clean negative space" instead; logos composited in presentation software
- Presentation mode modifier library in prompt-engineering.md (background styles, layout zones, typography, pattern overlays, slide types)
- 4 Presentation prompt templates (2 Complete, 2 Background-Only)
- Brand Style Guide Integration section in prompt-engineering.md
- Expanded merge rules (items 6-12) for brand guide fields in presets.md
- 8 new CLI args in presets.py for brand guide creation
- README updated with new feature documentation, rationale, and upstream tracking

### Changed
- Domain modes expanded from 9 to 11 (Presentation Complete + Background)
- presets.py `create` command accepts brand guide fields (backward-compatible)
- Logo handling rewritten: replaced "reserve space for logo" with negative-space approach

## [1.4.2] - 2026-03-27

### Added
- **Replicate backend** -- `google/nano-banana-2` as alternative to MCP and Direct Gemini API
  - `scripts/replicate_generate.py` -- stdlib-only generation script
  - `scripts/replicate_edit.py` -- stdlib-only editing script
  - `references/replicate.md` -- full reference doc with params, pricing, error handling
- **5-Input Creative Brief** system in SKILL.md (Purpose, Audience, Subject, Brand, References)
- **Edit-First principle** elevated to core principle with edit-vs-regenerate decision matrix
- **Three Prompt Variations** (Literal/Creative/Premium) for `/banana batch`
- **Quality Checklist** in response verification step
- **PEEL Strategy** for structured spec refinement (Position, Expression, Environment, Lens)
- **Progressive Enhancement** 4-phase workflow for `/banana chat` sessions
- **Multilingual & Localization** section in prompt-engineering.md
- **Expanded Character Consistency** (identity-locked patterns, group photos, storytelling)
- **5 new Common Pitfalls** (contradictory instructions, impossible physics, style mixing, etc.)
- **Expanded Search Grounding** with practical examples table
- **Resolution pixel dimension tables** for all aspect ratios at 512/1K/2K/4K
- **Input Limits section** in gemini-models.md (14 images, 7MB inline, 500MB total, HEIC/HEIF)
- **Watermark Behavior by Tier** table (SynthID, visible sparkle, C2PA)
- **Thinking Visibility** docs (`includeThoughts`, thought images)
- `setup_mcp.py` now supports `--replicate-key` and `--check-replicate`
- Replicate pricing in cost_tracker.py and cost-tracking.md

### Changed
- Prompt engineering approach: "Start with Intent, Refine with Specs" (PEEL strategy)
- Fallback chain: MCP → Direct Gemini API → Replicate
- Output tokens per image corrected to up to ~2,520 (was ~1,290)

### Fixed
- Free tier rate limits in cost-tracking.md corrected to ~5-15 RPM / ~20-500 RPD (was ~10 / ~500)

## [1.4.1] - 2026-03-27

### Changed
- Restructured as official Claude Code plugin (`.claude-plugin/plugin.json` manifest)
- Added marketplace catalog (`.claude-plugin/marketplace.json`) for distribution via `/plugin marketplace add`
- Moved `banana/` to `skills/banana/` (standard plugin layout)
- Moved `.claude/agents/` to `agents/` (standard plugin layout)
- Plugin install is now the primary installation method
- Updated CI workflow, README, CLAUDE.md, and install.sh for new structure

### Fixed
- Git remote URL corrected from `claude-banana` to `banana-claude`
- Removed `firebase-debug.log` from git tracking

## [1.4.0] - 2026-03-19

### Breaking Changes
- Removed `gemini-3-pro-image-preview` (Nano Banana Pro) -- shut down by Google March 9, 2026
- Replaced 6-component Reasoning Brief with Google's official 5-component formula (Subject → Action → Location/Context → Composition → Style)
- Default resolution changed from `1K` to `2K` in fallback scripts
- Banned prompt keywords: "8K", "masterpiece", "ultra-realistic", "high resolution" -- use prestigious context anchors instead

### Added
- Banned Keywords section in prompt-engineering.md (Stable Diffusion-era terms that degrade quality)
- Negative Prompts guidance (semantic reframing, ALL CAPS for constraints)
- Prompt Length Guide (20-60 words quick draft → 200-300 complex)
- Text Rendering section for Nano Banana 2
- Domain-to-model routing table in gemini-models.md
- Resolution defaults by domain mode
- Error response taxonomy in mcp-tools.md (429, 400 FAILED_PRECONDITION, IMAGE_SAFETY)
- Non-existent parameters warning in mcp-tools.md
- `.claude/agents/brief-constructor.md` subagent for prompt construction
- `CLAUDE.md` at repo root with development context and testing instructions
- Mandatory reference loading instruction at top of SKILL.md
- Full generation pipeline with retry logic and error handling in SKILL.md
- Exponential backoff retry logic (429 handling) in generate.py and edit.py
- FAILED_PRECONDITION billing error detection in fallback scripts
- Prestigious context anchors replacing banned quality keywords in all templates

### Changed
- SKILL.md version bumped to 1.4.0 with improved frontmatter
- gemini-models.md fully restructured with NB2/NB naming, updated pricing ($0.067/1K)
- Model routing table uses 5-component references instead of 6-component
- All prompt templates updated to use prestigious anchors instead of banned keywords
- Prompt adaptation rules updated to remove banned keywords

### Fixed
- gemini-3-pro-image-preview listed as "Active" when it was dead since March 9
- Pricing was stale ($0.039 for 3.1 Flash when actual is $0.067)
- Rate limits updated to reflect 92% cut (Free: ~5-15 RPM / ~20-500 RPD)

## [1.3.0] - 2026-03-14

### Added
- **Multi-model routing** -- task-based model selection table (draft/standard/quality/text-heavy/batch)
- **Cost tracking** -- `cost_tracker.py` with log, summary, today, estimate, and reset commands
- **Direct API fallback** -- `generate.py` and `edit.py` scripts for when MCP is unavailable (stdlib only)
- **Brand/style presets** -- `presets.py` for reusable brand identities (colors, style, typography, lighting, mood)
- **CSV batch workflow** -- `batch.py` parses CSV files into generation plans with cost estimates
- **Green screen transparency pipeline** -- workaround for Gemini's lack of transparent backgrounds
- **Safety filter rephrase strategies** -- 5 rephrase patterns, common trigger categories, example rephrases
- Cost tracking reference (`references/cost-tracking.md`) with pricing table and free tier limits
- Brand presets reference (`references/presets.md`) with schema, 3 example presets, merge behavior
- Abstract domain mode added to README
- Step 1.5 (Check for Presets) in Creative Director pipeline
- `/banana preset` and `/banana cost` commands in Quick Reference
- Expanded error handling for MCP unavailable and safety filter false positives

### Changed
- Quality Presets section replaced with Model Routing table
- Pro model status updated: may still be accessible for image generation
- Pricing note: research suggests NB2 pricing may be ~$0.067/img
- Architecture diagram updated to show all 7 scripts and 6 references
- install.sh creates `~/.banana/` directory for cost tracking and presets

### Removed
- Legacy `nano-banana/scripts/__pycache__/` (orphaned .pyc files)

## [1.2.0] - 2026-03-13

### Added
- 4K resolution output via `imageSize` parameter (512, 1K, 2K, 4K)
- 5 new aspect ratios: 2:3, 3:2, 4:5, 5:4, 21:9 (14 total)
- Thinking level control (minimal/low/medium/high)
- Search grounding with Google Search (web + image)
- Multi-image input support (up to 14 references)
- Image-only output mode
- Safety filter documentation with `finishReason` values
- Pricing table, content credentials section (SynthID + C2PA)
- Resolution selection step (Step 4.5) in pipeline
- Character consistency multi-image reference technique
- Cover image, pipeline diagram, reasoning brief diagram, domain modes diagram

### Changed
- Rate limits corrected: ~10 RPM / ~500 RPD (reduced Dec 2025)
- `NANOBANANA_MODEL` default: `gemini-3.1-flash-image-preview`
- Search grounding key: `googleSearch` (REST format)
- Quality presets now include resolution column

### Fixed
- SKILL.md markdown formatting bug on text-heavy template line
- Contradictory prompt engineering mistake #9 wording

## [1.0.0] - 2026-03-13

### Added
- Initial release of Banana Claude
- Creative Director pipeline with 6-component Reasoning Brief
- 8 domain modes, MCP integration, post-processing pipeline
- Batch variations, multi-turn chat, prompt inspiration
- Install script with validation

[3.4.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.4.1
[3.4.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.4.0
[3.3.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.3.0
[3.2.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.2.0
[3.1.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.1.0
[3.0.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v3.0.0
[2.7.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.7.0
[2.6.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.6.0
[2.5.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.5.0
[2.4.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.4.0
[2.3.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.3.0
[2.2.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.2.0
[2.1.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.1.0
[2.0.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.0.1
[2.0.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v2.0.0
[1.9.1]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.9.1
[1.9.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.9.0
[1.8.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.8.0
[1.7.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.7.0
[1.6.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.6.0
[1.5.0]: https://github.com/juliandickie/nano-banana-studio/releases/tag/v1.5.0
[1.4.2]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.2
[1.4.1]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.1
[1.4.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.4.0
[1.3.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.3.0
[1.2.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.2.0
[1.0.0]: https://github.com/AgriciDaniel/banana-claude/releases/tag/v1.0.0
