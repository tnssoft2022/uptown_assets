# Uptown Assets

Claude Code system that turns real estate listings (for sale or rent) into vertical 9:16 videos for Facebook
Reels, TikTok and YouTube Shorts (16:9 and 1:1 versions on request):
read the listing, plan the story, make the voice-over, cut the MP4. The user is Thai; the README is in Thai.

The `director` role (default) talks with the user and sends work to the agents in `.claude/agents/`:
`brief` (sorts assets, writes brief.md), `retouch` (photo fixes with ffmpeg; declutter, virtual staging,
sky and upscale with Magnific credits), `voice-kanya` (Thai voice-over with macOS `say`),
`editor-magnific` (upscales and AI motion clips, costs Magnific credits) and `editor` (HyperFrames build,
ffmpeg for the sound).

## Layout

```
brand/
  logo.png     Uptown Assets logo (transparent PNG). The editor puts it on every video: top-left on every
               shot and large on the end card, animated.
  logo_layers/ the logo cut by position into ring, mark (U), uptown, assets (scripts/split_logo.py); the
               animation moves these, never redraws them.
  logo_anim/   the logo sting (HyperFrames project) and SNIPPETS.md: the corner and end card blocks the
               editor pastes into every cut.
  logo_anim.mov  the sting rendered with alpha (900x900, ProRes 4444, 2.4 s) for other editors;
               logo_anim_preview.mp4 shows it on the wine colour.
  fonts/kanit/ Kanit (SIL OFL, OFL.txt), the heading font; Sarabun comes with macOS.
  icons/       Lucide line icons (ISC, LICENSE) and ICONS.md: which icon goes with which listing fact.
  motion_fx/   motion graphics (SNIPPETS.md, typography.css, motion_fx.js): type scale, price highlight,
               animated feature icons, parallax, the safe zone and the restraint rules; motion_fx_preview.mp4.
  text_fx/     text effects (text_fx.js helpers and SNIPPETS.md) the editor uses for every on-screen line and
               caption; each style's "ข้อความเคลื่อนไหว" row in STYLES.md picks them.
  transition_fx/ transitions (transition_fx.js helpers and SNIPPETS.md) the editor uses between shots; each
               style's "ทรานสิชัน" row in STYLES.md picks them.
  music/       one instrumental track per style (standard, calm, walk .mp3; card uses walk.mp3 for now), AI music from the
               user's paid Magnific account (Google Lyria 3 Pro). Used when a listing's assets/ has no music.
               Each has a <track>.beats.json beat grid (scripts/music_beats.py) so cuts land on the beat.
listings/
  <code>-<name>/
    assets/    originals: photos, clips, logo, music. Never modify or delete.
    listing.md listing text as the site shows it, source URLs, photo sources (from the fetch script)
    brief.md   written by the brief agent
    output/    finished videos, preview/ (the draft the user approves), qc/ (quality control report), build.sh, hyperframes/ (the cut's HTML
               project; hyperframes_16x9/, hyperframes_1x1/ when asked), voiceover.wav, voice/,
               magnific/, retouched/, analysis/ (photo analysis: measure.json, photos.json, plan.json,
               photo_analysis.jpg)
```

Everything in `listings/` is gitignored (only `listings/.gitignore` is tracked), so briefs and videos are
not in git. `session-role/` and `video-list/` are Claude Code plugins, not part of the video pipeline.

`scripts/fetch_uptownassets.py <url>` turns an uptownassets.com listing page (`/th/` or `/en/`, `project/...`
or `view/...`) into a listing folder: full-size photos in `assets/` (never overwrites one) and `listing.md`,
with the site's ✓/✗ checklists (furniture, amenities) kept as marks. Python 3.9,
standard library only. Listings from other sites are read by hand into the same layout.

`scripts/render_cut.py preview|final|check` renders a cut: a half-size draft preview with the real sound
(the user approves it), then the full render (HyperFrames, CRF 18) muxed with the mix, checked against the
delivery spec (MP4 H.264 High, yuv420p, 30 fps, 1080×1920 / 1920×1080 / 1080×1080, AAC 44.1 kHz, faststart).
The picture is HyperFrames (not Remotion); ffmpeg does the copies, mix, mux and checks.

`scripts/qc.py <listing-dir>` is the quality control before every preview and full render: Thai spelling
(the `SPELLING.md` list, market spellings for real estate words, and broken tone marks or vowels), every
number and ✗ item against listing.md, text over the subject or outside the safe zone (frames rendered
with and without text), where each photo's focus lands, and sound and timing. It writes
`output/qc/qc.md`, `qc.json`, `qc_sheet.jpg`; no ❌ may stay, and the director reads every text line itself.

`scripts/voiceover.py <script.json> <output-dir>` makes the Thai voice-over with Kanya (macOS `say`): spoken
spellings for numbers and abbreviations, each line fitted to its shot and levelled, `voiceover.wav` and
`voice/timing.json` with line and phrase times for the captions; other TTS engines plug into its `ENGINES`.
`scripts/mix_audio.py` mixes voice and music: music ducked 12–18 dB under the voice, the mix at −14 LUFS,
−1 dBTP. `brand/music/LICENSES.md` is the music licence register: no listed licence, no track.

`scripts/photo_analysis.py measure|sheet <listing-dir>` is the photo analysis the `brief` agent runs before
every treatment: `measure` measures each photo (size, sharpness, light, colour cast, near-duplicates);
`brief` then writes `output/analysis/photos.json` (room, 1–5 scores, focus point, camera move) and `sheet`
totals the scores, picks the Hero Shot, works out the 9:16 crops of each move, checks where the text can
sit and draws `output/analysis/photo_analysis.jpg`. Python 3.9 standard library plus ffmpeg.

## Tools

- `ffmpeg` and `ffprobe`
- Node.js and the HyperFrames skills in `~/.claude/skills/hyperframes/` (the editor renders the picture with
  them; the Thai text uses the Sarabun font that comes with macOS)
- macOS with the Kanya voice (Thai voice-over)
- A paid Magnific account connected to Claude (only for `editor-magnific` and the AI edits of `retouch`;
  the `brand/music/` tracks were made with it)

`COPY_STYLE.md` (Thai) is the copy style guide: tone, lengths, hook formulas, words to avoid and a checklist
for every hook, on-screen line, caption, voice-over line and end card. `brief` drafts by it; the director checks by it.

`STYLES.md` (Thai) holds the video style presets (มาตรฐาน, เรียบหรู, เดินชมห้อง, การ์ดข้อมูล): tone, length, shot pace,
transitions, text look, voice pace, music mood and staging look. The director asks the user to pick one
before the brief, in the app's question box (one click picks it); `brief`, `voice-kanya`, `editor` and `retouch` (staging) follow it.

## Rules every session follows

- **Facts only from the listing or the user.** Never invent prices, sizes or features, and don't claim a
  view, orientation or nearby station the listing doesn't state. Nearby stations and landmarks the listing
  does name go on a "nearby places" card before the end card, names and distances as the listing gives them.
  Project amenities the listing marks ✓ go in the video too (amenity photos, then a "ส่วนกลาง" card). The
  site's amenity and furniture lists are checklists: only ✓ items exist, ✗ items don't, and a list copied
  without its marks proves nothing.
- **Cosmetic retouching is allowed, with no label on screen:** colour and light fixes, removing movable
  clutter and personal items, virtual staging of empty rooms, a clearer sky, and renders or show-unit images
  when the user approves them for that listing.
- **Never misrepresent the property itself:** don't hide defects (cracks, stains, leaks, damage), don't make
  rooms or land look bigger or change walls, windows and built-in fixtures, don't add a view, amenity or
  feature it doesn't have, and don't remove real things around it (power poles, wires, neighbouring
  buildings, roads). AI motion moves the camera only: nothing added, removed or warped.
- **On-screen text is Thai** unless the user asks for another language. Prices "5.5 ล้านบาท", areas
  "ตร.ม.", phone numbers 0XX-XXX-XXXX (not +66), "รหัสทรัพย์" for the reference code. Brand names and URLs
  stay as they are.
- **Fair housing:** describe the property and its amenities, never who should live there.
- **Rights:** use only music, footage and images the user has the rights to; flag anything unclear (e.g. a
  Google Maps screenshot) before using it.
- **Captions are always burned in**, since many people watch muted.
