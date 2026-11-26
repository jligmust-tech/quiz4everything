#!/usr/bin/env python3
"""Stage 1-2 of the quiz4everything pipeline: document -> normalized text -> section outline.

Deterministic. No network, no model calls.

Produces the ONLY thing span verification can work against: one canonical text
string with stable character offsets, kept line-structured so headings stay
detectable. Whitespace normalization is the *verifier's* job (see verify.py),
not the ingest's — collapsing newlines here destroys both headings and page
fidelity.

Usage:
    python3 ingest.py DOC --out document.json
    python3 ingest.py DOC --stats
    python3 ingest.py DOC --engine pdftotext --out document.json

Supported inputs: .pdf .txt .md .markdown
Exit codes: 0 ok, 2 unreadable/unsupported, 3 nothing extractable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

import _console  # local encoding shim; scripts/ is on sys.path when run directly

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")

# ---------------------------------------------------------------- extraction


def _clean(text: str) -> str:
    """Normalize characters, PRESERVE newlines. Line structure is information."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00ad", "")                      # soft hyphen
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\u2013", "-"), ("\u2014", "-"),
                 ("\u2212", "-"), ("\u00a0", " ")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t\u2000-\u200a\u202f\u205f]", " ", text)
    text = re.sub(r"[ ]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip("\n")


def _dehyphenate(text: str) -> str:
    """Undo end-of-line hyphenation: 'represen-\\ntation' -> 'representation'."""
    return re.sub(r"([A-Za-z])-\n(?=[a-z])", r"\1", text)


def _extract_pdf_pypdf(path: str) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise SystemExit(f"error: PDF is encrypted: {path}")
    return [(p.extract_text() or "") for p in reader.pages]


def _extract_pdf_pdftotext(path: str) -> list[str]:
    # pdftotext always emits UTF-8 (we pass -enc UTF-8), but text=True would
    # decode with the *locale* codec. On a Windows GBK console that mangles or
    # crashes on Chinese documents, so the encoding is pinned explicitly.
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise SystemExit(f"error: pdftotext failed: {out.stderr.strip()}")
    pages = out.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def _extract_pdf(path: str, engine: str) -> tuple[list[str], str]:
    if engine in ("auto", "pypdf"):
        try:
            pages = _extract_pdf_pypdf(path)
            if sum(len(p.strip()) for p in pages) > 0:
                return pages, "pypdf"
            if engine == "pypdf":
                raise SystemExit("error: pypdf extracted no text (scanned PDF? needs OCR)")
        except ImportError:
            if engine == "pypdf":
                raise SystemExit("error: pypdf not installed (pip install pypdf)")
    try:
        return _extract_pdf_pdftotext(path), "pdftotext"
    except FileNotFoundError:
        raise SystemExit(
            "error: no PDF engine available. Install pypdf (pip install pypdf) "
            "or poppler-utils (pdftotext)."
        )


def _extract_text_file(path: str) -> tuple[list[str], str]:
    raw = open(path, "rb").read()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return [raw.decode(enc)], f"text:{enc}"
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"error: cannot decode {path}")

# ------------------------------------------------------------- heading detect


NUMBERED = re.compile(
    r"^(?:(?:chapter|section|part|unit|appendix|lecture|module)\s+)?"
    r"(?:\d{1,2}(?:\.\d{1,2}){0,3}\.?|[IVXLC]{1,6}\.)\s+[A-Z\u4e00-\u9fff]",
    re.I,
)
TERMINAL = tuple(".!?,;)")
NAMED = re.compile(
    r"^(?:chapter|section|part|unit|appendix|introduction|conclusion|"
    r"summary|abstract|references|bibliography|acknowledg\w*|"
    r"methods?|materials|results?|discussion|background|related work|"
    r"future work|limitations?)\b",
    re.I,
)
NOISE = re.compile(r"^[\s\d.\-|/·•_=*#~]+$")
CAPTION = re.compile(
    r"^(?:figure|fig\.?|table|tab\.?|eq\.?|equation|box|exhibit|plate)\s*[\dIVX]+",
    re.I,
)
BADGE = re.compile(r"^\s*(?:page\s*)?\d{1,4}\s*(?:/|of)\s*\d{1,4}\s*$", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _is_titlecase(s: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", s)
    if not words:
        return False
    return sum(1 for w in words if w[0].isupper()) / len(words) >= 0.6


def heading_score(line: str, prev_blank: bool, next_len: int) -> float:
    s = _norm(line)
    if not s or len(s) < 3 or NOISE.match(s) or BADGE.match(s) or CAPTION.match(s):
        return 0.0
    if len(s) > 90 or s.endswith(TERMINAL):
        return 0.0
    score = 0.0
    if NUMBERED.match(s):
        score += 0.55
    if NAMED.match(s):
        score += 0.30
    if s.isupper() and len(s) > 3:
        score += 0.35
    elif _is_titlecase(s):
        score += 0.20
    if len(s.split()) <= 12:
        score += 0.10
    if prev_blank:
        score += 0.10
    if next_len > len(s) * 2:
        score += 0.10
    return min(score, 1.0)


MD_ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")


def _markdown_titles(code: str) -> dict[str, int]:
    """title -> level, from ATX headings in the markdown source."""
    titles: dict[str, int] = {}
    for ln in code.split("\n"):
        m = MD_ATX.match(ln)
        if m:
            titles[_norm(m.group(2))] = len(m.group(1))
    return titles


def detect_sections(pages: list[str], md_titles: dict[str, int]) -> tuple[list[dict], str, list[int]]:
    """Cut the canonical text into sections at detected headings."""
    page_offsets: list[int] = []
    parts: list[str] = []
    cursor = 0
    for pg in pages:
        cleaned = _dehyphenate(_clean(pg))
        page_offsets.append(cursor)
        parts.append(cleaned)
        cursor += len(cleaned) + 2          # we join pages with "\n\n"
    full = "\n\n".join(parts)

    lines = full.split("\n")
    starts: list[int] = []
    pos = 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1

    hits: list[tuple[int, str, float, int]] = []
    for i, ln in enumerate(lines):
        m = MD_ATX.match(ln)
        s = _norm(m.group(2)) if m else _norm(ln)
        if not s:
            continue
        if s in md_titles:
            hits.append((i, s, 0.95, md_titles[s]))
            continue
        prev_blank = (i == 0) or (not lines[i - 1].strip())
        nxt = next((lines[j].strip() for j in range(i + 1, min(i + 4, len(lines)))
                    if lines[j].strip()), "")
        sc = heading_score(s, prev_blank, len(nxt))
        if sc >= 0.55:
            hits.append((i, s, round(sc, 2), 0))

    # Collapse wraps: a heading wrapped over 2-3 lines keeps its first line. Only
    # collapse an adjacent line that would not qualify as a heading on its own —
    # PDF extraction often yields consecutive headings with no blank line between.
    merged: list[tuple[int, str, float, int]] = []
    for h in hits:
        if merged and h[0] - merged[-1][0] == 1 and h[2] < 0.8:
            continue
        merged.append(h)

    if not merged:
        words = len(full.split())
        return [{
            "id": "s1", "ordinal": 1, "title": "Full document", "level": 1,
            "char_start": 0, "char_end": len(full),
            "page_start": 1, "page_end": len(pages),
            "words": words,
            "est_items": max(1, min(25, round(words / 90))),
            "heading_confidence": 0.0,
            "warnings": ["no headings detected; the whole document is one section"],
        }], full, page_offsets

    sections: list[dict] = []
    for idx, (li, title, conf, level) in enumerate(merged):
        start = 0 if idx == 0 else starts[li]
        end = starts[merged[idx + 1][0]] if idx + 1 < len(merged) else len(full)
        body = full[start:end]
        words = len(body.split())
        warnings: list[str] = []
        if conf < 0.7:
            warnings.append("low heading confidence - confirm the section split")
        if re.search(r"\b(references|bibliography|works cited|index|citations)\b", title, re.I):
            warnings.append("reference/index section - do not generate items")
        if re.search(r"\b(table of contents|contents)\b", title, re.I):
            warnings.append("front matter - do not generate items")
        if words < 80:
            warnings.append("short section (<80 words): supports 1-2 items at most")
        if words > 4000:
            warnings.append("long section (>4000 words): split at sub-headings first")
        sections.append({
            "id": f"s{idx + 1}",
            "ordinal": idx + 1,
            "title": title,
            "level": level or 1,
            "char_start": start,
            "char_end": end,
            "page_start": _page_of(start, page_offsets),
            "page_end": _page_of(max(start, end - 1), page_offsets),
            "words": words,
            "est_items": max(1, min(25, round(words / 90))),
            "heading_confidence": conf,
            "warnings": warnings,
        })
    return sections, full, page_offsets


def _page_of(char_pos: int, page_offsets: list[int]) -> int:
    page = 1
    for i, off in enumerate(page_offsets):
        if char_pos >= off:
            page = i + 1
    return page

# --------------------------------------------------------------------- main


def detect_lang(text: str) -> str:
    sample = text[:4000]
    if not sample.strip():
        return "unknown"
    return "zh" if len(CJK.findall(sample)) / max(1, len(sample)) > 0.15 else "en"


def build(path: str, engine: str, max_pages: int | None) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        raise SystemExit(f"error: no such file: {path}")

    if ext == ".pdf":
        pages, used = _extract_pdf(path, engine)
    elif ext in (".txt", ".md", ".markdown"):
        pages, used = _extract_text_file(path)
    else:
        raise SystemExit(f"error: unsupported extension {ext!r} (pdf/txt/md only)")

    truncated = False
    if max_pages and len(pages) > max_pages:
        pages = pages[:max_pages]
        truncated = True

    if sum(len(p.strip()) for p in pages) == 0:
        raise SystemExit("error: extracted no text (scanned PDF? needs OCR first)")

    is_md = ext in (".md", ".markdown")
    md_titles = _markdown_titles(pages[0]) if is_md else {}

    sections, full, page_offsets = detect_sections(pages, md_titles)
    if truncated:
        sections[-1]["warnings"].append(
            f"truncated at --max-pages {max_pages}: items cover the first {max_pages} pages only")

    page_meta = [{
        "n": i + 1,
        "char_start": page_offsets[i],
        "char_end": page_offsets[i] + len(_dehyphenate(_clean(pg))),
        "chars": len(_dehyphenate(_clean(pg))),
    } for i, pg in enumerate(pages)]

    return {
        "doc_id": "doc-" + hashlib.sha1(
            f"{os.path.basename(path)}|{len(full)}|{full[:200]}".encode()
        ).hexdigest()[:10],
        "path": os.path.abspath(path),
        "filename": os.path.basename(path),
        "engine": used,
        "n_pages": len(pages),
        "chars": len(full),
        "words": len(full.split()),
        "lang": detect_lang(full),
        "truncated": truncated,
        "pages": page_meta,
        "sections": sections,
        "text": full,
    }


def print_stats(doc: dict) -> None:
    print(f"{doc['filename']}  ({doc['engine']}, {doc['n_pages']}p, "
          f"{doc['words']} words, lang={doc['lang']})")
    print(f"{'#':>3}  {'pages':>8}  {'words':>6}  {'items':>5}  title")
    for s in doc["sections"]:
        warn = ("  ! " + "; ".join(s["warnings"])) if s["warnings"] else ""
        print(f"{s['ordinal']:>3}  {s['page_start']:>3}-{s['page_end']:<4}  "
              f"{s['words']:>6}  {s['est_items']:>5}  {s['title'][:58]}{warn}")


def main(argv=None) -> int:
    _console.setup()
    ap = argparse.ArgumentParser(description="Build a document + section outline.")
    ap.add_argument("document")
    ap.add_argument("--out", help="write JSON here (default: stdout)")
    ap.add_argument("--engine", default="auto", choices=["auto", "pypdf", "pdftotext"])
    ap.add_argument("--max-pages", type=int, default=None,
                    help="hard cap; emits a warning so nothing is dropped silently")
    ap.add_argument("--stats", action="store_true", help="print the section table only")
    args = ap.parse_args(argv)

    doc = build(args.document, args.engine, args.max_pages)
    if args.stats:
        print_stats(doc)
        return 0

    payload = json.dumps(doc, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"wrote {args.out}: {len(doc['sections'])} sections, "
              f"{doc['chars']} chars, {doc['words']} words, lang={doc['lang']}")
        for s in doc["sections"]:
            if s["warnings"]:
                print(f"  warning s{s['ordinal']}: {'; '.join(s['warnings'])}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
