# CLAUDE.md -- Development context for nano-banana-studio

This file is read by Claude Code when working inside this repository.

**Start every session by reading `PROGRESS.md`** -- it has full development
history, design decisions, and next steps.

## Third-party API reference (workspace-level)

Full LLMS documentation for integrated and evaluated third-party APIs lives at
`../dev-docs/` (workspace root, one level above this repo). **Always check
`../CLAUDE.md`'s dev-docs inventory BEFORE** updating prompt-engineering
references, answering model-capability questions, or planning an empirical
spike — the authoritative answer is often already pinned locally.

Specifically:
- **`../dev-docs/nano-banana-image-generation.md`** is the official Google
  Gemini 3.1 Flash Image prompting guide. Consult it before editing
  `skills/banana/references/prompt-engineering.md` or making any claim about
  Gemini 3.1 behaviour. Spike 6 in v3.7.3 would have been unnecessary if this
  file had been read first — the "describe the scene, don't list keywords"
  rule was already in the official guide.
- **`../dev-docs/google-nano-banana-2-llms.md`** is the Replicate model card
  confirming the Replicate `google/nano-banana-2` is the same
  `gemini-3.1-flash-image-preview` model as the direct Gemini API path.
- **`../dev-docs/elevenlabs-best-practices.md`** is the condensed ElevenLabs
  prompt-engineering guide — consult before tuning narration tags or voice
  design prompts.

Other files in `dev-docs/` cover ElevenLabs (full API), Google ADK (reference
only — not adopted), Replicate (OpenAPI schema + MCP server install guide),
and ByteDance Seedance 2.0 (v3.8.0 bake-off candidate). Most are large — query
via Explore subagent, not Read. **The full inventory and when-to-consult table
is the single source of truth in `../CLAUDE.md`** — do not duplicate it here.

## What this repo is

`nano-banana-studio` is a Claude Code **plugin** that enables AI image generation
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
| `skills/banana/references/gemini-models.md` | Model roster, routing table, resolution tables, input limits. Update when Google releases new models. |
| `skills/banana/references/prompt-engineering.md` | The prompt construction system: 5-component formula, 11 domain modes, PEEL strategy, brand guide integration. Update when Google publishes new guidance. |
| `skills/banana/references/mcp-tools.md` | MCP tool parameter reference. Update when Google changes the API. |
| `skills/banana/references/replicate.md` | Replicate backend API reference (`google/nano-banana-2`). |
| `skills/banana/references/presets.md` | Brand Style Guide schema (17 fields, 8 optional for brand guides). |
| `skills/banana/references/social-platforms.md` | 47 social media platform specs (pixels, ratios, negative space). Loaded by `/banana social`. |
| `skills/banana/references/brand-builder.md` | Brand guide creation flow (learn → refine → preview → save). Loaded by `/banana brand`. |
| `skills/banana/scripts/social.py` | Social media batch generation (generate, list, info). Groups by ratio to avoid duplicate API calls. |
| `skills/banana/references/setup.md` | Setup, install, update, status, sharing guide. Loaded on demand by `/banana setup/status/update`. |
| `skills/banana/presets/*.json` | 12 example brand guide presets. Copy to `~/.banana/presets/` to use. |
| `skills/banana/scripts/slides.py` | Slide deck batch generation (generate, estimate, template subcommands). |
| `skills/banana/scripts/generate.py` | Direct Gemini API fallback for generation. Uses urllib.request (stdlib). |
| `skills/banana/scripts/edit.py` | Direct Gemini API fallback for editing. Uses urllib.request (stdlib). |
| `skills/banana/scripts/replicate_generate.py` | Replicate API fallback for generation. Uses urllib.request (stdlib). |
| `skills/banana/scripts/replicate_edit.py` | Replicate API fallback for editing. Uses urllib.request (stdlib). |
| `skills/banana/references/asset-registry.md` | How to detect, load, and use persistent assets in generation. |
| `skills/banana/references/reverse-prompt.md` | Image → 5-Component Formula prompt extraction methodology. |
| `skills/banana/references/brand-book.md` | Brand book generator guide (tiers, formats, color specs). |
| `skills/banana/scripts/brandbook.py` | Brand book generator (markdown + pptx + html output). |
| `skills/banana/scripts/pantone_lookup.py` | Color conversion: Hex → RGB → CMYK → nearest Pantone (156 colors). |
| `skills/banana/scripts/assets.py` | Asset registry CRUD (list, show, create, delete, add-image). |
| `skills/banana/scripts/presets.py` | Brand Style Guide CRUD (list, show, create, delete). |
| `skills/banana/scripts/content_pipeline.py` | Multi-modal content pipeline orchestrator. |
| `skills/banana/references/content-pipeline.md` | Content pipeline output types, dependencies, cost estimation. |
| `skills/banana/scripts/analytics.py` | Analytics dashboard (HTML with SVG charts, cost/usage/quota). |
| `skills/banana/references/analytics.md` | Analytics dashboard sections, data sources, chart types. |
| `skills/banana/scripts/deckbuilder.py` | Slide deck builder (.pptx with brand styling, 3 layouts). |
| `skills/banana/references/deck-builder.md` | Deck assembly, layouts, preset integration, logo handling. |
| `skills/banana/scripts/abtester.py` | A/B prompt variation tester with preference tracking. |
| `skills/banana/references/ab-testing.md` | A/B variation styles, rating system, preferences. |
| `skills/banana/scripts/history.py` | Session generation history (log, list, show, export, sessions). |
| `skills/banana/references/session-history.md` | Session history tracking, gallery export, session ID management. |
| `skills/banana/scripts/multiformat.py` | Multi-format image converter (PNG/WebP/JPEG at 4K/2K/1K/512). |
| `skills/banana/references/multi-format.md` | Multi-format conversion guide (sizes, formats, prerequisites). |
| `skills/banana/scripts/batch.py` | CSV batch workflow parser with cost estimates. |
| `skills/banana/scripts/cost_tracker.py` | Cost logging and summaries (log, summary, today, estimate). |
| `skills/banana/scripts/setup_mcp.py` | MCP + Replicate key configuration. Stores keys in ~/.banana/config.json. |
| `skills/banana/scripts/validate_setup.py` | Installation and setup verification checks. |
| `skills/banana/references/cost-tracking.md` | Pricing table, free tier limits, usage tracking guide. |
| `skills/banana/references/post-processing.md` | ImageMagick/FFmpeg pipelines, green screen transparency, format conversion. |
| `skills/video/SKILL.md` | Video Creative Director orchestrator. Defaults to Kling v3 Std as of v3.8.0; VEO is opt-in backup via `--provider veo`. |
| `skills/video/scripts/video_generate.py` | Async video generation with polling. Routes between Gemini API (VEO preview), Vertex AI (VEO GA + image-to-video + Scene Ext v2), and **Replicate (Kling v3 Std, v3.8.0+ default)** via `--backend` dispatch. |
| `skills/video/scripts/_vertex_backend.py` | Pure data translation helper for Vertex AI VEO surface. URL composer, request body builder, response parsers, service-agent provisioning detection, `--diagnose` CLI. Imported by `video_generate.py` when `--backend auto` routes to Vertex. Stdlib only. |
| `skills/video/scripts/_replicate_backend.py` | **v3.8.0+ (Fabric added v3.8.1)** — Pure data translation helper for Replicate predictions API. Hosts both Kling v3 Std (video) and Fabric 1.0 (lip-sync) model registry entries. Kling: multi_prompt/duration/aspect/mode validation. Fabric: resolution (480p/720p) + image/audio format validation + `audio_path_to_data_uri` helper. Response parsers handle the full 6-value status enum (including `aborted`). HTTP helpers use `Authorization: Bearer` + `User-Agent: nano-banana-studio/...` to avoid Cloudflare rejection on `/v1/account`. `--diagnose` CLI pings the free account endpoint and lists registered models per-family. Stdlib only. |
| `skills/video/scripts/video_lipsync.py` | **v3.8.1+** — Standalone runner for Fabric 1.0 audio-driven lip-sync. Argparse: `--image FACE --audio AUDIO [--resolution 480p\|720p]`. Imports `_replicate_backend` for HTTP plumbing + validation + data-URI encoding — zero duplicated Replicate logic. Poll loop, download, and save follow the same pattern as `video_generate.py::_poll_replicate`. Closes the v3.8.0 gap where VEO-generated speech couldn't be paired with audio_pipeline.py custom voices. See `references/lipsync.md` for the 2-step narrate→lipsync workflow. |
| `skills/video/scripts/video_sequence.py` | Multi-shot sequence pipeline (plan → storyboard → generate → stitch). As of v3.8.0, all auto-selected quality tiers (draft/fast/standard/premium/lite/legacy) route to Kling v3 Std. `veo-backup` tier is opt-in VEO 3.1 Lite. |
| `skills/video/scripts/video_extend.py` | **DEPRECATED in v3.8.0.** Requires `--acknowledge-veo-limitations` flag or exits with code 2. Per spike 5 Phase 2C, VEO extended workflows produce glitches and inconsistent actors at 30s. Use `video_sequence.py` with Kling shot list for extended workflows instead. |
| `skills/video/references/kling-models.md` | **v3.8.0+ (Seedance retest appended v3.8.1)** — Kling v3 Std default model, capabilities, multi_prompt JSON schema, pricing ($0.16/8s pro mode), extended workflows via shot-list pipeline, known limitations (English+Chinese audio only, character variation across separate generations). v3.8.1 appends the Seedance 2.0 retest verdict: **permanently rejected for human-subject workflows** (E005 filter consistent across all tested human subjects; only non-human mascots pass). Authoritative source: `dev-docs/kwaivgi-kling-v3-video-llms.md`. |
| `skills/video/references/lipsync.md` | **v3.8.1+** — Fabric 1.0 audio-driven lip-sync reference: why the subcommand exists (closes the VEO external-audio gap), capabilities table (480p/720p, 60s max, mp3/wav/m4a/aac, jpg/jpeg/png), canonical 2-step workflow (`audio_pipeline.py narrate` → `video_lipsync.py`), cost comparison vs Kling/VEO alternatives, known limitations (mouth region only, no camera movement, no emotional direction beyond audio prosody). Authoritative source: `dev-docs/veed-fabric-1.0-llms.md`. |
| `skills/video/references/veo-models.md` | VEO model specs, pricing, rate limits, **v3.8.0 "BACKUP ONLY" status** with spike 5 scoreboard, 5 Vertex API constraints discovered in Phase 2, Lite/Fast/Standard tier comparison findings, Backend Availability (Gemini API vs Vertex AI), auth setup. |
| `skills/video/references/video-prompt-engineering.md` | 5-Part Video Framework, templates, camera motion vocabulary. |
| `skills/video/scripts/audio_pipeline.py` | **v3.7.1+v3.7.2** — Multi-provider audio replacement pipeline (renamed from `elevenlabs_audio.py` in v3.7.2 when Lyria was added as the default music source). Subcommands: `pipeline` (canonical end-to-end with parallel TTS+music), `narrate`, `music --source lyria\|elevenlabs`, `mix`, `swap`, `voice-design`, `voice-promote`, `voice-list`, `status`. Stdlib only. |
| `skills/video/references/audio-pipeline.md` | **v3.7.1+v3.7.2** — Reference for the audio replacement architecture (renamed from `elevenlabs-audio.md` in v3.7.2). Covers Lyria + ElevenLabs music providers with the 5-way bake-off results, voice management (design → promote → use), prompt engineering for both TTS and music, FFmpeg parameter rationale, custom voice schema, cost model. |
| `agents/brief-constructor.md` | Subagent for prompt construction. |

## Scripts use stdlib only

All fallback scripts (`generate.py`, `edit.py`, `replicate_generate.py`, `replicate_edit.py`)
use Python's `urllib.request` to call APIs directly. They have ZERO pip dependencies by design.
Do NOT add `google-genai`, `requests`, or `replicate` as dependencies -- the stdlib approach
ensures the skill works on any system with Python 3.6+.

## Key constraints

- `imageSize` parameter values must be UPPERCASE on the Gemini API: "1K", "2K", "4K". Lowercase fails silently.
- **Vertex AI uses lowercase `"4k"` for VEO `resolution`**, while the Gemini API and the plugin's existing image-gen scripts use uppercase `"4K"`. `_vertex_backend.build_vertex_request_body()` normalizes `"4K" → "4k"` at the request boundary so callers can keep using the uppercase convention. Don't change the plugin convention.
- Gemini generates ONE image per API call. There is no batch parameter.
- No negative prompt parameter exists. Use semantic reframing in the prompt.
- `responseModalities` must explicitly include "IMAGE" or the API returns text only.
- **Describe the scene, don't list keywords.** Gemini 3.1's core strength is narrative understanding — prose beats tag lists. (Google's official Gemini 3.1 Flash Image prompting guide, verified 2026-04-15.)
- **Don't name publication formats** in prompts: `"Vanity Fair magazine cover style"`, `"National Geographic cover story"`, `"Wallpaper* editorial"`, etc. Gemini 3.1 renders the output as a literal magazine cover with masthead typography and headline text overlays. This supersedes the v3.6.x "use prestigious context anchors" rule, which was empirically shown to be harmful in spike 6 (2026-04-15). See `skills/banana/references/prompt-engineering.md` → "Prompt Patterns That Don't Help".
- The old "banned keywords" list (`"8K"`, `"masterpiece"`, `"ultra-realistic"`, `"high resolution"`) is useless on Gemini 3.1 but not harmful. Cut them to save tokens; don't panic if a user's source prompt contains them.
- NEVER mention "logo" in Presentation mode prompts -- the model generates unwanted logo artifacts. Describe the area as "clean negative space" instead. Logos are composited in presentation software.
- Brand Style Guide fields in presets are optional -- old presets without them continue to work.
- Fallback chain: MCP (primary) -> Direct Gemini API -> Replicate.
- **v3.7.1 audio architecture**: For multi-clip stitched VEO sequences that need narration or seam-free music, use `elevenlabs_audio.py pipeline` to replace the entire audio bed instead of relying on VEO's emergent audio. VEO's clip-locked music intro/outro envelopes create audible seams when concatenated; the v3.7.1 pipeline replaces them with a single continuous track. See `skills/video/references/elevenlabs-audio.md`.
- **v3.7.1 narration line-length rule**: For VEO native narration, target line word count = `duration_seconds × (voice_wpm / 60)`. ~16 words for an 8s clip at native VEO narrator pace (~120 wpm). Shorter lines trigger a known failure mode where VEO sings the line to fill time. Per-voice WPM differs (Daniel ~137, Nano Banana Narrator ~159) — see F8 in `references/video-audio.md`.
- **v3.7.1 narrator + visible character constraint**: When a human is visible in the VEO frame, prompting `"A narrator says..."` will cause VEO to lip-sync them to the line regardless of `NOT speaking, mouth closed` constraints. Workarounds: (a) frame the human without face visible, (b) use the v3.7.1 audio replacement pipeline to override VEO's lip-synced audio. See F1-F2 in `references/video-audio.md`.
- **Eleven Music API blocks named-creator/brand prompts**. Returns HTTP 400 with `bad_prompt` and a `prompt_suggestion`. This is music-API-specific — image generation prompts welcome creator names. Strip named-creator references from music prompts before sending. See F6 in `references/video-audio.md`.
- **Custom voice schema** (v3.7.1+): `~/.banana/config.json` `custom_voices.{role}` is the canonical location. Role-keyed (narrator, character_a, etc.), supports three creation paths via `source_type` discriminator (designed | cloned | library), provider-pluggable for future second-provider support.
- **v3.7.2 music provider default is Lyria 2** (Google Vertex AI `lyria-002`), with ElevenLabs Music as the alternative via `--music-source elevenlabs`. Lyria is $0.06/call fixed, 32.768s clip duration, 48kHz/192kbps stereo, supports `negative_prompt`. Reuses the existing `vertex_api_key` + `vertex_project_id` + `vertex_location` from VEO setup — no new credentials. **Lyria's docs only mention OAuth auth but spike 4 confirmed API-key auth works** (same pattern as VEO). See `references/audio-pipeline.md` "Music sources" for the 5-way bake-off results and decision matrix.
- **Both music APIs (Lyria and Eleven Music) reject prompts containing named copyrighted creators or brands** (e.g. "Annie Leibovitz", "BBC Earth"). This is music-API-specific — image generation prompts welcome creator names. Strip named-creator references from music prompts before sending. See F6 in `references/video-audio.md`.
- **Audio gen model quality is uncorrelated with spec-sheet metrics** (F13 in `references/video-audio.md`). Spike 4 5-way bake-off proved this: Stable Audio 2.5 had the strongest specs but was rated worst by listening test; Lyria won despite being slower than Stable Audio. **Always evaluate new audio providers via subjective listening, not benchmark comparison.**
- **v3.7.4 stereo mix rule**: `audio_pipeline.py`'s `SIDECHAIN_FILTER` uses `aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0` on the narration branch (NOT `aformat=channel_layouts=stereo` alone). FFmpeg's `aformat` sets metadata but does not upmix mono sources to stereo — the v3.7.1 filter produced "stereo container with silent right channel" that sounded like speaker-left-only narration on headphones. The canonical mono-to-stereo upmix is `pan=stereo|c0=c0|c1=c0`, and the `mix_narration_with_music` ffmpeg invocation also passes `-ac 2` to lock the output channel count. Do not revert to the v3.7.1 pattern.
- **v3.7.4 client-side named-creator strip**: `audio_pipeline.py` maintains a `NAMED_CREATOR_TRIGGERS` list (20+ entries across photographers, publications, composers, broadcasters, pop artists) and strips any case-insensitive match from music prompts before sending to Lyria or ElevenLabs Music. This replaces the "don't name creators" user-side rule with a client-side safety net. Users can bypass with `--allow-creators` (e.g. to test whether the upstream filter has relaxed for a specific term or to handle false positives like the word "Drake" in a duck-themed prompt). The list lives in one place and covers both providers.
- **v3.7.4 Lyria long-music path**: when `length_ms > 32768` and `source=lyria`, `generate_music()` auto-routes to `generate_music_lyria_extended()` which makes N Lyria calls, chains them with FFmpeg `acrossfade=d=2:c1=tri:c2=tri`, trims to exact target. Cost: N × $0.06. For 90s = 3 calls = $0.18. If cost predictability matters over per-clip-control, fall back to `--music-source elevenlabs` which handles any length up to 600000ms in a single subscription-billed call.
- **v3.7.4 Instant Voice Cloning**: the `voice-clone` subcommand uploads 30+ seconds of audio (single file or directory of files) to `POST /v1/voices/add` via a new `_http_post_multipart()` stdlib helper. Result persists to `custom_voices.{role}` with `source_type=cloned` and `design_method=ivc`. If the response contains `requires_verification: true`, the voice is persisted but unusable until the user completes the ElevenLabs voice captcha in the dashboard. **Professional Voice Cloning (PVC) is NOT implemented** — deferred to v3.7.5+ as a separate subcommand since it needs 30+ minutes of audio + Creator+ plan + a multi-step fine-tuning workflow. The `source_type=cloned` enum value is shared between IVC and future PVC.
- **v3.7.4 auto-measured per-voice WPM**: `voice-promote` and `voice-clone` now auto-measure WPM after creation by generating a 38-word neutral reference phrase, probing the MP3 duration with ffprobe, computing `word_count / (duration_sec / 60)`, and persisting to `custom_voices.{role}.wpm`. The retroactive `voice-measure --role ROLE` subcommand measures existing pre-v3.7.4 voices. This replaces the hardcoded `Daniel ~137, Nano Banana Narrator ~159` values in the v3.7.1 line-length calibration rule (F8 in `references/video-audio.md`). The Creative Director skill should read `custom_voices.{role}.wpm` directly rather than guessing at per-voice pace. Measurement cost is negligible (one TTS call). Auto-measure is SKIPPED on voice-clone when `requires_verification: true` — run `voice-measure` manually after completing the captcha.
- **v3.8.0 default video model is Kling v3 Std** (`kwaivgi/kling-v3-video` via Replicate), replacing VEO 3.1 Standard. Per spike 5 (94 generations, ~$53 total spend): Kling wins 8 of 15 playback-verified shot types to VEO Fast's 0, is 7.5× cheaper per 8s clip, and produces coherent 30s narratives where VEO's extended workflow produces "glitches, inconsistent actors, horrible" (user verdict 2026-04-15). VEO remains callable as opt-in backup via `--provider veo --tier {lite|fast|standard}`. Full spike findings at `spikes/v3.8.0-provider-bakeoff/writeup/v3.8.0-bakeoff-findings.md`.
- **v3.8.0 Kling parameter constraints** (all from the Kling v3 Std model card at `dev-docs/kwaivgi-kling-v3-video-llms.md`, enforced client-side by `_replicate_backend.validate_kling_params()`): aspect_ratio ∈ {16:9, 9:16, **1:1**} — Kling is the only plugin-registered model with 1:1 support; duration integer in [3, 15]; mode ∈ {standard (720p), pro (1080p)} — no 4K support; multi_prompt is a JSON array STRING with max 6 shots, min 1s per shot, and **sum of shot durations MUST equal the top-level `duration`** parameter (hardest rule, easy to miss); `end_image` requires `start_image`; start_image max 10 MB; prompt/negative_prompt max 2500 chars.
- **v3.8.0 Kling audio limitation**: per the model card's "Limitations" section, audio generation works best in English and Chinese only. Other languages are unverified. For non-English-or-Chinese workflows, generate with `generate_audio: false` and use `audio_pipeline.py` with ElevenLabs TTS + Lyria music for the audio bed.
- **v3.8.0 `aspect_ratio` + `start_image` mutual exclusion**: when both are provided to Kling, `aspect_ratio` is IGNORED and the output uses the start image's native aspect ratio. `validate_kling_params()` logs a WARNING but does not raise. The SKILL.md orchestrator instructs Claude to offer cropping/padding the start image if the aspect conflict matters to the user.
- **v3.8.0 Replicate Cloudflare + User-Agent**: `api.replicate.com/v1/account` returns HTTP 403 (Cloudflare error code 1010) on requests with the default Python-urllib User-Agent. `_replicate_backend.py` sends `User-Agent: nano-banana-studio/3.8.0 (+https://github.com/juliandickie/nano-banana-studio)` on every request to avoid the WAF heuristic. The existing image-gen `replicate_generate.py` does NOT set a User-Agent and works only because `/v1/models/.../predictions` endpoints have more lenient Cloudflare rules — adding User-Agent to that script is a candidate v3.8.x hardening.
- **v3.8.0 `Prefer: wait=0` is non-spec-compliant**: Replicate's OpenAPI regex is `^wait(=([1-9]|[1-9][0-9]|60))?$`, so `wait=0` doesn't match. The spike's `lib/replicate_client.py` used `wait=0` and it happened to work. `_replicate_backend.py` omits the `Prefer` header entirely for async-first semantic (correct for Kling's 3-6 min wall times). If a future use case needs sync mode, use `wait=N` with N ∈ [1, 60].
- **v3.8.0 Replicate Prediction.status has 6 values, not 5**: the spike's client only handles `starting | processing | succeeded | failed | canceled`. The OpenAPI schema explicitly adds `aborted` (terminated before `predict()` is called, e.g., queue eviction or deadline). `_replicate_backend.parse_replicate_poll_response()` maps `aborted` to the "failed" bucket — if we missed this, the poll loop would spin forever on aborted predictions.
- **v3.8.0 `video_extend.py` is deprecated**: hard gate via `--acknowledge-veo-limitations` flag. Running without the flag exits with code 2 and a JSON message pointing users at `video_sequence.py` with the Kling shot-list pipeline. Per spike 5 Phase 2C, VEO's Scene Extension v2 + keyframe fallback produces glitches and inconsistent actors at 30s — user verdict: "horrible, do not use". This is hard-gated, not just warned, to prevent accidental use.
- **v3.8.0 Kling chain helper deferred**: the spike's `extended_run.py` proved last-frame-chaining Kling calls works for single-continuous-long-shot workflows, but the existing `video_sequence.py` shot-list pipeline already handles extended workflows via independent Kling calls per shot. A dedicated Kling chain helper is deferred to v3.8.x if a specific single-continuous-30s use case emerges.
- **v3.8.1 Fabric 1.0 lip-sync via `/video lipsync`**: new standalone `video_lipsync.py` runner for VEED Fabric 1.0 (`veed/fabric-1.0` on Replicate). Takes image + audio + resolution ∈ {480p, 720p}, produces a talking-head MP4 where the face is lip-synced to the audio. Closes the v3.8.0 gap where VEO generated speech internally and Kling didn't accept audio input — so custom-designed ElevenLabs voices from `audio_pipeline.py narrate` had no way to reach a visible character's face. The recommended flow is 2-step: `audio_pipeline.py narrate --voice brand_voice --out /tmp/narr.mp3` → `video_lipsync.py --image face.png --audio /tmp/narr.mp3`. See `references/lipsync.md`.
- **v3.8.1 Fabric 1.0 constraints**: input formats image ∈ {jpg, jpeg, png}, audio ∈ {mp3, wav, m4a, aac}. Output resolution ∈ {480p, 720p} (no 1080p or 4K). Max duration 60 seconds (driven by audio length). No prompt parameter — Fabric ONLY animates the face, nothing else in the frame. No camera movement, no body animation, no emotional direction beyond audio prosody. Cost approximately $0.30/call (verified empirically in v3.8.1 Fabric smoke test — update this with the real number).
- **v3.8.1 User-Agent hardening applied to image-gen Replicate scripts**: `skills/banana/scripts/replicate_generate.py` and `replicate_edit.py` now send `User-Agent: nano-banana-studio/3.8.1 (+https://github.com/juliandickie/nano-banana-studio)` on every Replicate request. Defensive fix — the image-gen scripts currently work without User-Agent, but the video-side `_replicate_backend.py` hit HTTP 403 Cloudflare error 1010 on `/v1/account` without it. The same edge rules could tighten on `/v1/models/.../predictions` at any time; the UA header is forward-compatible hardening.
- **v3.8.1 Seedance 2.0 retest verdict — permanently rejected**: The user-requested retest (3 diverse Phase 2 subjects: woman in home office, woman athlete, cartoon robot mascot) completed 2026-04-15. Results: 2 of 3 FAILED with `E005 — input/output flagged as sensitive` on both human subjects (talking head AND athlete). Only the non-human cartoon robot mascot succeeded. Pattern is consistent with Phase 1's rejection on the bearded-man subject: **any human subject triggers the ByteDance safety filter**. Seedance is NOT wired into the plugin as a default, backup, or tertiary provider — it's unusable for the plugin's primary workflows (human subjects, product demos, talking heads, social content). Retest spend: $0.14 + $0.48 (anchors). Documented in `references/kling-models.md` "Seedance 2.0 retest outcome (v3.8.1)" section.
- **v3.8.1 Vertex smoke-test subcommand on `_vertex_backend.py`**: new `smoke-test` subparser (sibling to `diagnose`) that validates spike 5 Phase 2 Vertex API constraints via 3 FREE probes: (1) preview-ID → 404, (2) invalid aspect ratio "1:1" → HTTP 400, (3) Gemini auth ping. **Only free probes** — an earlier design accidentally burned ~$3.60 by submitting minimal valid VEO requests that passed validation at submit time but generated real videos. The fix: only use probes that reject at URL resolution (404) or synchronously at submit validation. The other 2 constraints (GA -001 reachability, duration {4,6,8}) are documented in the output as "requires budget to verify" rather than auto-tested.
- **v3.8.1 empirical finding — Vertex drift from spike 5 Phase 2**: During the smoke-test design, Vertex accepted `durationSeconds=5` on VEO 3.1 Lite GA -001 instead of rejecting it synchronously as spike 5 Phase 2 observed. This suggests either (a) the duration constraint has relaxed on this Vertex project, (b) validation moved from synchronous to asynchronous. Either way, the spike 5 finding "Vertex validates durations synchronously at submit time" is no longer reliable as of 2026-04-15. The v3.8.1 smoke test does NOT test duration to avoid the billing trap; this drift is documented in `references/veo-models.md` and in the smoke-test's "untested constraints" output section.

## Upstream tracking

Originally forked from https://github.com/AgriciDaniel/banana-claude (v1.4.1 baseline), now an independent project.

To check for upstream changes:
```bash
git fetch upstream
git diff upstream/main
```

Our additions over upstream: Replicate backend, Presentation mode, Brand Style Guides,
research-driven prompt improvements (5-Input Creative Brief, PEEL strategy, Edit-First,
Progressive Enhancement, expanded character consistency, multilingual support).

## Installation

Test locally: `claude --plugin-dir .` or standalone: `bash install.sh`

## Feature Completion Checklist

**MANDATORY: After completing ANY feature or significant change, run through this
entire checklist before committing.** Do not skip items. Do not batch them for later.

### 1. Version Bump (ALL 3 files)

| File | What to update |
|------|---------------|
| `.claude-plugin/plugin.json` | `"version"` field |
| `README.md` | Version badge number in shields.io URL |
| `CITATION.cff` | `version` field + `date-released` to today |

Do NOT set version in `marketplace.json` -- it conflicts with `plugin.json`.
SKILL.md no longer carries version -- `plugin.json` is the authoritative source.

### 2. Documentation Updates

| File | What to update |
|------|---------------|
| `CHANGELOG.md` | Add new `## [X.Y.Z]` section with Added/Changed/Fixed. Add link reference at bottom. |
| `README.md` | Update "What's New in This Fork" section if feature is user-facing. Update architecture diagram if new files created. Update commands table if new commands added. |
| `PROGRESS.md` | Add session entry with numbered list of what was done. Update priority table if roadmap item completed. Update version in header. |
| `ROADMAP.md` | Mark completed features. Update version reference. |
| `CLAUDE.md` | Update file responsibilities table if new files created. Update key constraints if new rules added. |

### 3. README "What's New in This Fork" Check (IMPORTANT — frequently missed)

If the feature is user-facing, it MUST appear in the README "What's New in This Fork" section.
Each feature gets a `### Feature Name (vX.Y.Z)` heading.

**CRITICAL — README subsections are sales copy, not changelog entries.** The README is the plugin's sales page. The job of a What's New subsection is to convince a prospective user that the feature is valuable in the time it takes to read 1–3 sentences. Detailed decision trees, bullet lists of every change, empirical findings, cost breakdowns, and implementation notes all belong in CHANGELOG.md / PROGRESS.md / ROADMAP.md — **not** in README.

| Pattern | Belongs in |
|---|---|
| "Feature X lets you do Y so that Z." (1–3 sentences, ≤100 words) | README |
| "Five more deferred-bucket items — the theme is..." followed by 5 bullets | CHANGELOG |
| Empirical spike findings, file-size variance, cost tables | CHANGELOG + PROGRESS |
| Setup walkthrough, config field names, CLI flag lists | Reference docs + CHANGELOG |
| Internal rationale ("the coffee shop demo surfaced...") | PROGRESS |
| "Why [decision]" / "What this unlocks" paragraphs | PROGRESS or the reference doc |

**Target length:** match the style of the v2.x entries (`### Asset Registry (v1.8.0)`, `### Analytics Dashboard (v2.6.0)`, etc.) — 1–3 sentences, value-forward, no sub-bullets unless the feature genuinely ships multiple user-facing capabilities worth naming separately (e.g. v3.7.1 shipped both the audio pipeline AND custom voice design — two distinct value props, so two short paragraphs is OK).

**Rule of thumb:** if a user would read the README subsection and think "that's the *news*, not a *summary*," it's too long. Cut it in half and move the details to CHANGELOG.

**Retrospective correction:** v3.6.0–v3.6.3 README subsections were written as mini-changelogs with 5-7 bullets each and were slimmed to 1-3 sentences in v3.7.3. Do not regenerate that mistake on future releases — check this section before writing the What's New paragraph.

### 4. Command Sync Check (IMPORTANT — frequently missed)

Every command in SKILL.md Quick Reference table MUST also appear in:
- **README.md Commands table** — exact same commands and descriptions
- **README.md Quick Start section** — include examples for major new commands

Run this to verify:
```bash
echo "=== SKILL.md ===" && grep '| `/banana' skills/banana/SKILL.md
echo "=== README ===" && grep '| `/banana' README.md
```
If they don't match, update README before committing.

### 5. README Architecture Diagram Check (IMPORTANT — frequently missed)

If ANY new files were created (scripts, references, presets, etc.), the architecture
tree diagram in README.md MUST be updated to include them. Also verify the version
number and SKILL.md line count in the diagram are current.

Run this to compare:
```bash
echo "=== Diagram files ===" && grep '│' README.md | grep -oE '[a-z_-]+\.(md|py|json)' | sort
echo "=== Actual files ===" && (ls skills/banana/references/ skills/banana/scripts/) | sort
```
If the lists don't match, update the diagram.

### 6. Cross-File Consistency Check (versions, models, ratios)

After all edits, verify these match across files:
- **Version number** identical in all 3 version files (plugin.json, README.md badge, CITATION.cff)
- **File list** in CLAUDE.md file responsibilities table matches what exists on disk
- **Model names** and **rate limits** consistent across gemini-models.md, cost-tracking.md, mcp-tools.md
- **Aspect ratios** consistent across gemini-models.md, replicate.md, generate.py, replicate_generate.py

### 7. New Script Checks

If any new Python scripts were created:
- `chmod +x` — all scripts in `scripts/` must be executable
- Verify they compile: `python3 -c "import py_compile; py_compile.compile('path', doraise=True)"`
- Test `--help` works

### 8. SKILL.md Size Check

```bash
wc -l skills/banana/SKILL.md  # Must stay under 500 lines
```

Current: ~200 lines (lean orchestrator pattern). If approaching 300+, extract to reference files.

### 9. Memory File

Update `~/.claude/projects/.../memory/project_nano_banana_studio_workflow.md` if:
- Version changed
- New key constraints added
- Architecture changed (e.g., new skill files, new reference files)

### 10. Git Commit

Stage specific files (not `git add -A`). Commit with descriptive message following the pattern:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation only
- `refactor:` for restructuring

Push to fork: `git push origin main`

### 11. GitHub Release + Distribution Zips (on version bumps)

When a version is bumped, create a GitHub Release with distribution zips:

```bash
# Build plugin zip (excludes .git, screenshots, dev files, .claude/)
cd /path/to/nano-banana-studio
zip -r ../nano-banana-studio-vX.Y.Z.zip . -x ".git/*" ".DS_Store" "*/.DS_Store" \
  "*__pycache__/*" "*.pyc" ".github/*" "screenshots/*" "PROGRESS.md" \
  "ROADMAP.md" "CODEOWNERS" "CODE_OF_CONDUCT.md" "SECURITY.md" \
  "CITATION.cff" ".gitattributes" ".gitignore" ".claude/*"

# Build skill zip (standalone, no plugin wrapper)
mkdir -p /tmp/banana-skill/banana
cp -r skills/banana/* /tmp/banana-skill/banana/
cp agents/brief-constructor.md /tmp/banana-skill/banana/
cd /tmp/banana-skill && zip -r /path/to/banana-skill-vX.Y.Z.zip banana/
rm -rf /tmp/banana-skill

# Create GitHub Release with zips attached
gh release create vX.Y.Z \
  ../nano-banana-studio-vX.Y.Z.zip \
  ../banana-skill-vX.Y.Z.zip \
  --title "vX.Y.Z" \
  --notes "See CHANGELOG.md for details"
```

## Plugin development notes

- `.claude-plugin/` contains ONLY `plugin.json` and `marketplace.json`. Never put skills, agents, or commands in this directory.
- `skills/` and `agents/` must be at plugin root (not inside `.claude-plugin/`).
- Plugin variable `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin cache directory. Use for hook commands and MCP configs.
- SKILL.md uses `${CLAUDE_SKILL_DIR}` for script paths -- this is a semantic marker Claude interprets based on context. Works in both plugin and standalone mode.
- Relative paths in SKILL.md (`references/`, `scripts/`) resolve relative to SKILL.md location. These work in both modes.
- Test locally with `claude --plugin-dir .` (loads plugin without installing).
- After changes, run `/reload-plugins` in Claude Code to pick up updates without restarting.
- Validate with `claude plugin validate .` or `/plugin validate .` before releasing.
