# video-list

A Claude Code mod for Uptown Assets. It puts a **🎬 วีดีโอทั้งหมด** button above the chat box, at the end of the session-role line (on a line of its own without session-role).
Pressing it scans `listings/*/output/` for finished videos (`.mp4`, `.mov`, `.m4v`), writes
`listings/videos.html` (gitignored with the rest of `listings/`), serves `listings/` on localhost with
`server.py` (Range support, so videos can seek) and opens the page in the Claude app's built-in browser
pane beside the chat. Where that pane can't be reached it opens the default browser instead.
The page groups the videos by listing or, with the ตามวันที่ switch, by the day they were made
(newest first; the page remembers the choice), and names each video by its property (the first
`# ` heading of the listing's `listing.md`, the folder name without one) with the รหัสทรัพย์ from the
folder name, and tags it with the property type and sale or rent (the `- ประเภททรัพย์:` and
`- ประเภทประกาศ:` lines of listing.md; no tag without them or when they say `ถามผู้ใช้`). Buttons filter
the videos by property type. It shows each one's length (ffprobe), size and date, plays it right there, has
a download button (saved under the property name) and a search box that matches the property name, type,
sale or rent, code and file name. Press the button again to refresh the page. `/videos` does the same.

A second button, **📋 เปิด/ปิดขั้นตอน**, sits after it and opens or closes a pane beside the chat with
the work steps of this session's listing only: the `listings/<listing>/output/progress.md` table this
session last wrote or read (another session's listing never shows here; before this session touches a
progress.md the pane says there is none yet)
(# | ขั้นตอน | สถานะ | ใช้เวลา), each step coloured by its status (✅ green, ⏳ yellow, ⏸ magenta),
with the property name and how many steps are done. A step in progress (⏳) or waiting on you (⏸)
shows a live ⏱ timer, counting once a second from when the table was first written with it so, and the
header shows the total time so far (the done steps' ใช้เวลา plus the running timers). The pane redraws as the director updates the table
(after each file write and at the end of every turn). It opens by itself the first time this session
writes or reads a listing's progress.md (when the work starts); after that it stays as you leave it.
`/steps` does the same as the button.

Needs `python3` for the page server, `ffprobe` on the PATH for the lengths, and macOS (`open`) for the fallback.
