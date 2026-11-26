# 05 — Pipeline: PDF → outline → items → session

This is the system shape implied by the design rules. Nothing here is built yet;
it is the contract the skill(s) will implement.

```
┌──────────┐   ┌───────────┐   ┌──────────────┐   ┌───────────┐   ┌───────────┐
│ 1 ingest │──►│ 2 section │──►│ 3 generate   │──►│ 4 QA gate │──►│ 5 practice│
│  parse   │   │  outline  │   │  items       │   │  validate │   │  session  │
└──────────┘   └───────────┘   └──────────────┘   └───────────┘   └───────────┘
                     │                                    │              │
                     ▼                                    ▼              ▼
              user picks ONE                        reject/repair    events log
                 section                              loop           (reviews)
                                                                         │
                                                                ┌────────▼────────┐
                                                                │ 6 scheduler     │
                                                                │ due items       │
                                                                └─────────────────┘
```

---

## Stage 1 — Ingest

**Input:** PDF (also txt/md). **Output:** a normalized document with page
anchors and stable character offsets.

Requirements:
- Preserve page numbers; every downstream quote must resolve to `(page, start, end)`.
- Detect two-column layouts, tables, and figures; do not silently interleave
  columns (the most common PDF-parsing failure and a common source of
  nonsensical items).
- Figure/table content is *not* usable as a source span unless a caption
  states the claim in text. An item that requires reading a chart cannot be
  validated by our QA gate, so exclude figure-dependent items by default.
- OCR fallback for scanned PDFs, flagged as `low_confidence` so the QA gate can
  be stricter (verbatim span matching will be fuzzy).
- Store the raw text once; all spans index into it.

**Failure modes to handle explicitly:** encrypted PDFs, >200-page documents
(chunk, do not truncate silently), non-UTF8 text, RTL scripts, poor OCR.

---

## Stage 2 — Section outline

**Output:** ordered list of sections, each with `title`, `page_range`,
`char_range`, `sub_topics[]`, `est_items` — then the user picks **one**.

Rules:
- Prefer the document's own headings. Only fall back to LLM segmentation when
  headings are absent or unreliable (DR-31).
- Sections must be **self-contained enough to quiz on**: a section of 80 words
  yields 1–2 items and is not worth a session; a 40-page chapter is too big for
  one session and should be split at sub-headings.
- Show the user page ranges and a one-line summary per section. The pick must be
  informed — a user choosing "Chapter 3" blind is a user who will get items from
  Chapter 3 they didn't want.
- Report `est_items` so the user can right-size ("this section supports ~12
  items; want 8?").

**Reject** (or flag) a section that is: a table of contents, a reference list,
front matter, an index, or pure figures. Generating items from a citation list
is a classic LLM failure.

---

## Stage 3 — Item generation

Inputs: one section's text, the section's sub-topics, the requested count, the
difficulty mix, the target format, the language.

Procedure (per section):
1. Extract **candidate concepts**: the load-bearing claims, definitions,
   distinctions, mechanisms, quantities. Keep the source span for each. Aim for
   ~2–3 concepts per item requested so there is something to reject.
2. Assign each concept a target level (`L1`–`L4`) per §2 of 03-item-design.
3. For each concept, draft an item in a format appropriate to it (§1 of 03).
4. Emit the full metadata contract (§9 of 03), including per-distractor rationale
   and `est_difficulty`.
5. Batch to the QA gate.

**Hard constraints on the generator prompt:**
- Only claims present in the supplied section text; no outside knowledge.
- Every item carries a verbatim `source_span`.
- Distractors: one per named misconception, no accidental truths.
- Faithful to hedging in the source ("associated with" must not become "causes").
- If the section does not support an item of the requested level, say so and emit
  fewer items — **do not invent**. Under-delivery is a valid outcome; padding is
  not.

That last rule is the one that separates a usable tool from a plausible-looking
one. Make it explicit in the prompt and enforce it in the schema
(`items.length` may be < requested, with a `shortfall_reason`).

---

## Stage 4 — QA gate

Three passes, cheapest first:

1. **Schema/structural** — the 12 checks in §6 of 03-item-design. Deterministic,
   no model call.
2. **Span verification** — exact/fuzzy match of `source_span.quote` against the
   parsed document at the recorded offsets. Failure = reject. No exceptions,
   including for `low_confidence` OCR (then require fuzzy ≥ 0.9 similarity).
3. **Adversarial review** — a separate model call per item: "is this item
   ambiguous, unfair, unanswerable from the span, or does it have a second
   defensible answer? Quote the span that would make another option correct."
   Reject on any hit.

Repair loop: structural failures → regenerate once with the failure reason
appended; adversarial failures → drop (not regenerate, to avoid burning budget
on a concept that may not be item-able).

**Bank-level checks** after per-item QA:
- Coverage: no sub-topic >30% of items (DR-32) unless focus was requested.
- Level mix: `L1` ≤ 60%.
- Format mix: ≥1 production and ≥1 recognition item (DR-14).
- Duplicate/near-duplicate detection across the bank.
- Diversity of keys: correct answer spread roughly evenly across A/B/C.

Ship the bank with a **quality summary**: how many requested, how many passed,
why the rest failed. Never silently drop.

---

## Stage 5 — Practice session

Per item: present → commit answer → reveal key + explanation + source excerpt →
record `(item, correct, latency, rating, format)`.

Rules from 02:
- Feedback always, after the attempt (DR-4, DR-6).
- Missed items re-asked once, separated by other items (DR-2x).
- No answer key visible before attempts (DR-23).
- No score shown mid-session that could be read as "mastery" (DR-13).
- End with calibration + coverage, not a single grade (DR-27, §8 of 04).

**Session sizing:** 8 items ≈ 10–15 min. Cap at ~12 for the first session with a
new section; fatigue degrades both answering and the value of feedback. `[?]`

---

## Stage 6 — Scheduler

Pure function over review history: `next_due(item_state, review_event) → date`.
See 04 §2–3. Keep it side-effect-free and unit-testable; this is the component
most likely to be wrong in subtle ways and the easiest to test.

---

## Data model (minimum)

```jsonc
// Document
{"id","path","pages","lang","parse_confidence","created_at"}

// Section
{"id","doc_id","ordinal","title","page_range","char_range","sub_topics":[],"est_items"}

// Concept            <- the unit of mastery
{"id","section_id","label","source_span","level_target"}

// Item
{"id","concept_id","section_id","type","level","stem","options","key",
 "distractor_rationale","explanation_correct","takeaway","source_span",
 "est_difficulty","language","provenance","qa":{"structural","span","adversarial"},
 "stats":{"p_value","discrimination","distractor_pick_rate","n_attempts"}}

// ReviewEvent
{"id","item_id","learner_id","ts","format","response","correct","latency_ms",
 "rating","scheduled_interval_days","R_at_review"}

// ItemState  (derived, recomputable from events)
{"item_id","S","D","last_review","next_due","lapses"}

// Flag
{"id","item_id","reason","note","ts","resolved"}
```

Two schema decisions worth defending:
- **`ReviewEvent` is the source of truth**; `ItemState` is a cache. Anything you
  might want to recompute (a better scheduler later) must be derivable from
  events. This is what makes swapping in a real FSRS later a non-event.
- **`Concept` is separate from `Item`.** Without it, "mastery" is meaningless and
  coverage is unmeasurable. Items are evidence about a concept; the concept is
  what the learner is supposed to gain.

---

## Skill packaging

The user flow is: *give a PDF → get sections → pick one → get a session*. That
maps onto skills/commands like:

- `quiz ingest <pdf>` → document + outline
- `quiz section <section-id>` → item bank + QA report
- `quiz practice <section-id>` → session
- `quiz review` → due items

These are placeholders. Exact packaging (one skill with subcommands vs several
skills vs a local webapp) is an open question — see 06. The prior art we have
(`learning-quiz-bank.zip`, reviewed in 07) is a single command that does stages
2–3 only, badly, with no QA gate, no scheduling, and a Windows absolute path
hard-coded.

---

## Non-functional requirements

- **Determinism where possible.** Same PDF + same section + same seed → same
  concept list. Item text may vary; concept coverage should not.
- **Cost control.** Stage 3+4 are the expensive part. Cap by section size, and
  make "generate 5 more items for this concept" the cheap top-up path rather than
  regenerating the whole bank.
- **No silent truncation.** If a document exceeds the context budget, say so and
  require the user to pick a section; do not summarise-and-quiz, which produces
  items about the summary.
- **Privacy.** Documents may be unpublished work. Default to local processing,
  no persistence beyond the session unless the user opts in.
- **Escape hatch.** Every auto-generated field is editable by the user, and a
  corrected item is promoted to the bank (human-in-the-loop improves the bank
  over time).
