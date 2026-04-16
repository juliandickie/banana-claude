# Nano Banana Studio: Expansion Roadmap

## Context

Nano Banana Studio v3.6.3 is a comprehensive Creative Director plugin for AI image and video generation. This roadmap captures planned features, organized by implementation priority.

**Architecture:** Two interlinked skills sharing brand presets and asset registry:
1. **Image Skill** (`/banana`) — 24 commands: generation, editing, social media, slides, brand guides, assets, analytics, content pipeline
2. **Video Skill** (`/video`) — 10 commands: VEO 3.1 generation, image-to-video, multi-shot sequences with storyboard approval, clip extension, FFmpeg toolkit

---

## Completed Features

| # | Feature | Version | Notes |
|---|---------|---------|-------|
| 1 | `/banana slides` — batch slide deck pipeline | v1.6.0 | plan → prompts → generate workflow |
| 2 | `/banana brand` — conversational brand guide builder | v1.7.0 | learn → extract → refine → preview → save |
| 3 | Pre-built brand guide library (12 presets) | v1.7.0 | tech-saas, luxury-dark, organic-natural, etc. |
| 4 | `/banana social` — platform-native generation | v1.7.0 | 46 platforms, ratio grouping, 4K + auto-crop |
| 5 | `/banana asset` — persistent asset registry | v1.8.0 | characters, products, equipment, environments |
| 6 | `/banana reverse` — image-to-prompt reverse engineering | v1.9.0 | Claude vs Gemini perspectives + blended prompt |
| 7 | `/banana book` — visual brand book generator | v2.0.0 | markdown + pptx + html, 3 tiers, Pantone colors |
| 8 | `/banana formats` — multi-format image converter | v2.2.0 | PNG/WebP/JPEG at 4K/2K/1K/512, sips fallback |
| 9 | `/banana history` — session generation history | v2.3.0 | log, list, export as markdown gallery |
| 10 | `/banana ab-test` — A/B prompt variation testing | v2.4.0 | Literal/Creative/Premium + preference learning |
| 11 | `/banana deck` — slide deck builder | v2.5.0 | .pptx with 3 layouts, brand styling, logo placement |
| 12 | `/banana analytics` — analytics dashboard | v2.6.0 | HTML with SVG charts, cost/usage/quota |
| 13 | `/banana content` — multi-modal content pipeline | v2.7.0 | hero + social + email + formats orchestration |
| 14 | `/video` — VEO 3.1 video generation (core) | v3.0.0 | Text-to-video, image-to-video, first/last frame |
| 15 | `/video sequence` — multi-shot production | v3.3.0 | Storyboard approval, first/last frame chaining |
| 16 | `/video extend` + `/video stitch` — extension + FFmpeg toolkit | v3.4.0 | Clip chaining to 148s, concat/trim/convert |
| 17 | VEO 3.1 model variants + draft workflow + pricing fixes | v3.5.0 | Lite/Fast/Standard tiers, `--quality-tier` flag, model routing |
| 18 | Vertex AI backend (API-key auth) — unblocks Lite, image-to-video, Scene Ext v2, GA `-001` IDs | v3.6.0 | `_vertex_backend.py` helper, `--backend auto`, service agent retry |
| 19 | First+last frame interpolation + reference images on Vertex | v3.6.1 | `lastFrame` / `referenceImages` wired into `build_vertex_request_body` |
| 20 | Sequence production polish — review subcommand, `use_veo_interpolation`, partial storyboard regen, `~/Documents/nano-banana-sequences/` default | v3.6.2 | Review-sheet markdown generator, `--shots 1,3-5`, per-project output dirs |
| 21 | Review gate enforcement + smarter plans | v3.6.3 | Plan-hash tracking (SHA-256), mandatory review gate with `--skip-review` bypass, 8-type shot-type defaults, `--reference-image` on banana `generate.py`, 1080p Lite pricing verified |

---

## Planned Features

### v3.5.0 — VEO 3.1 Model Variants & Draft Workflow (SHIPPED 2026-04-10)

v3.5.0 shipped the VEO 3.1 model variant work (Standard / Fast / Lite /
Legacy 3.0), corrected pricing, the `--quality-tier` draft-then-final
workflow for sequences, Scene Extension v2 as the default extension
method, token-limit prompt validation, and a full rewrite of
`veo-models.md`. See `CHANGELOG.md` for the full list.

The "Sequence Production Improvements" items below (review gate, plan
hash tracking, audio strategy split, etc.) originally slated for v3.5.0
are **deferred to v3.6.0** — the coffee shop demo surfaced the model
variant gap as a higher-priority blocker, so that work landed first.

### v3.6.0 — Vertex AI Backend (SHIPPED 2026-04-11)

v3.6.0 shipped the Vertex AI backend that v3.5.0's reality check
revealed was needed. The auth approach turned out to be much simpler
than the original plan anticipated: bound-to-service-account API keys
(the `AQ.*` format from Vertex Express Mode signup) work for
`predictLongRunning` even though Google's Express Mode docs only list
3 methods. No OAuth, no service account JSON, no `gcloud` install.

**What shipped:**

- `_vertex_backend.py` helper module (~650 lines, stdlib only) with
  request body builder, URL composer, response parser, and a
  `--diagnose` CLI for free auth verification.
- `--backend {auto,gemini-api,vertex-ai}` flag on `video_generate.py`
  with auto-routing rules: text-only on preview IDs → Gemini API
  (v3.4.x compat), Vertex-only models or any image/video input →
  Vertex AI.
- `vertex_api_key` / `vertex_project_id` / `vertex_location` in
  `~/.banana/config.json`.
- Service-agent provisioning auto-retry (90 s sleep + retry once on
  the transient cold-start error).
- Scene Extension v2 `durationSeconds=7` auto-override.
- `--quality-tier draft` re-pointed from Fast back to Lite (the
  original v3.5.0 promise — 8× cost reduction restored).
- `video_extend.py --method` default flipped back to `video`.
- 1:1 aspect ratio special-case removed (was wrong in v3.5.0 docs).
- Lite duration constraint corrected to {4, 6, 8} (was wrong as 5-60
  in v3.5.0 docs).
- Doc rewrites in `veo-models.md`, `video-sequences.md`, `SKILL.md`,
  `README.md`, `CHANGELOG.md`.

**Carry-over from v3.5.0 plan still deferred to v3.6.1:**

The v3.6.0 implementation focused on the backend unblock; the
sequence-production-improvements scope from the original v3.5.0 plan
(review gate, plan hash tracking, audio strategy split, etc.) is
still pending. These items are documented below as v3.6.1 priorities.

### v3.6.1 — Deferred Sequence Production Improvements

These learnings came from producing the first real 30-second multi-shot sequence (the coffee shop demo for the README). The theoretical pipeline shipped in v3.3.0 works, but these specific gaps surfaced during actual use. They were originally scoped to v3.5.0, deferred to v3.6.0 because the model variant unblock landed first, then deferred again to v3.6.1 because v3.6.0's scope was the Vertex AI backend:

#### Process & UX — Make the approval gate impossible to skip

- **`/video sequence review` subcommand** — Given a plan.json with populated prompts and a storyboard directory, generate a `REVIEW-SHEET.md` that interleaves each shot's frames inline with its VEO prompt, cost estimate, and parameters. This is the artifact I hand-wrote during the demo. The sequence skill should produce it automatically whenever the storyboard changes, so it's always fresh and always current.
- **Default output location should be visible from Finder** — The current `video_sequence.py` writes plans to `/tmp` by default, which is hidden on macOS. Change default to `~/Documents/nano-banana-sequences/<project-name>/` so users can review with Quick Look (`Space` key) out of the box. Keep `--output` flag for explicit overrides.
- **Review sheet should be the mandatory gate between `storyboard` and `generate`** — `video_sequence.py generate` should refuse to run if no `REVIEW-SHEET.md` exists for the current plan, or if the plan hash in the review sheet doesn't match the current plan.json hash (detects stale reviews). Override flag `--skip-review` for CI/automation use.
- **Rename the approval gate step explicitly** — Currently steps are `plan → storyboard → generate → stitch`. Rename to `plan → storyboard → review → generate → stitch`, making the human approval a first-class pipeline stage.

#### Plan freshness — Prevent prompt drift from frame updates

- **Plan hash tracking** — When storyboard frames are regenerated, the sequence script should detect that the frames changed and flag the corresponding prompts as potentially stale. One option: store a SHA-256 of each frame in the plan.json, compare on review-sheet generation, and emoji-flag any shot where the frame has changed since the prompt was last edited.
- **`/video sequence update-prompts` subcommand** — Given a plan with regenerated frames, suggest updated prompt wording that references the new frame details. This would use the image-to-text capability of Gemini to describe the current frame, then propose prompt edits that match.
- **Single source of truth** — During the demo, the plan.json said one thing ("overhead shot") while the actual frames showed another ("three-quarter high angle"). The review-sheet generation should actually *read* the frames and compare against prompt claims before presenting for approval.

#### Sequence architecture — Support "end frame optional" shots

- **Flag: `end_frame: null` explicitly means VEO interpolates** — Add a `use_veo_interpolation: true` field to shots in plan.json. When true, only the start frame is used, and the VEO call drops `--last-frame`. This was a real architectural need in Shot 1 of the coffee shop demo: cutting to an unrelated Shot 2 meant we didn't need to constrain where Shot 1 ended, freeing VEO to execute a dramatic push-in.
- **`video_sequence.py storyboard --shots 1,3` partial regeneration** — Add ability to regenerate frames for specific shots without rebuilding the whole storyboard. Critical for iteration when one frame has a bug but others are approved.
- **Store shot types explicitly: `establishing`, `medium`, `closeup`, `product`, `transition`, `cutaway`, `b-roll`** — This field exists in the plan.json schema but has no semantic effect. It should drive defaults like duration, camera style hints, and whether an end frame is recommended.

#### Image-to-image frame chaining — Make it first-class

- **Add `--reference-image` flag to `generate.py`** — Currently the only way to do reference-based generation is to use `edit.py`, which is misleadingly named. Add `--reference-image PATH` to `generate.py` that passes the image as an `inlineData` part alongside the text prompt. This is the same thing `edit.py` does under the hood, but using `generate.py` makes the intent clear: "generate a new image informed by this reference", not "edit this image".
- **Document the conservatism bias** — Image-to-image mode anchors heavily on source geometry and is excellent for continuity (same cup across shots) but bad for large camera moves (dolly from wide to close-up). The prompt engineering reference should document when to use text-only vs image-reference:
  - **Text-only generation** — Large camera moves, dramatic framing changes, establishing → close-up transitions within a shot
  - **Image-reference generation** — Character/object identity locks, cross-shot prop continuity, minor framing adjustments, style matching
- **Output resolution warning** — Image-reference mode returns half-resolution (~1376×768 from a 2K source). For VEO input this is acceptable (above 720p minimum), but the user should know. Add a note to the generate script's output JSON that says `{"source_resolution": "2K", "output_resolution": "1K-ish", "reason": "image-to-image downscaling"}` when applicable.

#### Audio strategy — Decide dialogue and narration up front

The sequence pipeline currently has a single free-text `audio` field per shot that mixes ambient sound, SFX, dialogue, and narration indiscriminately. In practice these are three architecturally different audio modes, and the decision must be made *before* shot prompts are written because it changes the visuals, timing, and duration:

- **Ambient + SFX (VEO generates natively)** — Background atmosphere and action-matched sound effects. VEO handles these well and they don't constrain the visual prompt. This is what the coffee shop demo uses.
- **On-camera dialogue (VEO generates with lip-sync)** — A character speaks visible lines during the shot. VEO supports this in English with strict constraints:
  - 8-second duration limit (dialogue clips can't be extended)
  - Lip-sync is reliable only for short phrases (3-8 words per clip)
  - The speaking character must be visible in the frame
  - The prompt must explicitly include the line in quotation marks
  - Changes the prompt structure: `A woman says, "Welcome to our cafe," as she places a latte on the counter.`
- **Voiceover narration (post-production overlay)** — Narrator speaks over the sequence without appearing on camera. VEO doesn't generate this; it's added in post. But it affects:
  - Total sequence duration (narration paces the cut lengths)
  - Shot pacing (each shot must be long enough for its share of narration)
  - Visual framing (shots can't introduce audio-distracting elements during narration)
  - Cost (no extra VEO cost, but needs text-to-speech or voice actor + audio editing)

**Implementation tasks for v3.5.0:**

- **Add a sequence-level `narration` field to plan.json** — `narration: null` (none), `narration: "text..."` (voiceover text to be added in post), or `narration: "sync"` (on-camera dialogue only, see per-shot `dialogue` field below).
- **Add a per-shot `dialogue` field to plan.json** — separate from the `audio` field. When present, it signals on-camera sync-sound dialogue and triggers VEO prompt construction that includes the line, timing cues, and lip-sync requirements.
- **Split the `audio` field into `ambient` and `sfx`** — two clean fields instead of one blob. VEO prompts should always include both.
- **`/video sequence plan` should ask about audio strategy up front** — before generating shot skeletons, the planning step should prompt Claude (via the SKILL.md instructions) to ask the user: "Does this sequence have voiceover narration? On-camera dialogue? Ambient only?" and record the answer in the plan. This single decision cascades into every shot's prompt.
- **`/video sequence narration` subcommand** — post-generation, given a finished stitched MP4 and a narration script, call a TTS service (or accept a prerecorded audio file) and mix it into the video using FFmpeg. This lets the same visual sequence be re-used with different narrations (English, French, Spanish) without regenerating any VEO clips. Huge cost saver for multi-language deliverables.
- **Audio strategy reference doc** — Write `references/video-audio.md` additions that cover the three modes, when to use which, VEO's dialogue limitations, and how to structure prompts for each case. Also document the hybrid case: VEO generates ambient + SFX during the shot, post-production adds voiceover on top.

#### Prompt engineering — Discoveries captured in video-prompt-engineering.md

The specific prompt engineering discoveries from this demo have been captured in `skills/video/references/video-prompt-engineering.md` under a new **"Discoveries and Tips from Real Sequence Production"** section. That file is the long-term home for learnings that accumulate over time as we run more sequences.

**Initial tips captured** (see the reference file for full details and examples):

1. Scene bible anchors locked across prompts — identical phrasing, not paraphrases ✅
2. Off-frame composition beats forcing all elements visible ✅
3. Explicit percentage framing for camera moves ✅
4. Image-to-image has conservatism bias ✅
5. ALL CAPS for anatomical and count constraints 🔬
6. Real camera brand names anchor color and grade ✅
7. Audio is three distinct things, not one ✅
8. Not every shot needs an end frame ✅
9. Hybrid storyboard generation (text-only for first frames, image-reference for continuations) ✅

**Evidence levels used in the reference file:**
- ✅ **Demonstrated** — observed in real generation output, bug or improvement reproducible
- 🔬 **Unverified** — reasonable guess from general knowledge or one-shot observation, not yet eval-tested
- 📊 **Measured** — backed by a formal eval run with multiple samples (none yet)

This honest framing means future developers know which tips to trust and which to test. When v3.5.0 implementation work starts, the 🔬 Unverified tips should be targeted for eval runs to promote them to 📊 Measured.

#### VEO API integration fixes already shipped in v3.4.1

These bugs were discovered during the first real VEO test and are documented here so future developers understand the pitfalls:

- ✅ `personGeneration: "allow_adult"` rejected for text-to-video — only omit it, or use `"allow_all"`
- ✅ Image format is `inlineData.data`, not `bytesBase64Encoded`
- ✅ Response path is `response.generateVideoResponse.generatedSamples[0].video.uri`, not `response.generatedSamples`
- ✅ Video URIs require the API key as a query parameter for authenticated download

#### New v3.6.0 items surfaced during v3.5.0 research

- **`--num-videos` flag (1–4 per API call)** — VEO 3.1 supports generating up to 4 variations in a single `predictLongRunning` request, amortizing the setup/denoise overhead. Adds a new output shape (array of paths). Overlaps with the banana skill's `/banana ab-test` — might belong there instead.
- **Object insertion support** — VEO 3.1 can add elements into generated video while maintaining consistent lighting and physics. New flag probably looks like `--insert-object <image.png> --insert-description "a coffee cup on the table"`.
- **Parallel batch execution in `video_sequence.py`** — Currently shots are generated sequentially. Up to 10 concurrent operations are allowed per project. Parallel execution would cut a 4-shot sequence wall-clock from ~4 min to ~1 min at the cost of losing the "fail fast on shot 1" pattern.
- **`output_gcs_uri` support** — Write directly to Cloud Storage instead of downloading and re-uploading. Required for workflows that need videos to outlive the 48-hour retention window without local storage.
- **Regional restrictions awareness** — Detect EEA/Swiss/UK locale and warn when image-to-video features will be restricted. Also surface the `personGeneration: allow_adult` default in those regions.
- **1080p Lite pricing verification** — The reference doc only explicitly states $0.05/sec for 720p Lite. 1080p Lite pricing is unverified. Run a real API call to confirm and update the PRICING dict.
- **Character consistency improvements** — VEO's character drift is a documented limitation. Consider routing character-heavy shots through Replicate backends (Kling 2.6, Seedance 2.0) which handle multi-shot consistency better.

#### Cost and workflow wins to preserve

These worked well and should be documented in the video-sequences reference so future users follow the same pattern:

- **Storyboard:video cost ratio is 15×** ($0.08 per frame vs ~$1.20 per clip) — this is the economic argument for the approval gate. A 30-second, 4-shot sequence costs $0.64 in storyboard and $4.50 in video. If one frame has a bug, the cost of a storyboard regeneration is 0.13% of the cost of regenerating the corresponding clip.
- **Sequential VEO testing over parallel** — fire one clip, inspect it, then decide whether to proceed. A bug found on clip 1 avoids burning 3× the cost on clips 2-4.
- **Hybrid generation mode for storyboard** — use text-only for the first frame of each shot (full control), then image-reference chaining for subsequent frames (consistency). Cross-shot continuity (e.g., the cup in shot 3 end → shot 4 start) uses image-reference.

---

## Future Considerations

- **Figma Plugin Bridge** — Export to Figma frames via API
- **CMS Integration** — Auto-upload to WordPress, Contentful, Sanity
- **E-Commerce Automation** — Connect to Shopify/WooCommerce for product shots
- **3D Object Generation** — When model support exists
- **Interactive Prototypes** — Generate clickable UI mockups
- **Team Collaboration** — Shared presets via git repo

---

## Priority Summary

| # | Feature | Effort | Impact | Status |
|---|---------|--------|--------|--------|
| 1 | v3.5.0 — VEO 3.1 model variants + draft workflow + pricing fixes | Medium | Very High | **Shipped 2026-04-10** |
| 2 | v3.6.0 — Vertex AI backend (unblocks Lite, image-to-video, Scene Ext v2, GA `-001` IDs) | Large | Very High | **Shipped 2026-04-11** |
| 3 | v3.6.1 — First+last frame interpolation + reference images on Vertex | Small | High | **Shipped 2026-04-11** |
| 4 | v3.6.2 — Sequence production polish (review subcommand, `use_veo_interpolation`, partial storyboard regen, new output default) | Medium | High | **Shipped 2026-04-11** |
| 5 | v3.6.3 — Review gate enforcement with plan hash tracking + shot-type defaults + `--reference-image` on banana + 1080p Lite verified | Medium | High | **Shipped 2026-04-11** |
| 6 | v3.7.1 — ElevenLabs audio replacement pipeline + custom voice design + strategic reset (12 empirical findings) | Large | Very High | **Shipped 2026-04-14** |
| 7 | v3.7.2 — Lyria 2 as new default music source after 5-way bake-off (Lyria > ElevenLabs > MusicGen > MiniMax > Stable Audio); script renamed elevenlabs_audio.py → audio_pipeline.py; F13 spec-vs-quality finding | Medium | High | **Shipped 2026-04-14** |
| 8 | v3.6.4 — `update-prompts` Gemini-vision subcommand (closes the prompt-drift loop from v3.6.3) | Medium | High | Deferred — superseded in priority by v3.7.x |
| 9 | v3.7.3 — Spike 6 (banned-keywords re-validation, $0.70 actual) + prompt-engineering.md refresh aligned to Google's official Gemini 3.1 docs; documents the "publication-format anchors render literal magazine covers" failure mode | Small | Medium | **Shipped 2026-04-15** |
| 9 | v3.7.4 — Audio polish bundle: real stereo mix, auto-measured per-voice WPM, ElevenLabs Instant Voice Cloning, multi-call Lyria with FFmpeg acrossfade for > 32.768s, shared client-side named-creator stripping across Lyria + Eleven Music | Medium | Medium | **Shipped 2026-04-15** |
| 9a | v3.7.5+ — Professional Voice Cloning (PVC) subcommand, Lyria long-music cost warning, strip-list extensibility via config file | Medium | Low | After v3.8.0 |
| 10 | v3.8.0 — **Kling v3 Std as default video model, VEO 3.1 as opt-in backup only** — informed by spike 5 (sessions 16). Shipped in session 17 (2026-04-15). See `CHANGELOG.md` [3.8.0] section. | Large | High | **✅ Shipped 2026-04-15** |
| 10a | v3.8.1 — **Seedance 2.0 retest with Phase 2 subjects** — completed 2026-04-15 in session 18. Result: 2 of 3 FAILED with E005 on both human subjects (woman in home office, woman athlete); only cartoon robot mascot succeeded. **Verdict: permanently rejected for human-subject workflows.** Not wired into the plugin. See `references/kling-models.md` "Seedance 2.0 retest outcome (v3.8.1)" section. Spend: $0.14 + $0.48 anchors. | Small | Medium | **✅ Shipped 2026-04-15** (verdict: rejected) |
| 10b | v3.8.1 — **Vertex smoke-test subcommand** — completed 2026-04-15 in session 18. Landed as `_vertex_backend.py smoke-test` subparser (not a separate script) for discoverability. Tests 3 free probes: preview ID → 404, invalid aspect ratio → 400, auth ping. The 2 remaining constraints (GA -001 reachability, duration) are documented as "requires budget" in the output rather than auto-tested. Also surfaced a real Vertex drift from spike 5 Phase 2 (duration now accepted at submit, validated asynchronously). | Small | Medium | **✅ Shipped 2026-04-15** |
| 10c | v3.8.1 — **Fabric 1.0 `/video lipsync` subcommand** — completed 2026-04-15 in session 18. New `video_lipsync.py` standalone runner + `lipsync.md` reference doc. Closes the v3.8.0 gap where custom ElevenLabs voices from `audio_pipeline.py narrate` couldn't reach visible character faces. Integrates Fabric 1.0 via existing `_replicate_backend.py` helpers — ~40 lines of new backend code. | Small | High | **✅ Shipped 2026-04-15** |
| 10d | v3.8.1 — **Replicate User-Agent hardening** — completed 2026-04-15 in session 18. Applied to both `replicate_generate.py` AND `replicate_edit.py`. Defensive fix against Cloudflare WAF error 1010 that could tighten on `/v1/models/.../predictions` endpoints. | Trivial | Low | **✅ Shipped 2026-04-15** |
| 11 | Backlog cherry-picks — `output_gcs_uri`, `--num-videos`, parallel batch execution, object insertion, regional restrictions awareness | Various | Low-Medium | Cherry-pick as needed |

### Deferred research spikes (will run before their target releases)

The strategic reset session included six planned empirical spikes. Spikes 1, 2, 3 (audio architecture) shipped in v3.7.1. Spike 4 (Lyria + 5-way music bake-off) shipped in v3.7.2. Spike 6 (banned-keywords re-validation) shipped in v3.7.3. **Spike 5 completed in session 16** (2026-04-15 evening) with two phases spanning $53 total spend — findings locked in v3.8.0 scope.

- ~~**Spike 5 — Character consistency bake-off**~~ **COMPLETED 2026-04-15 in session 16.** Two phases: (1) Phase 1 (initial 7-candidate bake-off) determined Kling v3 Std is the strongest candidate but kept VEO 3.1 Lite as default; (2) Phase 2 (15-shot-type head-to-head + tier comparison + extended 30s tests) REVERSED the Phase 1 default recommendation after user-verified playback revealed Kling wins 8 of 15 shot types while VEO wins 0. **User decision: Kling v3 Std becomes v3.8.0 default, VEO becomes opt-in backup only, VEO extended workflows disabled.** See `spikes/v3.8.0-provider-bakeoff/writeup/v3.8.0-bakeoff-findings.md` for the full findings doc. Implementation queued for Session 17 — see `spikes/v3.8.0-provider-bakeoff/NEXT_SESSION.md` and `spikes/v3.8.0-provider-bakeoff/IMPLEMENTATION_PLAN.md`.

### Pending spikes for v3.8.x (after v3.8.0 ships)

- **Seedance 2.0 retest** (~$2-3) — Phase 1 rejected Seedance on safety filter (E005 on bearded-man subject). User wants to retest with Phase 2's different subjects (woman in home office, athlete, fashion model, cartoon robot) to see if the filter behaves differently. Start with the 3 most diverse subject types (test_02 talking head, test_06 athlete, test_11 robot mascot) to confirm the filter isn't universally restrictive before committing to the full 15-test matrix. See the "Deferred to v3.8.x" section in `spikes/v3.8.0-provider-bakeoff/NEXT_SESSION.md` for the full retest plan.

### Future research backlog (post-v3.7.4)

Items that came up during sessions 12–15 but don't have committed target releases yet. Most of the v3.7.1/v3.7.2 polish debt from the earlier version of this list (multi-call Lyria, stereo mix, auto-WPM, IVC) shipped in v3.7.4 — this list is now forward-looking rather than known-issues.

**Audio research:**
- **Lyria-vs-ElevenLabs head-to-head genre bake-off**. v3.7.2's spike 4 tested both providers with a single "cinematic nature documentary" prompt where Lyria won decisively. The user noted that **different genres might surface different model strengths** and would be worth a dedicated test: electronic, classical, folk, ambient, jazz, hip-hop, etc. Each genre × each provider = ~12 test calls = ~$1-2 cost. Could ship as a v3.7.x research release that updates `audio-pipeline.md` with per-genre provider recommendations. Targets a v3.7.x research release.

**Audio polish still deferred:**
- **Professional Voice Cloning (PVC) subcommand** — separate endpoint family (`/v1/voices/pvc/*`), needs 30+ minutes of audio + Creator+ plan + multi-step fine-tuning workflow. Reserved under the existing `source_type: "cloned"` enum as a future `design_method: "pvc"`. Targets v3.7.5+.
- **Lyria long-music cost warning** — when `generate_music_lyria_extended()` would issue more than 5 calls (~$0.30), emit a pre-flight confirmation or require a `--confirm-extended-cost` flag. Tiny polish item.
- **Strip-list extensibility via config file** — `NAMED_CREATOR_TRIGGERS` is currently hardcoded. A future release could move it to `~/.banana/config.json` so users can add their own terms without editing the script.
- **"in the style of X" compound-phrase stripping** — when `strip_named_creators()` removes "Hans Zimmer" from "in the style of Hans Zimmer, warm strings", it leaves a dangling "in the style of , warm strings". The music providers ignore it, but a future pass could detect and strip the containing phrase as a unit.

**Orthogonal video capabilities surfaced in session 15 dev-docs additions:**

Two model cards added to `../dev-docs/` in session 15 solve jobs the plugin currently cannot do at all. They're NOT spike 5 bake-off candidates (which are general text-to-video alternatives to VEO) — they're new product surfaces. See the workspace `CLAUDE.md` "Specialised video capabilities" section for the full details.

- **`/video animate-character` via ByteDance DreamActor M2.0** — motion transfer from real filmed footage onto a generated avatar. Input: one character image + one driving video of a real person performing. Output: the character image animated with the driving video's motion. **Deferred to v3.9.x** — session 19 (2026-04-16) proved that Kling v3 Std's `start_image` + a character-matching prompt already handles the primary brand-consistency use case (generated characters doing scripted actions) natively at 2.5× lower cost and 1.5× higher resolution than DreamActor. DreamActor's remaining niche is narrower: real-footage-to-avatar workflows where a user films themselves and wants to map a generated avatar onto their performance. DreamActor smoke test results ($0.05/s, 694×1242 output, identity preserved) are documented in `kling-models.md` §Character Consistency.
- **`/video lipsync` via VEED Fabric 1.0** — audio-driven talking head. Input: one face image + one audio file (ANY audio — including an ElevenLabs TTS output from the v3.7.x audio pipeline). Output: the face lip-synced to the audio. This is structurally different from VEO's "person speaking" mode: VEO generates the speech internally and can't accept external audio, so there's no way to have a VEO character speak an ElevenLabs voice-designed narrator line. Fabric closes that loop. **Integration sketch:** `audio_pipeline.py narrate --voice brand_voice --text "..."` → Fabric with a banana-generated face → ship-ready talking-head reel. Targets a v3.8.x research release.

**v3.8.0 planning:**
- Primary spike is still **spike 5** (character consistency bake-off) above. Candidate pool expanded from 3 to 7 generic t2v models as of session 15. Recommended 2-phase approach: first $5-8 narrows to 2-3 finalists, second phase runs the controlled side-by-side.

Total deferred spike budget: ~$25-30 (spike 5 at $15-25, optional genre bake-off at $1-2, DreamActor + Fabric smoke tests at ~$1 each).
