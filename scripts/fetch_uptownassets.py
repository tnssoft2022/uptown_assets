#!/usr/bin/env python3
"""Fetch one uptownassets.com project page into listings/.

    python3 scripts/fetch_uptownassets.py <project-url> [--name <folder-name>]

- reads the Thai and English pages (any of /th/ or /en/ in the URL works)
- saves the full-size photos to listings/<code>-<name>/assets/photo-NN.<ext>
  (the page only links thumbnails; the full size is the same path without "thumbnails/")
- writes listings/<code>-<name>/listing.md: the listing text as the site shows it, the source
  URLs, the date fetched, the contact on the page and which photo came from which URL

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
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "listings"
URL_RE = re.compile(r"^https?://(?:www\.)?uptownassets\.com/(?:th|en)/project/(\d+)-([^/?#]+)")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X) uptown-assets-video-tool"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</p\s*>", "\n", fragment, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.splitlines()]
    return "\n".join(l for l in lines if l)


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
        print("Not an uptownassets.com project URL (…/th|en/project/<code>-<slug>)", file=sys.stderr)
        return 2
    code, slug = m.group(1), m.group(2)
    urls = {lang: re.sub(r"/(?:th|en)/project/", f"/{lang}/project/", args.url, count=1) for lang in ("th", "en")}

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

    out = [f"# {th.get('name') or en.get('name') or slug}", ""]
    out += [f"- รหัสทรัพย์ (code in the URL): {code}",
            f"- Source (th): {urls['th']}",
            f"- Source (en): {urls['en']}",
            f"- Fetched: {today}",
            f"- Contact on the page: {thai_phone(phone) if phone else '-'}" + (f", {email}" if email else ""),
            "- Photos: from the Uptown Assets site (the company's own listing)", ""]
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
    for p in problems:
        print(f"warning: {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
