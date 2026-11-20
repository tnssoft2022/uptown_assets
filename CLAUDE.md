# Uptown Assets

Claude Code system that turns real estate listings (for sale or rent) into vertical 9:16 TikTok videos:
read the listing, plan the story, make the voice-over, cut the MP4. The user is Thai; the README is in Thai.

The `director` role (default) talks with the user and sends work to the agents in `.claude/agents/`:
`brief` (sorts assets, writes brief.md), `voice-kanya` (Thai voice-over with macOS `say`),
`editor-magnific` (upscales and AI motion clips, costs Magnific credits) and `editor` (ffmpeg build).

## Layout

```
listings/
  <code>-<name>/
    assets/    originals: photos, clips, logo, music. Never modify or delete.
    brief.md   written by the brief agent
    output/    finished videos, build.sh, voiceover.wav, voice/, magnific/
```

Everything in `listings/` is gitignored (only `listings/.gitignore` is tracked), so briefs and videos are
not in git. `session-role/` and `usage-band/` are Claude Code plugins, not part of the video pipeline.

## Tools

- `ffmpeg` and `ffprobe`
- macOS with the Kanya voice (Thai voice-over)
- A paid Magnific account connected to Claude (only for `editor-magnific`)

## Rules every session follows

- **Facts only from the listing or the user.** Never invent prices, sizes or features, and don't claim a
  view, orientation or nearby station the listing doesn't state.
- **Don't misrepresent the property.** No renders or show units in place of the real rooms, and no edits
  or AI motion that add, remove or warp anything.
- **On-screen text is Thai** unless the user asks for another language. Prices "5.5 ล้านบาท", areas
  "ตร.ม.", phone numbers 0XX-XXX-XXXX (not +66), "รหัสทรัพย์" for the reference code. Brand names and URLs
  stay as they are.
- **Fair housing:** describe the property and its amenities, never who should live there.
- **Rights:** use only music, footage and images the user has the rights to; flag anything unclear (e.g. a
  Google Maps screenshot) before using it.
- **Captions are always burned in**, since many people watch muted.
