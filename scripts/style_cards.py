#!/usr/bin/env python3
"""Print the style picker for the chat: one card per style in STYLES.md.

Each card shows the style's sample room (brand/styles/<file>.jpg, not the listing's photos) in 9:16, with
no text on the image, and under it the style name and a
short description (no length). The cards only show the styles: they have no buttons, because a widget
button only fills the chat box and the user then has to press Enter. The director asks for the pick right
after with AskUserQuestion, which answers in one click. The images load from jsDelivr, which serves
the public GitHub repo's main branch, so a new or changed image shows only after it is pushed (a changed
image under the same name can stay cached for about 12 hours: give it a new name instead). The output has
no embedded image data, so pass it to show_widget as it is.

    python3 scripts/style_cards.py [--recommend <style>] > cards.html

Python 3.9, standard library only. Keep STYLES below in step with STYLES.md.
"""
import argparse
import html
import sys
from pathlib import Path

# name, sample image in brand/styles/, one-line summary
STYLES = [
    ("มาตรฐาน", "standard", "เป็นกันเอง"),
    ("เรียบหรู", "calm", "ช้า สงบ"),
    ("เดินชมห้อง", "walk", "คลิปเดินชม"),
    ("การ์ดข้อมูล", "card", "รูปในกรอบ ข้อมูลเป็นหมวด"),
]

IMAGES = Path(__file__).resolve().parent.parent / "brand" / "styles"
CDN = "https://cdn.jsdelivr.net/gh/tnssoft2022/uptown_assets@main/brand/styles"


def card(name: str, image: str, summary: str, recommended: bool) -> str:
    badge = ('<span style="font-size:11px;color:var(--text-accent);background:var(--bg-accent);'
             'padding:1px 8px;border-radius:var(--radius)">แนะนำ</span>') if recommended else ""
    border = "var(--border-accent)" if recommended else "var(--border)"
    return (
        f'<div style="width:148px;border:0.5px solid {border};border-radius:12px;padding:10px;display:flex;'
        'flex-direction:column;align-items:center;gap:6px;box-sizing:border-box">'
        f'<img src="{image}" alt="ห้องตัวอย่างสไตล์{html.escape(name)}" width="126" height="224" '
        'style="display:block;border-radius:8px;object-fit:cover">'
        f'<span style="font-size:13px;font-weight:500">{html.escape(name)}</span>'
        f'<span style="font-size:11px;color:var(--text-muted);text-align:center">{html.escape(summary)}</span>'
        f'{badge}</div>'
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
        f'<h2 class="sr-only">สไตล์วิดีโอ {len(STYLES)} แบบ แต่ละแบบมีรูปห้องตัวอย่าง</h2>'
        f'<div style="display:flex;flex-wrap:wrap;gap:12px;padding:0.5rem 0">{cards}</div>'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
