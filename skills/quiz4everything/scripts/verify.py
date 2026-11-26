#!/usr/bin/env python3
"""Stage 4 (deterministic half): the QA gate.

Every check here is machine-checkable and cheap. This script is the reason the
generation prompt can be written in prose: whatever the model claims, this
decides. Anything it cannot decide deterministically becomes a *queued*
question for an adversarial review pass (see adversarial_prompt()).

Usage:
    python3 verify.py --doc document.json --bank bank.json
    python3 verify.py --doc document.json --bank bank.json --report qa.json
    python3 verify.py --doc document.json --bank bank.json --adversarial-out adv.json
    python3 verify.py --doc document.json --bank bank.json --strict   # warnings fail too

Exit codes: 0 pass (possibly with warnings), 1 rejections found, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

import _console  # local encoding shim

MIN_SPAN_CHARS = 40
MAX_OPTION_LEN_RATIO = 1.40
NEAR_DUP_THRESHOLD = 0.90
TF_SHARE_MAX = 0.34
L1_SHARE_MAX = 0.60
TOPIC_SHARE_MAX = 0.30
MIN_EXPLANATION_CHARS = 15
VALID_TYPES = {"mcq", "cloze", "short_answer", "true_false", "ordering", "numeric"}
VALID_LEVELS = {"L1", "L2", "L3", "L4"}


# ------------------------------------------------------------------ normalize

def norm_ws(s: str) -> str:
    """Whitespace-insensitive form used for span matching. Never changes letters."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    s = re.sub(r"-\s*\n\s*", "", s)          # rejoin line-broken hyphenation
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm_all(text: str) -> str:
    """Return (normalized_text, index_map) so we can recover original offsets."""
    out = []
    idx = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "-" and i + 1 < n and text[i + 1] in "\n\r":
            j = i + 1
            while j < n and text[j] in "\n\r \t":
                j += 1
            if j < n and text[j].islower():
                i = j                       # drop the hyphen and the break
                continue
        if ch.isspace():
            out.append(" ")
            idx.append(i)
            while i + 1 < n and text[i + 1].isspace():
                i += 1
            i += 1
            continue
        c = unicodedata.normalize("NFC", ch)
        if c in "\u2019\u2018":
            c = "'"
        elif c in "\u201c\u201d":
            c = '"'
        elif c in "\u2013\u2014\u2212":
            c = "-"
        out.append(c)
        idx.append(i)
        i += 1
    # collapse runs of spaces introduced above
    text2 = re.sub(r" {2,}", " ", "".join(out))
    return text2, idx


# --------------------------------------------------------------------- checks

def find_span(doc_text: str, quote: str, claimed: dict | None) -> dict:
    """Locate `quote` in doc_text. Returns a result dict with an exact/fuzzy verdict."""
    nq = norm_ws(quote)
    if len(nq) < MIN_SPAN_CHARS:
        return {"status": "reject", "reason": f"span shorter than {MIN_SPAN_CHARS} chars",
                "normalized_chars": len(nq)}

    ntext, _idx = norm_all(doc_text)

    pos = ntext.find(nq)
    if pos >= 0:
        return {"status": "exact", "reason": "verbatim", "start_norm": pos,
                "end_norm": pos + len(nq), "normalized_chars": len(nq)}

    # Fuzzy: slide a window the length of the quote and keep the best ratio.
    best = (0.0, -1)
    win = len(nq)
    step = max(1, win // 12)
    for start in range(0, max(1, len(ntext) - win + 1), step):
        r = SequenceMatcher(None, nq, ntext[start:start + win]).ratio()
        if r > best[0]:
            best = (r, start)
            if r > 0.99:
                break
    ratio, start = best
    claimed_pages = (claimed or {}).get("page")
    if ratio >= 0.90:
        return {"status": "fuzzy", "reason": f"best match {ratio:.3f} (<1.0)",
                "similarity": round(ratio, 3), "start_norm": start,
                "end_norm": start + win, "normalized_chars": len(nq),
                "claimed_page": claimed_pages}
    return {"status": "reject", "reason": f"span not found (best match {ratio:.3f})",
            "similarity": round(ratio, 3), "claimed_page": claimed_pages}


def check_item(item: dict, doc: dict, section_text_cache: dict) -> dict:
    """Per-item checks. Returns {'item_id', 'status', 'violations': [], 'span': {...}}."""
    v: list[str] = []
    warns: list[str] = []
    iid = str(item.get("id", "<no-id>"))

    # --- schema presence
    for field in ("id", "type", "level", "topic", "stem", "source_span", "language"):
        if not item.get(field):
            v.append(f"missing field: {field}")
    if item.get("type") not in VALID_TYPES:
        v.append(f"invalid type {item.get('type')!r}")
    if item.get("level") not in VALID_LEVELS:
        v.append(f"invalid level {item.get('level')!r}")
    if not isinstance(item.get("source_span"), dict):
        v.append("source_span must be an object")
        return {"item_id": iid, "status": "reject", "violations": v, "warnings": warns}

    # --- provenance (03 §9: non-negotiable)
    prov = item.get("provenance") or {}
    for field in ("model", "prompt_version", "generated_at"):
        if not prov.get(field):
            warns.append(f"provenance.{field} missing")

    # --- span verification
    quote = item["source_span"].get("quote", "")
    span = find_span(doc["text"], quote, item["source_span"])
    if span["status"] == "reject":
        v.append("span: " + span["reason"])
    elif span["status"] == "fuzzy":
        warns.append("span: " + span["reason"])

    # claimed page must agree
    if span.get("status") in ("exact", "fuzzy") and span.get("claimed_page"):
        actual = page_at_offset(doc, span["start_norm"])
        if actual and actual != span["claimed_page"]:
            warns.append(f"span page mismatch: claimed {span['claimed_page']}, found {actual}")

    # --- section containment: the span must sit inside the item's section
    sec = next((s for s in doc["sections"] if s["id"] == item.get("section_id")), None)
    if sec is None:
        warns.append(f"unknown section_id {item.get('section_id')!r}")
    elif span["status"] != "reject":
        s_text = section_text_cache.setdefault(
            sec["id"], norm_ws(doc["text"][sec["char_start"]:sec["char_end"]]))
        if norm_ws(quote) not in s_text:
            v.append("span lies outside the declared section")

    # --- language
    if item.get("language") and item["language"] != doc.get("lang"):
        v.append(f"language {item['language']!r} != document {doc.get('lang')!r}")

    # --- format-specific structure
    t = item.get("type")
    if t in ("mcq", "true_false"):
        opts = item.get("options") or []
        if t == "mcq" and len(opts) != 3:
            v.append(f"mcq must have exactly 3 options, has {len(opts)}")
        if t == "true_false" and [o.strip().lower() for o in opts] != ["true", "false"]:
            v.append("true_false options must be exactly ['True','False']")
        if len({norm_ws(o) for o in opts}) != len(opts):
            v.append("duplicate options")
        for o in opts:
            if re.search(r"\b(all|none) of the above\b", o, re.I) or \
               re.search(r"\b(all|none) of these\b", o, re.I):
                v.append("'all/none of the above' option")
        key = item.get("key")
        if t == "mcq":
            letters = "ABCDE"[:len(opts)]
            if key not in letters:
                # allow a full option text as key
                if key is not None and norm_ws(key) not in {norm_ws(o) for o in opts}:
                    v.append(f"key {key!r} is not one of the options")
            elif key is None:
                v.append("missing key")
        elif t == "true_false":
            if str(key).strip().lower() not in ("true", "false"):
                v.append(f"true_false key must be True/False, got {key!r}")
        # length cue
        if len(opts) >= 2:
            lens = [len(o) for o in opts if o.strip()]
            if lens and max(lens) / max(1, min(lens)) > MAX_OPTION_LEN_RATIO:
                warns.append(
                    f"option length spread {min(lens)}-{max(lens)} chars "
                    f"(> {int((MAX_OPTION_LEN_RATIO - 1) * 100)}% cue)")
        # distractor rationale completeness
        if t == "mcq":
            dr = item.get("distractor_rationale") or {}
            for letter in letters:
                if letter == key:
                    continue
                if not dr.get(letter) and not dr.get(str(letter)):
                    warns.append(f"no distractor_rationale for option {letter}")

    if t == "cloze":
        stem = item.get("stem", "")
        if "___" not in stem and "____" not in stem:
            v.append("cloze stem has no blank")
        if item.get("key") and norm_ws(str(item["key"])).lower() in norm_ws(stem).lower():
            v.append("cloze key appears in the stem")

    if t == "numeric":
        k = item.get("key")
        if not isinstance(k, dict) or "value" not in k or "unit" not in k:
            v.append("numeric key must be {value, unit, tolerance?}")

    # --- double negation
    stem = item.get("stem", "")
    if re.search(r"\bnot\b[^.]{0,40}\b(not|un|in)\w+", stem, re.I):
        warns.append("possible double negation in stem")

    # --- explanations
    for field in ("explanation_correct", "takeaway"):
        val = item.get(field) or ""
        if len(val.strip()) < MIN_EXPLANATION_CHARS:
            v.append(f"{field} missing or shorter than {MIN_EXPLANATION_CHARS} chars")

    # --- difficulty estimate
    est = item.get("est_difficulty")
    if isinstance(est, (int, float)):
        if not (0.40 <= est <= 0.95):
            warns.append(f"est_difficulty {est} outside 0.40-0.95 band")
    else:
        warns.append("est_difficulty missing")

    # --- concept link (unit of mastery)
    if not item.get("concept_id"):
        warns.append("no concept_id: this item cannot contribute to concept-level mastery")

    status = "reject" if v else "pass"
    return {"item_id": iid, "status": status, "violations": v,
            "warnings": warns, "span": span}


def page_at_offset(doc: dict, norm_pos: int) -> int | None:
    """Best-effort: map a normalized-text position back to a page number."""
    if not doc.get("pages"):
        return None
    # normalized positions are close to raw positions for prose; use a ratio
    ratio = norm_pos / max(1, doc["chars"])
    est_raw = int(ratio * doc["chars"])
    page = None
    for p in doc["pages"]:
        if est_raw >= p["char_start"]:
            page = p["n"]
    return page


def check_bank(items: list[dict], results: list[dict]) -> dict:
    """Bank-level aggregate checks."""
    problems: list[str] = []
    warns: list[str] = []
    n = len(items)
    if n == 0:
        return {"problems": ["empty bank"], "warnings": [], "stats": {}}

    by_type: dict[str, int] = {}
    by_level: dict[str, int] = {}
    by_topic: dict[str, int] = {}
    key_counts: dict[str, int] = {}
    for it in items:
        by_type[it.get("type", "?")] = by_type.get(it.get("type", "?"), 0) + 1
        by_level[it.get("level", "?")] = by_level.get(it.get("level", "?"), 0) + 1
        by_topic[it.get("topic", "?")] = by_topic.get(it.get("topic", "?"), 0) + 1
        if it.get("type") == "mcq":
            k = str(it.get("key"))
            key_counts[k] = key_counts.get(k, 0) + 1

    tf = by_type.get("true_false", 0)
    if tf / n > TF_SHARE_MAX:
        problems.append(f"true/false is {tf / n:.0%} of the bank (max {TF_SHARE_MAX:.0%}); "
                        "TF has a 50% guess floor and inflates apparent mastery")
    if by_type.get("mcq", 0) == n:
        problems.append("bank is 100% recognition (mcq): no production format (DR-14)")
    prod = by_type.get("cloze", 0) + by_type.get("short_answer", 0) + by_type.get("numeric", 0)
    if prod == 0:
        problems.append("no production-format items (cloze/short_answer/numeric) (DR-14)")

    l1 = by_level.get("L1", 0)
    if l1 / n > L1_SHARE_MAX:
        warns.append(f"L1 (recall) is {l1 / n:.0%} of the bank (target <= {L1_SHARE_MAX:.0%})")

    for topic, c in by_topic.items():
        if c / n > TOPIC_SHARE_MAX:
            warns.append(f"topic {topic!r} is {c / n:.0%} of the bank (target <= {TOPIC_SHARE_MAX:.0%})")

    if key_counts and len(key_counts) > 1:
        total = sum(key_counts.values())
        hi = max(key_counts.values())
        if hi / total > 0.7:
            warns.append(f"correct-answer position is skewed: {key_counts}")
    elif key_counts and len(key_counts) == 1 and sum(key_counts.values()) >= 3:
        warns.append(f"every mcq has the same key position ({next(iter(key_counts))}): "
                     "position bias will be learned")

    # near-duplicate detection over stems (token Jaccard; no embeddings needed)
    stems = [norm_ws(it.get("stem", "")).lower() for it in items]
    dups = []
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            a, b = set(re.findall(r"\w+", stems[i])), set(re.findall(r"\w+", stems[j]))
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac >= NEAR_DUP_THRESHOLD:
                dups.append((items[i].get("id"), items[j].get("id"), round(jac, 2)))
    for a, b, jac in dups:
        warns.append(f"near-duplicate stems: {a} ~ {b} (jaccard {jac})")

    # concept coverage
    concepts = {it.get("concept_id") for it in items if it.get("concept_id")}
    rejected = sum(1 for r in results if r["status"] == "reject")

    return {
        "problems": problems,
        "warnings": warns,
        "stats": {
            "items": n,
            "rejected": rejected,
            "passed": n - rejected,
            "by_type": by_type,
            "by_level": by_level,
            "topics": len(by_topic),
            "concepts": len(concepts),
            "items_per_concept": round(n / len(concepts), 2) if concepts else None,
            "key_spread": key_counts,
        },
    }


# --------------------------------------------------------------- adversarial

ADV_TEMPLATE = """You are auditing a quiz item generated from a document excerpt.

Answer ONLY from the excerpt. Do not use outside knowledge.

EXCERPT (verbatim from the source):
---
{span}
---

ITEM
type: {type}
stem: {stem}
options: {options}
claimed key: {key}

Decide, and be specific:
1. Is the item answerable from the excerpt alone? If not, what is missing?
2. Is the claimed key unambiguously correct?
3. Is any other option also defensible from the excerpt? Quote the words that
   would make it correct. This is the failure we care about most.
4. Does the stem misstate the source (hedging dropped, correlation called
   causation, a paraphrase that changes the claim)?
5. Is the item testing a load-bearing idea, or trivia?

Reply as JSON:
{{"verdict": "ok"|"reject"|"warn", "second_key": "A|B|C|none",
 "reasons": ["..."], "suggested_fix": "..."}}"""


def adversarial_prompt(item: dict) -> str:
    span = (item.get("source_span") or {}).get("quote", "")
    return ADV_TEMPLATE.format(
        span=span,
        type=item.get("type"),
        stem=item.get("stem"),
        options=item.get("options"),
        key=item.get("key"),
    )


# ---------------------------------------------------------------------- main

def main(argv=None) -> int:
    _console.setup()
    ap = argparse.ArgumentParser(description="Deterministic QA gate for a quiz bank.")
    ap.add_argument("--doc", required=True, help="document.json from ingest.py")
    ap.add_argument("--bank", required=True, help="bank.json from generation")
    ap.add_argument("--report", help="write the full JSON report here")
    ap.add_argument("--adversarial-out", help="write queued adversarial prompts here")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    try:
        doc = json.load(open(args.doc, encoding="utf-8"))
        bank = json.load(open(args.bank, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    items = bank.get("items") or bank.get("questions") or []
    if not isinstance(items, list):
        print("error: bank has no item list (expected 'items' or 'questions')", file=sys.stderr)
        return 2

    cache: dict[str, str] = {}
    results = [check_item(it, doc, cache) for it in items]
    agg = check_bank(items, results)

    rejects = [r for r in results if r["status"] == "reject"]
    warn_items = [r for r in results if r["warnings"]]

    report = {
        "document": {"doc_id": doc.get("doc_id"), "filename": doc.get("filename"),
                     "lang": doc.get("lang"), "sections": len(doc.get("sections", []))},
        "bank": {"id": bank.get("id"), "title": bank.get("title"),
                 "requested": (bank.get("meta") or {}).get("num_questions")},
        "summary": {
            "items": len(items),
            "passed": len(items) - len(rejects),
            "rejected": len(rejects),
            "with_warnings": len(warn_items),
            "bank_problems": len(agg["problems"]),
            "bank_warnings": len(agg["warnings"]),
        },
        "stats": agg["stats"],
        "bank_problems": agg["problems"],
        "bank_warnings": agg["warnings"],
        "items": results,
    }

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)

    if args.adversarial_out:
        todo = [{"item_id": r["item_id"], "prompt": adversarial_prompt(it)}
                for r, it in zip(results, items) if r["status"] == "pass"]
        with open(args.adversarial_out, "w", encoding="utf-8") as fh:
            json.dump(todo, fh, ensure_ascii=False, indent=1)
        if not args.quiet:
            print(f"queued {len(todo)} adversarial reviews -> {args.adversarial_out}")

    if not args.quiet:
        s = report["summary"]
        print(f"{s['passed']}/{s['items']} items passed deterministic QA")
        if rejects:
            print("\nREJECTED:")
            for r in rejects:
                print(f"  {r['item_id']}: {'; '.join(r['violations'])}")
        if agg["problems"]:
            print("\nBANK PROBLEMS:")
            for p in agg["problems"]:
                print(f"  - {p}")
        shown = 0
        for r in warn_items:
            for w in r["warnings"]:
                print(f"  warn {r['item_id']}: {w}")
                shown += 1
                if shown >= 15:
                    break
            if shown >= 15:
                print("  ... (see report for the rest)")
                break
        for w in agg["warnings"]:
            print(f"  warn bank: {w}")
        st = agg["stats"]
        if st:
            print(f"\nformats {st['by_type']}  levels {st['by_level']}  "
                  f"concepts {st['concepts']}  keys {st['key_spread']}")

    failed = bool(rejects) or bool(agg["problems"])
    if args.strict:
        failed = failed or any(r["warnings"] for r in results) or bool(agg["warnings"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
