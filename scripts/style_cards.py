#!/usr/bin/env python3
"""Print the style picker for the chat: one card per style in STYLES.md.

Each card shows the style's sample room (brand/styles/<file>.jpg, not the listing's photos) in 9:16, with
no text on the image, and under it the style name and length. The images load from jsDelivr, which serves
the public GitHub repo's main branch, so a new or changed image shows only after it is pushed (a changed
image under the same name can stay cached for about 12 hours: give it a new name instead). The output has
no embedded image data, so pass it to show_widget as it is. The director passes the HTML to show_widget;
the user's pick comes back as a chat message ("สไตล์: ฉับไว").

    python3 scripts/style_cards.py [--recommend <style>] > cards.html

Python 3.9, standard library only. Keep STYLES below in step with STYLES.md.
"""
import argparse
import html
import sys
from pathlib import Path

# name, sample image in brand/styles/, one-line summary
STYLES = [
    ("มาตรฐาน", "standard", "20–30 วิ · เป็นกันเอง"),
    ("เรียบหรู", "calm", "30–40 วิ · ช้า สงบ"),
    ("ฉับไว", "fast-2", "15–20 วิ · ตัดเร็ว"),
    ("เน้นข้อมูล", "data", "30–45 วิ · ตัวเลขนำ"),
]

HEADER_ICON = (
    '<svg viewBox="0 0 20 20" fill="currentColor"><path d="M11.586 2a1.5 1.5 0 0 1 1.06.44l2.914 2.914a1.5 1.5 '
    '0 0 1 .44 1.06V16.5a1.5 1.5 0 0 1-1.5 1.5h-9a1.5 1.5 0 0 1-1.492-1.347L4 16.5v-13A1.5 1.5 0 0 1 5.5 2zM5.5 '
    '3a.5.5 0 0 0-.5.5v13a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V7h-2.5A1.5 1.5 0 0 1 11 5.5V3zm7.04 10.304a.5.5 0 0 '
    '1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713.574-1.2.574-.486 '
    '0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067a.5.5 0 0 1 '
    '.886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527.696.74.696s'
    '.519-.18.74-.696m0-4a.5.5 0 0 1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713'
    '.574-1.2.574-.486 0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067'
    'a.5.5 0 0 1 .886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527'
    '.696.74.696s.519-.18.74-.696M12 5.5a.5.5 0 0 0 .5.5h2.293L12 3.207z"/></svg>'
)


IMAGES = Path(__file__).resolve().parent.parent / "brand" / "styles"
CDN = "https://cdn.jsdelivr.net/gh/tnssoft2022/uptown_assets@main/brand/styles"


def card(name: str, image: str, summary: str, recommended: bool) -> str:
    badge = ('<span style="font-size:11px;color:var(--text-accent);background:var(--bg-accent);'
             'padding:1px 8px;border-radius:var(--radius)">แนะนำ</span>') if recommended else ""
    return (
        f'<button type="button" class="elicit-pill" data-value="{html.escape(name)}" '
        'style="width:148px;border-radius:12px;padding:10px;display:flex;flex-direction:column;'
        'align-items:center;gap:6px;box-shadow:0 1px 2px rgba(0,0,0,0.04)">'
        f'<img src="{image}" alt="ห้องตัวอย่างสไตล์{html.escape(name)}" width="126" height="224" '
        'style="display:block;border-radius:8px;object-fit:cover">'
        f'<span style="font-size:13px;font-weight:500">{html.escape(name)}</span>'
        f'<span style="font-size:11px;color:var(--text-muted)">{html.escape(summary)}</span>{badge}</button>'
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--recommend", choices=[s[0] for s in STYLES])
    a = ap.parse_args()
    missing = [f for _, f, _ in STYLES if not (IMAGES / f"{f}.jpg").is_file()]
    if missing:
        print(f"missing sample images in {IMAGES}: {', '.join(missing)}", file=sys.stderr)
        return 1
    cards = "".join(card(n, f"{CDN}/{f}.jpg", s, n == a.recommend)
                    for n, f, s in STYLES)
    print(
        '<h2 class="sr-only">เลือกสไตล์วิดีโอ 4 แบบ แต่ละแบบมีรูปห้องตัวอย่าง</h2>'
        f'<form class="elicit"><div class="elicit-header">{HEADER_ICON}<span>สไตล์วิดีโอ</span></div>'
        '<div class="elicit-body"><div class="elicit-group">'
        '<label class="elicit-question">วิดีโอนี้ใช้สไตล์ไหนดี?</label>'
        f'<div class="elicit-pills" data-name="สไตล์" data-multi="false">{cards}</div></div>'
        '<div class="elicit-group"><label class="elicit-question">อยากปรับอะไรเพิ่มไหม?</label>'
        '<textarea class="elicit-textarea" data-name="ปรับเพิ่ม"></textarea></div></div>'
        '<div class="elicit-footer"><button type="button" class="elicit-skip">เลือกให้เลย</button>'
        '<button type="button" class="elicit-submit">ใช้สไตล์นี้</button></div></form>'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
