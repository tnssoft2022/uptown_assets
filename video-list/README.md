# video-list

A Claude Code mod for Uptown Assets. It puts a **🎬 วีดีโอทั้งหมด** button above the chat box, at the end of the session-role line (on a line of its own without session-role).
Pressing it scans `listings/*/output/` for finished videos (`.mp4`, `.mov`, `.m4v`), writes
`listings/videos.html` (gitignored with the rest of `listings/`), serves `listings/` on localhost with
`server.py` (Range support, so videos can seek) and opens the page in the Claude app's built-in browser
pane beside the chat. Where that pane can't be reached it opens the default browser instead.
The page groups the videos by listing or, with the ตามวันที่ switch, by the day they were made
(newest first; the page remembers the choice), and names each video by its property (the first
`# ` heading of the listing's `listing.md`, the folder name without one) with the รหัสทรัพย์ from the
folder name. It shows each one's length (ffprobe), size and date, plays it right there, has a download
button (saved under the property name) and a search box that matches the property name, code and file name. Press the button again to refresh the page. `/videos` does the same.

Needs `python3` for the page server, `ffprobe` on the PATH for the lengths, and macOS (`open`) for the fallback.
