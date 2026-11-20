# Uptown Assets

Claude Code system that turns real estate listings (for sale or rent) into vertical 9:16 TikTok videos:
read the listing, plan the story, make the voice-over, cut the MP4. The user is Thai; the README is in Thai.

The `director` role (default) talks with the user and sends work to the agents in `.claude/agents/`:
`brief` (sorts assets, writes brief.md), `retouch` (photo fixes with ffmpeg; declutter, virtual staging,
sky and upscale with Magnific credits), `voice-kanya` (Thai voice-over with macOS `say`),
`editor-magnific` (upscales and AI motion clips, costs Magnific credits) and `editor` (ffmpeg build).

## Layout

```
listings/
  <code>-<name>/
    assets/    originals: photos, clips, logo, music. Never modify or delete.
    brief.md   written by the brief agent
    output/    finished videos, build.sh, voiceover.wav, voice/, magnific/, retouched/
```

Everything in `listings/` is gitignored (only `listings/.gitignore` is tracked), so briefs and videos are
not in git. `session-role/` is a Claude Code plugin, not part of the video pipeline.

## Tools

- `ffmpeg` and `ffprobe`
- macOS with the Kanya voice (Thai voice-over)
- A paid Magnific account connected to Claude (only for `editor-magnific` and the AI edits of `retouch`)

`COPY_STYLE.md` (Thai) is the copy style guide: tone, lengths, hook formulas, words to avoid and a checklist
for every hook, on-screen line, caption, voice-over line and end card. `brief` drafts by it; the director checks by it.

## Rules every session follows

- **Facts only from the listing or the user.** Never invent prices, sizes or features, and don't claim a
  view, orientation or nearby station the listing doesn't state.
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
