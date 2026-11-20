# Uptown Assets

Claude Code system that turns real estate listings (for sale or rent) into vertical 9:16 TikTok videos:
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
               shot and large on the end card.
  styles/      one sample room per style (standard, calm, walk .jpg) for the style picker cards only.
  music/       one instrumental track per style (standard, calm, walk .mp3), AI music from the
               user's paid Magnific account (Google Lyria 3 Pro). Used when a listing's assets/ has no music.
listings/
  <code>-<name>/
    assets/    originals: photos, clips, logo, music. Never modify or delete.
    listing.md listing text as the site shows it, source URLs, photo sources (from the fetch script)
    brief.md   written by the brief agent
    output/    finished videos, build.sh, hyperframes/ (the cut's HTML project), voiceover.wav, voice/,
               magnific/, retouched/
```

Everything in `listings/` is gitignored (only `listings/.gitignore` is tracked), so briefs and videos are
not in git. `session-role/` and `video-list/` are Claude Code plugins, not part of the video pipeline.

`scripts/fetch_uptownassets.py <url>` turns an uptownassets.com listing page (`/th/` or `/en/`, `project/...`
or `view/...`) into a listing folder: full-size photos in `assets/` (never overwrites one) and `listing.md`,
with the site's ✓/✗ checklists (furniture, amenities) kept as marks. Python 3.9,
standard library only. Listings from other sites are read by hand into the same layout.

## Tools

- `ffmpeg` and `ffprobe`
- Node.js and the HyperFrames skills in `~/.claude/skills/hyperframes/` (the editor renders the picture with
  them; the Thai text uses the Sarabun font that comes with macOS)
- macOS with the Kanya voice (Thai voice-over)
- A paid Magnific account connected to Claude (only for `editor-magnific` and the AI edits of `retouch`)

`COPY_STYLE.md` (Thai) is the copy style guide: tone, lengths, hook formulas, words to avoid and a checklist
for every hook, on-screen line, caption, voice-over line and end card. `brief` drafts by it; the director checks by it.

`STYLES.md` (Thai) holds the video style presets (มาตรฐาน, เรียบหรู, เดินชมห้อง): tone, length, shot pace,
transitions, text look, voice pace, music mood and staging look. The director asks the user to pick one
before the brief, with picker cards from `scripts/style_cards.py` (one 9:16 sample room per style from
`brand/styles/`, AI images for the picker only, never in a video); `brief`, `voice-kanya`, `editor` and `retouch` (staging) follow it.

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
