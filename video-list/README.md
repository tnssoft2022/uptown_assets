# video-list

A Claude Code mod for Uptown Assets. It puts a **🎬 วีดีโอทั้งหมด** button above the chat box, at the end of the session-role line (on a line of its own without session-role).
Pressing it scans `listings/*/output/` for finished videos (`.mp4`, `.mov`, `.m4v`), writes
`listings/videos.html` (gitignored with the rest of `listings/`), serves `listings/` on localhost with
`server.py` (Range support, so videos can seek) and opens the page in the Claude app's built-in browser
pane beside the chat. Where that pane can't be reached it opens the default browser instead.
The page groups the videos by listing, newest first, shows each one's length (ffprobe), size and date,
and plays it right there. Press the button again to refresh the page. `/videos` does the same.

Needs `python3` for the page server, `ffprobe` on the PATH for the lengths, and macOS (`open`) for the fallback.
