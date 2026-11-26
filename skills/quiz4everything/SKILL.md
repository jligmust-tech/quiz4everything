---
name: quiz4everything
description: Turn a PDF, markdown, or text document into a verified quiz bank, then run retrieval practice and spaced review on it. Use when the user wants to make questions from study material, practise retrieval, drill what they got wrong, or review on a schedule. Triggers - "make a quiz from this PDF", "make practice questions", "quiz me on this", "review what I missed", "spaced repetition", and Chinese triggers 出题, 做题, 复习, 测一下我, 帮我出练习题, 从我上传的文档出题.
license: Apache-2.0
compatibility: Requires Python 3.10+. PDF input additionally needs pypdf (pip install pypdf) or poppler's pdftotext on PATH; markdown and text input need neither. No network access beyond the model you are already running in; no API keys, no server, no database.
metadata:
  version: "1.0"
  audience: learners
  workflow: local-first
---

# quiz4everything

Reading material in, retrieval practice out.

The point is not to produce questions. The point is to make the learner
retrieve, get feedback that explains, and come back days later. Everything below
serves that, and the non-negotiables are the ones the evidence actually supports.

## Running the scripts

All four scripts are plain Python with no third-party dependency except optional
PDF extraction. Invoke them the same way from any agent:

```bash
python3 scripts/ingest.py ...      # macOS / Linux
python  scripts/ingest.py ...      # Windows (python3 may not exist)
```

Two rules that apply to every command in this file:

- **Quote paths that contain spaces.** On Windows, `C:\Users\me\My Documents\a.pdf`
  must be `"C:\Users\me\My Documents\a.pdf"`.
- **Trust the exit code, not the wording.** 0 success, 1 rejection or nothing due
  or unreadable input, 2 bad arguments, 3 needs a human decision.

Scripts resolve their own directory, so they work from any working directory.
`session.py` and `_console.py` are imported by path; keep `scripts/` intact.

## Pipeline

Six stages. Stages 1, 4 and 6 are deterministic Python — never hand those to a
model. Stages 2, 3 and 5 involve judgement.

```
ingest.py  →  outline  →  generate  →  verify.py  →  session.py  →  schedule.py
 (script)      (model)     (model)      (script)      (script)       (script)
```

Data lives in one directory, default `quiz-data/`:

```
quiz-data/
  document.json     stage 1 output: full text, pages, section offsets
  banks/*.json      accepted banks, one per section generated
  events.jsonl      source of truth: one line per review
```

`events.jsonl` is append-only. All scheduler state is recomputed from it, so the
learner's history cannot be corrupted by a stale cache file.

## Ask the learner first

Before the first bank of a new project, ask one question:

> Do you want a local web page as the front end as well, or is practising inside
> this chat enough?

Ask it once per `quiz-data` directory — the moment `banks/` is absent or empty.
Do not re-ask if the learner already answered in this conversation, and never
block practice on the answer. The default if they shrug is chat-only.

Why it is asked rather than assumed: the design depends on the learner coming
back days later, and every step of friction between sessions reduces that. A page
they can open without starting an agent is genuinely lower cost. But it is also
real work, and it is not this skill's job to assume it.

| answer | what to do |
|---|---|
| chat only | the normal path in this file. Nothing to install. |
| local page | **It does not exist yet.** Say so plainly. Do not improvise a UI, do not start a server, do not scaffold a webapp — the scripts are file-based by design. Note the request and continue with chat practice. |
| both | practise in chat now, and record that the learner wants a page, so it is not lost. |

Being straight about this matters more than being helpful: a learner told "yes,
there's a web UI" will go looking for one that is not there, and conclude the
tool is broken rather than unfinished.

## Workflow

### 1. Ingest

```bash
python3 scripts/ingest.py <document.pdf|.md|.txt> --out document.json
python3 scripts/ingest.py <doc> --stats        # section table only
```

Exit 1 means the input could not be read (missing file, unsupported extension,
encrypted or scanned PDF with no text). The message on stderr says which. Do not
improvise text extraction if this fails — report it.

Read the printed warnings. They are load-bearing:

| warning | what to do |
|---|---|
| `front matter` / `reference/index section` | never generate items for it |
| `short section (<80 words)` | at most 1–2 items, or skip |
| `long section (>4000 words)` | split at sub-headings before generating |
| `low heading confidence` | verify the section boundaries yourself |
| `truncated at --max-pages N` | tell the user coverage stops at page N |
| `no headings detected` | one section; propose a split before generating |

Then show the learner the section table and **wait for them to pick one**.
Sections are the unit of choice. Do not generate for the whole document.

### 2. Generate

Use `references/item-generation.md` as the task contract and
`references/item-schema.md` for the exact JSON. Write one file per section,
e.g. `bank-s1.json`.

The governing rule, which overrides every count the user asks for:

> Emit fewer items rather than invent one. If the section supports four honest
> items and the user asked for eight, deliver four and say why.

Record `shortfall_reason` when you do this. A silently short bank is a bug; an
explained short bank is correct behaviour.

### 3. Verify — mandatory, not advisory

```bash
python3 scripts/verify.py --doc document.json --bank bank-s1.json \
  --report qa.json --adversarial-out adv.json
```

Exit 0 means every item passed the deterministic gate. Exit 1 means at least one
item was rejected — **delete or fix those items, then re-run**. Never ship a
rejected item because it looked good.

Then run the adversarial pass: `adv.json` holds one prompt per surviving item.
Send each to a model, collect the JSON verdict, and drop any item with
`verdict: reject` or a `second_key` other than `none`. Repairing is allowed once
for structural faults; a second defensible answer means drop, not patch.

Report the quality summary to the learner: how many generated, how many passed,
what was dropped and why. Never a silent drop.

### 4. Practice

```bash
# agent-driven (this is the normal path inside a chat)
python3 scripts/session.py init --data quiz-data --doc document.json
python3 scripts/session.py add  --data quiz-data --bank bank-s1.json
python3 scripts/session.py practice --data quiz-data --section s1 --max 8 --json
```

`practice --json` returns the queue and records nothing. Ask the learner each
item, then record each answer:

```bash
python3 scripts/session.py answer --data quiz-data --item q3 --response B \
  --latency-ms 8000 [--confident]
```

`answer` prints the graded result plus the feedback payload: the correct answer,
`why`, per-distractor rationales (only on a miss), `keep`, and the verbatim
`source` excerpt. Render all of it. The explanation is the treatment, not a
nicety.

Exit 3 with `needs_self_assessment` means the deterministic grader could not
judge a short answer. Show the model answer and ask the learner yes/partly/no,
then re-run with `--self yes|partly|no`. A correct production answer must never
be silently marked wrong.

Only when the learner is at a real terminal, use `practice` without `--json`
for the interactive TTY loop, which also re-asks missed items. Without a TTY it
exits 3 and tells you to use `--json`; it never pretends the learner quit.

### 5. Review

```bash
python3 scripts/session.py review --data quiz-data --json     # due items only
python3 scripts/session.py stats  --data quiz-data            # honest report
```

`review` with nothing due exits 1 and says when the next item lands. Say that,
rather than inventing something to do.

### 6. Report

`stats` reports concepts, not items, and separates observed from
guess-corrected accuracy. Use its numbers verbatim. Never restate them as "you
know 80% of this".

## Invariants

These are not style preferences.

1. **Feedback after the attempt.** Never show the answer, or any hint that
   discriminates it, before the learner responds (DR-6, DR-23).
2. **Every item has a verbatim source span** that really exists in the declared
   section. `verify.py` proves this; do not trust your own reading.
3. **Three options for MCQ**, one key, no "all of the above" (DR-14, 03 §2).
4. **Every distractor has a stated reason someone would pick it.** A distractor
   that is merely wrong teaches the wrong thing.
5. **Mixed formats.** A bank of only MCQ is rejected by the verifier: recognition
   overstates knowledge (DR-14).
6. **Concept is the unit of mastery**, not item. Every item carries `concept_id`.
7. **Never claim mastery from one session.** Today's result is a diagnostic. The
   word "learned" requires a correct answer after at least one day (DR-28).
8. **Report wrong items to the learner and retry them**, in-session at a
   terminal, next session otherwise (DR-20, DR-22).
9. **No streaks, badges, or item counts as a goal.** Volume gamification
   increases activity and degrades learning (DR-30).
10. **Local only.** No network calls except the model you are already using. No
    API keys in files. No learner data leaves the machine.
11. **Never claim a web front end exists.** It does not. If the learner asks for
    one, say so and continue with chat practice; do not scaffold a UI or start a
    server to seem responsive.

## Do not hand these to a model

Deterministic, and it matters that they are:

- text extraction and section offsets (`ingest.py`)
- span verification, option counts, key presence, duplicate and coverage checks
  (`verify.py`)
- intervals, stability, difficulty, ratings, due dates (`schedule.py`)
- grading of closed formats (`session.py`)
- mastery levels and guess correction (`session.py stats`)

A model may *write* items and *judge* whether a second answer is defensible.
It may not decide whether its own span exists.

## Reference files

- `references/item-generation.md` — the generation contract, level mix, the
  "emit fewer" rule, and what to do with a thin section.
- `references/item-schema.md` — exact JSON for a bank and an item, with every
  field the verifier checks.
- `references/item-quality.md` — distractor construction, stem traps, worked
  bad→good examples.
- `references/scheduling.md` — how ratings are derived and what the intervals
  mean, for when the learner asks why an item came back today.
- `../../docs/theory/` — the evidence base and the reasoning behind every rule
  cited above as DR-*. Present in the repository copy of this skill; if the skill
  is installed standalone, read `01-evidence-base.md` and
  `02-design-rules.md` from the repo instead.

## Failure modes worth naming

- **Generating from a table, figure, or caption.** The extractor gives you
  linear text; a table's meaning is in its layout. Skip it and note the omission.
- **A section that is one long argument.** Items become restatements of the
  thesis. Ask for sub-headings, or generate 3 items instead of 8.
- **The learner asks for a bank of 30 from a 300-word section.** Refuse with the
  reason, not with a shrug. That bank would be fabricated.
- **Short-answer grading.** If unsure, escalate. False negatives teach the
  learner that correct answers are wrong, which is worse than not grading.
