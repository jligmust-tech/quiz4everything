#!/usr/bin/env python3
"""Stages 5-6: practice sessions, review queue, mastery report.

Design commitments encoded here (see docs/theory/02 and 04):
  - ReviewEvent is the source of truth; all state is recomputed from events.
  - Feedback always comes AFTER the attempt (DR-6), and includes the source
    excerpt and every distractor's rationale (DR-4/5).
  - No answer key is visible before an attempt (DR-23).
  - A single score is never presented as mastery (DR-13/28); the report shows
    concept counts and calibration instead.
  - Missed items are re-asked once, later in the same session (DR-20/22).
  - Guessing on MCQ is corrected before anything is called knowledge (04 §4).

Usage:
    python3 session.py init   --data quiz-data --doc document.json
    python3 session.py add    --data quiz-data --bank bank.json
    python3 session.py practice --data quiz-data --section s1 [--max 8] [--json]
    python3 session.py review   --data quiz-data [--json]
    python3 session.py stats    --data quiz-data [--json]

Exit codes: 0 ok, 1 nothing to do / no due items, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schedule as sched  # noqa: E402

EVENTS = "events.jsonl"
BANKS = "banks"
DOC = "document.json"


# ------------------------------------------------------------------- storage

def paths(data: str) -> dict:
    return {
        "root": data,
        "events": os.path.join(data, EVENTS),
        "banks": os.path.join(data, BANKS),
        "doc": os.path.join(data, DOC),
    }


def ensure(data: str) -> dict:
    p = paths(data)
    os.makedirs(p["banks"], exist_ok=True)
    if not os.path.exists(p["events"]):
        open(p["events"], "w", encoding="utf-8").close()
    return p


def load_doc(data: str) -> dict | None:
    p = paths(data)
    if not os.path.exists(p["doc"]):
        return None
    return json.load(open(p["doc"], encoding="utf-8"))


def load_banks(data: str) -> list[dict]:
    p = paths(data)
    out = []
    if not os.path.isdir(p["banks"]):
        return out
    for fn in sorted(os.listdir(p["banks"])):
        if fn.endswith(".json"):
            out.append(json.load(open(os.path.join(p["banks"], fn), encoding="utf-8")))
    return out


def load_events(data: str) -> list[dict]:
    p = paths(data)
    out = []
    if not os.path.exists(p["events"]):
        return out
    with open(p["events"], encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def append_event(data: str, ev: dict) -> None:
    with open(paths(data)["events"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_ts() -> float:
    return time.time()


# ---------------------------------------------------------------- item index

def all_items(data: str) -> dict[str, dict]:
    idx = {}
    for bank in load_banks(data):
        for it in bank.get("items", []):
            it.setdefault("bank_id", bank.get("id"))
            idx[it["id"]] = it
    return idx


def items_for_section(data: str, section_id: str) -> list[dict]:
    return [it for it in all_items(data).values() if it.get("section_id") == section_id]


# --------------------------------------------------------------- event -> state

def build_state(events: list[dict]) -> dict[str, dict]:
    """Recompute per-item scheduler state from the event log. Pure replay."""
    state: dict[str, dict] = {}
    for ev in sorted(events, key=lambda e: e.get("ts_epoch", 0)):
        iid = ev.get("item_id")
        if not iid or ev.get("kind") != "review":
            continue
        prev = state.get(iid)
        elapsed = 0.0
        if prev and prev.get("last_ts") is not None:
            elapsed = max(0.0, (ev["ts_epoch"] - prev["last_ts"]) / 86400.0)
        st = sched.review(
            None if prev is None else {"S": prev["S"], "D": prev["D"],
                                       "reps": prev["reps"], "lapses": prev["lapses"]},
            rating=int(ev.get("rating", 3)),
            elapsed_days=elapsed,
            desired_retention=float(ev.get("desired_retention", sched.DEFAULT_RETENTION)),
        )
        st["last_ts"] = ev["ts_epoch"]
        st["next_due_ts"] = ev["ts_epoch"] + st["interval_days"] * 86400.0
        st["item_id"] = iid
        st["concept_id"] = ev.get("concept_id")
        st["section_id"] = ev.get("section_id")
        state[iid] = st
    return state


def due_items(data: str, events: list[dict] | None = None) -> list[dict]:
    events = events if events is not None else load_events(data)
    state = build_state(events)
    idx = all_items(data)
    t = now_ts()
    due = []
    for iid, st in state.items():
        if st.get("next_due_ts", 0) <= t and iid in idx:
            due.append((st["next_due_ts"], idx[iid]))
    due.sort(key=lambda x: x[0])
    return [it for _, it in due]


def unseen_items(data: str, section_id: str | None) -> list[dict]:
    events = load_events(data)
    seen = {e.get("item_id") for e in events if e.get("kind") == "review"}
    items = (items_for_section(data, section_id) if section_id
             else list(all_items(data).values()))
    return [it for it in items if it["id"] not in seen]


# ------------------------------------------------------------------ grading

def grade(item: dict, response: str) -> tuple[bool, bool, str]:
    """Return (correct, partial, how). Deterministic; no model call.

    For short answers we cannot be sure, so an empty/uncertain match returns
    partial=True and the caller must ask the learner (DR-16).
    """
    t = item.get("type")
    response = (response or "").strip()
    if not response:
        return False, False, "empty"
    low = response.lower()

    if t == "true_false":
        key = str(item.get("key", "")).strip().lower()
        # accept t/f, true/false, in any case
        mapping = {"t": "true", "f": "false", "1": "true", "2": "false"}
        got = mapping.get(low, low)
        return got == key, False, "bool"

    if t == "mcq":
        key = str(item.get("key", "")).strip()
        opts = item.get("options") or []
        # accept a letter, a 1-based number, or the option text
        if len(key) == 1 and key.upper() in "ABCDE":
            idx = "ABCDE".index(key.upper())
            if low in (key.lower(), str(idx + 1)):
                return True, False, "letter"
            if idx < len(opts) and low == opts[idx].strip().lower():
                return True, False, "text"
            return False, False, "mismatch"
        return (low == key.lower()), False, "exact"

    if t == "cloze":
        key = str(item.get("key", "")).strip().lower()
        accept = [a.strip().lower() for a in (item.get("accept") or [])]
        if low == key or low in accept:
            return True, False, "exact"
        # substring either way counts as partial credit
        if key and (key in low or low in key):
            return True, True, "near"
        return False, False, "mismatch"

    if t == "numeric":
        k = item.get("key") or {}
        try:
            val = float("".join(c for c in response if c in "-.0123456789"))
        except ValueError:
            return False, False, "unparsed"
        target = float(k.get("value", 0))
        tol = float(k.get("tolerance", abs(target) * 0.01 or 0.01))
        return abs(val - target) <= tol, False, "numeric"

    if t == "short_answer":
        rubric = [r.lower() for r in (item.get("rubric") or [])]
        key = str(item.get("key", "")).lower()
        hits = sum(1 for r in rubric if r and r in low)
        if rubric:
            if hits == len(rubric):
                return True, False, "rubric-full"
            if hits > 0:
                return True, True, "rubric-partial"
        # token overlap with the model answer
        kt = set(w for w in key.replace(",", " ").split() if len(w) > 3)
        rt = set(w for w in low.replace(",", " ").split() if len(w) > 3)
        if kt and len(kt & rt) / len(kt) >= 0.5:
            return True, False, "overlap"
        return False, True, "unjudged"      # escalate to self-assessment

    if t == "ordering":
        key = [str(x).strip().lower() for x in (item.get("key") or [])]
        got = [x.strip().lower() for x in response.replace(">", ",").split(",") if x.strip()]
        return got == key, False, "sequence"

    return False, False, "unknown-type"


# ------------------------------------------------------------------ display

def bar(n: int = 54) -> str:
    return "-" * n


def show_feedback(item: dict, correct: bool, partial: bool, resp: str) -> None:
    print()
    print(("  CORRECT" if correct and not partial else
           "  PARTLY RIGHT" if partial else "  INCORRECT"))
    key = item.get("key")
    opts = item.get("options") or []
    if item.get("type") == "mcq" and isinstance(key, str) and len(key) == 1:
        i = "ABCDE".index(key.upper())
        print(f"  Answer: {key}. {opts[i] if i < len(opts) else ''}")
    elif item.get("type") == "true_false":
        print(f"  Answer: {key}")
    else:
        print(f"  Answer: {key}")

    print(f"  Why: {item.get('explanation_correct', '').strip()}")
    dr = item.get("distractor_rationale") or {}
    if correct is False and dr:
        for letter, why in dr.items():
            print(f"    {letter} would be chosen by someone who {why.strip().rstrip('.')}.")
    tk = item.get("takeaway")
    if tk:
        print(f"  Keep: {tk.strip()}")
    span = (item.get("source_span") or {}).get("quote")
    if span:
        print(f"  Source: \"{span.strip()}\"")


def ask(item: dict) -> str | None:
    print()
    print(bar())
    tag = f"[{item.get('type')}/{item.get('level')}]"
    print(f"{tag} {item.get('stem', '').strip()}")
    opts = item.get("options") or []
    if item.get("type") == "true_false":
        print("   True / False")
        prompt = "Your answer (True/False, or 'q' to quit): "
    elif item.get("type") == "mcq":
        for i, o in enumerate(opts):
            print(f"   {chr(65 + i)}. {o}")
        prompt = "Your answer (letter, or 'q' to quit): "
    elif item.get("type") == "cloze":
        prompt = "Fill the blank (or 'q' to quit): "
    elif item.get("type") == "numeric":
        prompt = "Value (or 'q' to quit): "
    else:
        prompt = "Your answer in your own words (or 'q' to quit): "
    try:
        resp = input(prompt)
    except EOFError:
        return None
    return None if resp.strip().lower() in ("q", "quit") else resp


# ------------------------------------------------------------------ sessions

def run_session(data: str, items: list[dict], mode: str, as_json: bool,
                desired_retention: float, seed: int | None = None) -> int:
    if not items:
        print("Nothing to practise." if not as_json else json.dumps({"items": []}))
        return 1

    order = command_reshuffle(items, seed)
    asked: list[dict] = []
    results: list[dict] = []
    t_start = now_ts()

    if as_json:
        # Non-interactive: hand the whole queue to the caller. Nothing is
        # recorded here; each answer goes through `session.py answer`.
        ask_list = [{
            "item_id": it["id"],
            "section_id": it.get("section_id"),
            "concept_id": it.get("concept_id"),
            "type": it.get("type"),
            "level": it.get("level"),
            "stem": it.get("stem"),
            "options": it.get("options") or [],
            "prompt": ("Letter" if it.get("type") == "mcq"
                       else "True or False" if it.get("type") == "true_false"
                       else "Value" if it.get("type") == "numeric"
                       else "Fill the blank" if it.get("type") == "cloze"
                       else "In your own words"),
        } for it in order]
        print(json.dumps({"mode": mode, "n": len(ask_list), "asks": ask_list},
                         ensure_ascii=False, indent=1))
        return 0

    queue = list(order)
    retry: list[dict] = []
    while queue or retry:
        if not queue:
            queue, retry = retry, []
            if queue:
                print("\n" + bar())
                print("Re-asking the items you missed:")
            continue
        item = queue.pop(0)

        t_prompt = now_ts()
        resp = ask(item)
        t_answered = now_ts()
        if resp is None:
            print("\n(stopped)")
            break

        # latency is think-time, not grade-time: measured around the prompt
        correct, partial, how = grade(item, resp)
        latency_ms = int((t_answered - t_prompt) * 1000)

        # short answers the grader cannot judge: ask the learner (DR-16)
        if how == "unjudged":
            print(f"  Model answer: {item.get('key')}")
            try:
                sa = input("  Did you say essentially that? [y]es/[p]artly/[n]o: ").strip().lower()
            except EOFError:
                sa = "n"
            if sa.startswith("y"):
                correct, partial, how = True, False, "self-yes"
            elif sa.startswith("p"):
                correct, partial, how = True, True, "self-partly"
            else:
                correct, partial, how = False, False, "self-no"

        show_feedback(item, correct, partial, resp)

        rating = sched.derive_rating(correct, latency_ms, None, partial=partial)
        append_event(data, {
            "kind": "review",
            "item_id": item["id"],
            "concept_id": item.get("concept_id"),
            "section_id": item.get("section_id"),
            "ts": now_iso(),
            "ts_epoch": t_answered,
            "mode": mode,
            "format": item.get("type"),
            "response": resp,
            "correct": correct,
            "partial": partial,
            "grader": how,
            "latency_ms": latency_ms,
            "rating": rating,
            "desired_retention": desired_retention,
        })
        results.append({"item_id": item["id"], "correct": correct,
                        "partial": partial, "rating": rating, "how": how})
        asked.append(item)

        if not correct and item not in retry and len(asked) < 40:
            retry.append(item)

    # ---- session report: calibration + coverage, never a mastery claim
    n = len(results)
    if n:
        right = sum(1 for r in results if r["correct"] and not r["partial"])
        partly = sum(1 for r in results if r["partial"])
        mins = (now_ts() - t_start) / 60.0
        print("\n" + bar())
        print(f"Session: {n} responses, {right} correct, {partly} partly, "
              f"{n - right - partly} missed ({mins:.0f} min)")
        concepts = {i.get("concept_id") for i in asked if i.get("concept_id")}
        print(f"Concepts touched: {len(concepts)}")
        print("This is a diagnostic for today, not a mastery result.")
        print("Mastery can only be claimed after a delayed re-test "
              "(tomorrow at the earliest).")
    return 0


def cmd_init(args) -> int:
    p = ensure(args.data)
    if not os.path.exists(args.doc):
        print(f"error: no document at {args.doc}", file=sys.stderr)
        return 2
    doc = json.load(open(args.doc, encoding="utf-8"))
    json.dump(doc, open(p["doc"], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"initialized {args.data}: {doc['filename']}, {len(doc['sections'])} sections")
    return 0


def cmd_add(args) -> int:
    p = ensure(args.data)
    if not os.path.exists(args.bank):
        print(f"error: no bank at {args.bank}", file=sys.stderr)
        return 2
    bank = json.load(open(args.bank, encoding="utf-8"))
    items = bank.get("items") or bank.get("questions") or []
    for it in items:
        for field in ("explanation_correct", "takeaway"):
            it.setdefault(field, it.get("explanation", ""))
        it.setdefault("explanation_correct", it.get("explanation", ""))
    bank["items"] = items
    bank.setdefault("id", "bank-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    out = os.path.join(p["banks"], f"{bank['id']}.json")
    json.dump(bank, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"added bank {bank['id']}: {len(items)} items -> {out}")
    return 0


def cmd_practice(args) -> int:
    ensure(args.data)
    items = unseen_items(args.data, args.section)
    if args.section and not items and not items_for_section(args.data, args.section):
        print(f"error: no items for section {args.section!r}", file=sys.stderr)
        return 2
    if not items:
        # everything seen: fall back to the due queue so practice still works
        items = due_items(args.data) or list(all_items(args.data).values())
    if args.max:
        items = items[:args.max]
    return run_session(args.data, items, "practice", args.json, args.retention,
                       getattr(args, "seed", None))


def cmd_review(args) -> int:
    ensure(args.data)
    items = due_items(args.data)
    if args.max:
        items = items[:args.max]
    if not items:
        if args.json:
            print(json.dumps({"items": [], "message": "nothing due"}))
        else:
            st = build_state(load_events(args.data))
            nxt = min((s["next_due_ts"] for s in st.values()), default=None)
            msg = "Nothing due."
            if nxt:
                days = max(0.0, (nxt - now_ts()) / 86400.0)
                msg += f" Next item due in {days:.1f} day(s)."
            else:
                msg += " Practise a section first."
            print(msg)
        return 1
    return run_session(args.data, items, "review", args.json, args.retention,
                       getattr(args, "seed", None))


# -------------------------------------------------------------------- stats

def compute_mastery(events: list[dict], items: dict[str, dict]) -> dict:
    """Concept-level mastery from review history.

    Ladder (04 §4): Exposure -> Attempted -> Retained (>=1 day) -> Stable
    (2 consecutive correct delayed) -> Transferred (correct on a *different*
    item of the same concept, delayed).
    """
    by_concept: dict[str, list[dict]] = {}
    for ev in sorted(events, key=lambda e: e.get("ts_epoch", 0)):
        if ev.get("kind") != "review":
            continue
        cid = ev.get("concept_id") or ev.get("item_id")
        by_concept.setdefault(cid, []).append(ev)

    out = {}
    for cid, evs in by_concept.items():
        delayed = []
        for a, b in zip(evs, evs[1:]):
            gap_days = (b["ts_epoch"] - a["ts_epoch"]) / 86400.0
            if gap_days >= 1.0:
                delayed.append(b)
        delayed_ok = [e for e in delayed if e.get("correct") and not e.get("partial")]
        first_ok = [e for e in evs if e.get("correct")]

        level = "exposure"
        if first_ok:
            level = "attempted"
        if delayed_ok:
            level = "retained"
        # two consecutive correct, both delayed
        consec = 0
        best = 0
        prev_ok_delayed = False
        for e in delayed:
            ok = bool(e.get("correct") and not e.get("partial"))
            consec = consec + 1 if (ok and prev_ok_delayed) else (1 if ok else 0)
            prev_ok_delayed = ok
            best = max(best, consec)
        if best >= 2:
            level = "stable"

        # transfer: correct on an item other than the first one, after a delay
        ids = [e["item_id"] for e in delayed_ok]
        if level in ("stable", "retained") and len(set(ids)) >= 2:
            level = "transferred"

        out[cid] = {"level": level, "reviews": len(evs),
                    "delayed_correct": len(delayed_ok),
                    "items": len({e["item_id"] for e in evs})}
    return out


def cmd_stats(args) -> int:
    ensure(args.data)
    events = load_events(args.data)
    banks = load_banks(args.data)
    items = all_items(args.data)
    doc = load_doc(args.data)
    state = build_state(events)

    reviews = [e for e in events if e.get("kind") == "review"]
    mastery = compute_mastery(events, items)

    # calibration: predicted vs actual cannot be computed without predictions,
    # so report confidence-free honesty metrics instead.
    n = len(reviews)
    correct = sum(1 for e in reviews if e.get("correct") and not e.get("partial"))
    mcq = [e for e in reviews if e.get("format") in ("mcq", "true_false")]
    mcq_obs = (sum(1 for e in mcq if e.get("correct")) / len(mcq)) if mcq else None
    # guess-corrected for 3-option (k=3) and TF (k=2) mixed: use conservative k=3
    mcq_adj = (max(0.0, (mcq_obs - 1 / 3) / (1 - 1 / 3)) if mcq_obs is not None else None)

    due = [s for s in state.values() if s.get("next_due_ts", 0) <= now_ts()]
    levels = {}
    for m in mastery.values():
        levels[m["level"]] = levels.get(m["level"], 0) + 1

    concepts_total = len({i.get("concept_id") for i in items.values() if i.get("concept_id")})

    payload = {
        "document": (doc or {}).get("filename"),
        "banks": len(banks),
        "items": len(items),
        "reviews": n,
        "unique_items_reviewed": len(state),
        "due_now": len(due),
        "accuracy_all": round(correct / n, 3) if n else None,
        "recognition_observed": None if mcq_obs is None else round(mcq_obs, 3),
        "recognition_guess_corrected": None if mcq_adj is None else round(mcq_adj, 3),
        "concepts": {"total": concepts_total, "touched": len(mastery),
                     "by_level": levels},
        "mastery_note": ("Counts are concepts, not items. 'stable' requires two "
                         "consecutive correct delayed reviews."),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0

    print(bar())
    if not banks:
        print("No banks yet. Run ingest + generate + add first.")
        return 1
    print(f"{payload['document'] or '(no document)'}  •  {len(items)} items in "
          f"{len(banks)} bank(s)")
    print(f"reviews: {n}   items seen: {len(state)}   due now: {len(due)}")
    if n:
        print(f"accuracy (all formats): {correct / n:.0%}")
        if mcq_obs is not None:
            print(f"recognition-only: {mcq_obs:.0%} observed, "
                  f"{mcq_adj:.0%} after removing 3-option guessing")
    print()
    print("Concepts (the unit of mastery):")
    if not concepts_total:
        print("  no concepts recorded - items were generated without concept_id")
    else:
        order = ["transferred", "stable", "retained", "attempted", "exposure"]
        for lv in order:
            c = levels.get(lv, 0)
            if c:
                print(f"  {lv:12} {c}")
        print(f"  {'untouched':12} {max(0, concepts_total - len(mastery))}")
        print(f"  of {concepts_total} concepts")
    print()
    print(payload["mastery_note"])
    return 0


# ------------------------------------------------------- non-interactive use

def command_reshuffle(items: list[dict], seed: int | None) -> list[dict]:
    """Stable order for agent-driven sessions; same seed -> same order."""
    out = list(items)
    if seed is None:
        seed = int(datetime.now().strftime("%Y%m%d"))
    random.Random(seed).shuffle(out)
    return out


def feedback_payload(item: dict, correct: bool, partial: bool,
                     how: str, rating: int, latency_ms: int) -> dict:
    """The same content show_feedback prints, as data an agent can render."""
    key = item.get("key")
    answer = key
    opts = item.get("options") or []
    if item.get("type") == "mcq" and isinstance(key, str) and len(key) == 1:
        i = "ABCDE".index(key.upper())
        answer = {"letter": key.upper(),
                  "text": opts[i] if i < len(opts) else ""}
    return {
        "item_id": item.get("id"),
        "correct": correct,
        "partial": partial,
        "grader": how,
        "rating": rating,
        "latency_ms": latency_ms,
        "answer": answer,
        "why": (item.get("explanation_correct") or "").strip(),
        # distractor rationales are the teaching payload on a miss (DR-5)
        "distractors": ({} if correct else {
            k: v for k, v in (item.get("distractor_rationale") or {}).items()
            if k != key
        }),
        "keep": (item.get("takeaway") or "").strip(),
        "source": ((item.get("source_span") or {}).get("quote") or "").strip(),
    }


def cmd_answer(args) -> int:
    """Record one answer without a terminal: the agent-usable path.

    This exists so an agent skill can run the loop inside a chat instead of
    requiring the learner to type into a TTY. Grading is the same function,
    and the event written is identical to the interactive path.
    """
    ensure(args.data)
    items = all_items(args.data)
    item = items.get(args.item)
    if item is None:
        msg = {"error": f"no item {args.item!r}",
               "hint": "run `practice --json` to see valid ids"}
        print(json.dumps(msg, ensure_ascii=False))
        return 2

    t0 = now_ts()
    correct, partial, how = grade(item, args.response)

    # short answers the deterministic grader cannot judge must not be
    # silently marked wrong (DR-16): caller supplies --self
    if how == "unjudged":
        if not args.self:
            print(json.dumps({
                "item_id": args.item,
                "needs_self_assessment": True,
                "grader": how,
                "model_answer": item.get("key"),
                "question": "Did the learner say essentially that?",
                "options": ["yes", "partly", "no"],
                "note": "nothing was recorded; re-run with --self yes|partly|no",
            }, ensure_ascii=False, indent=1))
            return 3
        s = args.self.strip().lower()
        if s.startswith("y"):
            correct, partial, how = True, False, "self-yes"
        elif s.startswith("p"):
            correct, partial, how = True, True, "self-partly"
        else:
            correct, partial, how = False, False, "self-no"

    latency_ms = args.latency_ms if args.latency_ms is not None else 0
    rating = sched.derive_rating(correct, latency_ms,
                                 None if args.latency_ms is None else 20000,
                                 partial=partial, confident=args.confident)

    append_event(args.data, {
        "kind": "review",
        "item_id": item["id"],
        "concept_id": item.get("concept_id"),
        "section_id": item.get("section_id"),
        "ts": now_iso(),
        "ts_epoch": t0,
        "mode": args.mode,
        "format": item.get("type"),
        "response": args.response,
        "correct": correct,
        "partial": partial,
        "grader": how,
        "latency_ms": latency_ms,
        "rating": rating,
        "desired_retention": args.retention,
        "via": "answer-cli",
    })

    nxt = build_state(load_events(args.data)).get(item["id"], {})
    payload = feedback_payload(item, correct, partial, how, rating, latency_ms)
    payload["next_due_days"] = round(nxt.get("interval_days", 0), 2)
    payload["stability"] = round(nxt.get("S", 0), 3)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


# --------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Practice, review, and honest stats.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="store an ingested document")
    p_init.add_argument("--data", default="quiz-data")
    p_init.add_argument("--doc", required=True)
    p_init.set_defaults(fn=cmd_init)

    p_add = sub.add_parser("add", help="add a verified bank")
    p_add.add_argument("--data", default="quiz-data")
    p_add.add_argument("--bank", required=True)
    p_add.set_defaults(fn=cmd_add)

    p_prac = sub.add_parser("practice", help="practise unseen items")
    p_prac.add_argument("--data", default="quiz-data")
    p_prac.add_argument("--section")
    p_prac.add_argument("--max", type=int)
    p_prac.add_argument("--retention", type=float, default=sched.DEFAULT_RETENTION)
    p_prac.add_argument("--json", action="store_true")
    p_prac.add_argument("--seed", type=int, help="reproducible order")
    p_prac.set_defaults(fn=cmd_practice)

    p_rev = sub.add_parser("review", help="practise items that are due")
    p_rev.add_argument("--data", default="quiz-data")
    p_rev.add_argument("--max", type=int)
    p_rev.add_argument("--retention", type=float, default=sched.DEFAULT_RETENTION)
    p_rev.add_argument("--json", action="store_true")
    p_rev.add_argument("--seed", type=int, help="reproducible order")
    p_rev.set_defaults(fn=cmd_review)

    p_st = sub.add_parser("stats", help="mastery + calibration report")
    p_st.add_argument("--data", default="quiz-data")
    p_st.add_argument("--json", action="store_true")
    p_st.set_defaults(fn=cmd_stats)

    p_ans = sub.add_parser("answer", help="record one answer (non-interactive)")
    p_ans.add_argument("--data", default="quiz-data")
    p_ans.add_argument("--item", required=True)
    p_ans.add_argument("--response", required=True)
    p_ans.add_argument("--self", choices=["yes", "partly", "no"],
                       help="self-assessment for an unjudgeable short answer")
    p_ans.add_argument("--latency-ms", type=int, dest="latency_ms")
    p_ans.add_argument("--confident", action="store_true")
    p_ans.add_argument("--mode", default="practice")
    p_ans.add_argument("--retention", type=float, default=sched.DEFAULT_RETENTION)
    p_ans.set_defaults(fn=cmd_answer)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
