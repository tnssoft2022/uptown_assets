#!/usr/bin/env python3
"""Fetch one uptownassets.com project page into listings/.

    python3 scripts/fetch_uptownassets.py <project-or-view-url> [--name <folder-name>]

- reads the Thai and English pages (any of /th/ or /en/ in the URL works)
- saves the full-size photos to listings/<code>-<name>/assets/photo-NN.<ext>
  (the page only links thumbnails; the full size is the same path without "thumbnails/")
- writes listings/<code>-<name>/listing.md: the listing text as the site shows it, the source
  URLs, the date fetched, the property type and sale/rent as the listing states them
  ("ถามผู้ใช้" when it doesn't), the contact on the page, the ✓/✗ checklists (in-unit furniture and
  appliances, project amenities) and which photo came from which URL

Reuses an existing listings/<code>-*/ folder. Never overwrites a file in assets/: a photo that
is already there is skipped, and one that differs from the site is reported, not replaced.
listing.md is rewritten on every run. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "listings"
URL_RE = re.compile(r"^https?://(?:www\.)?uptownassets\.com/(?:th|en)/(project|view)/(\d+)-([^/?#]+)")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X) uptown-assets-video-tool"


def get(url: str) -> bytes:
    # /view/ URLs carry the Thai name; urllib needs it percent-encoded (already-encoded parts stay).
    url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


HAS, HAS_NOT = "✓", "✗"


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</p\s*>", "\n", fragment, flags=re.I)
    # The amenities list ("สิ่งอำนวยความสะดวก") is a checklist of every amenity the site knows, each
    # with a check or a cross icon. Keep the icon as a mark, or the list would claim them all.
    fragment = re.sub(r'<i[^>]*class="[^"]*\bfa-check\b[^"]*"[^>]*>', f"\n{HAS}\n", fragment)
    fragment = re.sub(r'<i[^>]*class="[^"]*\bfa-times\b[^"]*"[^>]*>', f"\n{HAS_NOT}\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ")
    lines = []
    for l in (re.sub(r"[ \t]+", " ", l).strip() for l in t.splitlines()):
        if l in (HAS, HAS_NOT) and lines:
            lines[-1] += f" {l}"  # the mark belongs to the amenity on the line before
        elif l:
            lines.append(l)
    return "\n".join(lines)


def checklists_of(details: str) -> dict[str, tuple[list[str], list[str]]]:
    """Each checklist on the page (e.g. "เฟอร์นิเจอร์" in the unit, "สิ่งอำนวยความสะดวก" of the project),
    by its heading: the items marked ✓ (there) and ✗ (not there)."""
    lists: dict[str, tuple[list[str], list[str]]] = {}
    heading = ""
    for l in details.splitlines():
        mark = l[-1:] if l.endswith((f" {HAS}", f" {HAS_NOT}")) else ""
        if not mark:
            heading = l
            continue
        has, has_not = lists.setdefault(heading, ([], []))
        (has if mark == HAS else has_not).append(l[:-2])
    return lists


def parse(page: str) -> dict:
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    name = re.search(r'class="text text-highlight".*?<span[^>]*>(.*?)</span>', page, re.S)
    details = re.search(r'class="scrollable-details"[^>]*>(.*?)</section>', page, re.S)
    gallery = re.search(r'id="project-image-gallery".*?(?=id="project-nav-gallery")', page, re.S)
    phone = re.search(r'href="tel:(\d+)"', page)
    email = re.search(r'href="mailto:([^"]+)"', page)
    photos = re.findall(r'<img[^>]+src="([^"]+)"', gallery.group(0)) if gallery else []
    return {
        "title": text_of(title.group(1)) if title else "",
        "name": text_of(name.group(1)) if name else "",
        "details": text_of(details.group(1)) if details else "",
        "photos": list(dict.fromkeys(photos)),
        "phone": phone.group(1) if phone else "",
        "email": email.group(1) if email else "",
    }


# Property types the listing text can name, in the words the video list shows. Building
# types are checked before land: a house listing often states its land area as "ที่ดิน".
KINDS = [
    ("ทาวน์โฮม", r"ทาวน์โฮม|ทาวน์เฮ้?าส์|town ?(?:home|house)"),
    ("บ้านแฝด", r"บ้านแฝด|semi-detached"),
    ("บ้านเดี่ยว", r"บ้านเดี่ยว|(?<!semi-)detached house"),
    ("คอนโด", r"คอนโด|condo"),
    ("อาคารพาณิชย์", r"อาคารพาณิชย์|ตึกแถว|shophouse|commercial building"),
]
LAND = r"ที่ดิน|\bland\b"
ASK = "ถามผู้ใช้"


def kind_of(text: str) -> str:
    """The property type the listing names; ASK when it names none or more than one."""
    found = [kind for kind, pattern in KINDS if re.search(pattern, text, re.I)]
    if len(found) == 1:
        return found[0]
    if not found and re.search(LAND, text, re.I):
        return "ที่ดิน"
    return ASK


def deal_of(text: str) -> str:
    """ขาย or เช่า from the listing text; ASK when it says neither or both."""
    sale = re.search(r"(?<!ฝ่าย)ขาย|for sale", text, re.I)
    rent = re.search(r"เช่า|for rent", text, re.I)
    if sale and not rent:
        return "ขาย"
    if rent and not sale:
        return "เช่า"
    return ASK


def thai_phone(digits: str) -> str:
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    return digits


def folder_for(code: str, slug: str, name: str | None) -> Path:
    existing = sorted(p for p in LISTINGS.glob(f"{code}-*") if p.is_dir())
    if name:
        return LISTINGS / (name if name.startswith(f"{code}-") else f"{code}-{name}")
    if existing:
        return existing[0]
    short = slug[:40].rsplit("-", 1)[0] if len(slug) > 40 else slug
    return LISTINGS / f"{code}-{short}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--name", help="folder name after the code, e.g. ladprao64-house-131")
    args = ap.parse_args()

    m = URL_RE.match(args.url)
    if not m:
        print("Not an uptownassets.com listing URL (…/th|en/project|view/<code>-<slug>)", file=sys.stderr)
        return 2
    kind, code, slug = m.group(1), m.group(2), m.group(3)
    urls = {lang: re.sub(r"/(?:th|en)/(project|view)/", f"/{lang}/{kind}/", args.url, count=1) for lang in ("th", "en")}

    pages = {}
    for lang, url in urls.items():
        try:
            pages[lang] = parse(get(url).decode("utf-8", "replace"))
        except Exception as e:  # keep going with the other language
            print(f"warning: could not read {lang} page: {e}", file=sys.stderr)
    if not pages:
        print("Could not read the listing page.", file=sys.stderr)
        return 1
    if not any(p["details"] for p in pages.values()):
        print("warning: no listing details found on the page (layout changed, or a building page "
              "without its own listing text)", file=sys.stderr)

    folder = folder_for(code, slug, args.name)
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (folder / "output").mkdir(exist_ok=True)

    thumbs = next((p["photos"] for p in pages.values() if p["photos"]), [])
    photo_rows, problems = [], []
    for i, thumb in enumerate(thumbs, 1):
        full = thumb.replace("/thumbnails/", "/", 1)
        try:
            data, used = get(full), full
        except Exception:
            data, used = get(thumb), thumb
            problems.append(f"photo {i}: full size not found, saved the thumbnail")
        ext = Path(used.split("?")[0]).suffix.lower() or ".jpg"
        dest = assets / f"photo-{i:02d}{ext}"
        if dest.exists():
            note = "already there" if dest.read_bytes() == data else "already there, DIFFERS from the site (kept the local file)"
            if "DIFFERS" in note:
                problems.append(f"{dest.name}: differs from the site, not replaced")
        else:
            dest.write_bytes(data)
            note = "saved"
        photo_rows.append((dest.name, used, note))

    th, en = pages.get("th", {}), pages.get("en", {})
    phone = th.get("phone") or en.get("phone")
    email = th.get("email") or en.get("email")
    today = datetime.date.today().isoformat()
    # Only the name and details: page titles carry an SEO suffix, not facts.
    said = "\n".join(p.get(k, "") for p in (th, en) for k in ("name", "details"))
    checklists = checklists_of(th.get("details", ""))

    out = [f"# {th.get('name') or en.get('name') or slug}", ""]
    out += [f"- รหัสทรัพย์ (code in the URL): {code}",
            f"- ประเภททรัพย์: {kind_of(said)}",
            f"- ประเภทประกาศ: {deal_of(said)}",
            f"- Source (th): {urls['th']}",
            f"- Source (en): {urls['en']}",
            f"- Fetched: {today}",
            f"- Contact on the page: {thai_phone(phone) if phone else '-'}" + (f", {email}" if email else ""),
            "- Photos: from the Uptown Assets site (the company's own listing)"]
    # Checklists: only ✓ items are facts. ✗ items are things the property does NOT have.
    for heading, (has, has_not) in checklists.items():
        out += [f"- {heading or 'Checklist'} ✓ (has): {', '.join(has) or '-'}",
                f"- {heading or 'Checklist'} ✗ (does not have, never use): {', '.join(has_not) or '-'}"]
    out += [""]
    for lang, label in (("th", "Thai"), ("en", "English")):
        p = pages.get(lang)
        if not p:
            continue
        out += [f"## Listing text ({label}, verbatim)", "",
                f"Page title: {p['title']}", "",
                f"Name: {p['name']}", ""]
        out += ["```", p["details"] or "(no details on the page)", "```", ""]
    out += ["## Photos", "", "| File | Source | Status |", "|---|---|---|"]
    out += [f"| {n} | {u} | {s} |" for n, u, s in photo_rows] or ["| - | no photos on the page | - |"]
    out += ["", "Facts for the video come only from the listing text above or from the user. Every page "
            "title on this site ends in \"ราคาถูก ใกล้รถไฟฟ้า\": it is an SEO suffix, not a fact about this "
            "property, so don't use it. A condo building page describes the project, not a unit for "
            "sale or rent: ask the user for the unit's details.", ""]
    (folder / "listing.md").write_text("\n".join(out), encoding="utf-8")

    print(f"Folder:  {folder.relative_to(ROOT)}")
    print(f"Photos:  {len(photo_rows)} ({sum(1 for r in photo_rows if r[2] == 'saved')} new)")
    print(f"Listing: {(folder / 'listing.md').relative_to(ROOT)}")
    print(f"Type:    {kind_of(said)} · {deal_of(said)}")
    for p in problems:
        print(f"warning: {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
