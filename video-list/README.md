# video-list

A Claude Code mod for Uptown Assets. It puts a **🎬 วีดีโอทั้งหมด (N)** button above the chat box, on the session-role line right after its ↻ (on a line of its own without session-role).
Pressing it opens a side pane that lists every finished video under `listings/*/output/`
(`.mp4`, `.mov`, `.m4v`), grouped by listing, newest first, with length (ffprobe), size and date.
Each video has **เปิด** (opens it in the default player) and **Finder** (shows it in Finder).
The list refreshes at the end of every turn and with **↻ โหลดใหม่**. `/videos` opens the pane too.

Needs macOS (`open`) and `ffprobe` on the PATH for the lengths.
