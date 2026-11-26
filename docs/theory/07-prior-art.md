# 07 — Prior art in this repo: `learning-quiz-bank.zip`

A previous attempt at the same problem, shipped as an agent skill. Reviewing it
is useful because it got the happy path right and the hard parts missing. Note:
the zip is currently in the repo root and is **not** committed as source — see
the note at the end.

---

## What it is

`learning-quiz-bank/SKILL.md` + `references/quiz-bank-schema.md` +
`references/prompt-templates.md`. A skill that shells out to a Windows-local
webapp:

```
python F:\workspace\learningHelper\webapp\backend\generate_bank.py "<material>" \
    --num N --difficulty basic|advanced|mixed [--focus "..."] [--title "..."]
```

Output: a JSON bank in `F:\workspace\learningHelper\webapp\data\banks\`, then the
user opens `http://localhost:8765` and imports it.

## What it got right

1. **A schema as the single contract** between generator and consumer. The bank
   object is explicitly "the only contract" and the skill is told to validate
   against it. That instinct is correct and is carried forward (03 §9).
2. **The 8-rule system prompt**: only-from-material, language follows material,
   MCQ + true/false, plausible distractors, ~50/50 true-false balance, basic vs
   advanced, even coverage, respect focus. These are the right *categories*.
3. **Deterministic `study_prompt` assembly.** Rather than trusting the model to
   produce a self-contained explanation prompt, Python re-builds it from the
   structured fields, embedding stem, key, explanation and source excerpt. That
   is a good pattern: **don't let the model be responsible for a field the code
   can guarantee.**
4. **An explicit pitfall list** in the skill: don't fabricate, retry once on LLM
   failure, halve `--num` if the JSON is truncated. Recognising that truncation
   and fabrication are the two real failure modes.
5. **Language detection heuristic** (CJK ratio > 30% over first 2000 chars) —
   crude but adequate, and documented.

## What is missing or wrong

| Gap | Consequence | Where we address it |
|---|---|---|
| **No span verification.** `source_ref` is a quote the model *writes*, never checked against the parsed document. | The single highest-risk failure — fabricated or drifted quotes — is unguarded. The skill says "spot-check a few", which does not scale. | DR-8, QA gate pass 2 (05 §Stage 4) |
| **No adversarial check for a second correct answer.** | The "accidentally true distractor" bug ships silently and actively teaches wrong things. | DR-9/DR-10, QA gate pass 3 |
| **No scheduling.** The artefact is a static bank; nothing brings an item back. | Loses the largest moderator (Rowland: ≥1 day 0.69 vs <1 day 0.41) and the whole spacing literature. | DR-21, 04 |
| **No feedback design.** `explanation` is "1–3 sentences"; there is no per-distractor rationale, no elaborative feedback. | Gives up ~+0.34 (Rowland 0.73 vs 0.39) and ~+0.23 transfer (Pan & Rickard). | DR-4/DR-5, 03 §5 |
| **No concept layer**, only `topic` free text. | Mastery and coverage are unmeasurable. | 05 data model, Q4 |
| **No difficulty calibration.** "basic/advanced" is a label the model assigns; no `p_value`, no target success band. | Items drift; a bank can be uniformly trivial or uniformly unfair and nothing notices. | DR-17, 04 §5 |
| **4-option MCQ default** in the schema example. | Slightly worse coverage per unit time; 4th option usually non-functional. | DR-12 (3 options) |
| **True/false as a first-class, ~50% of the bank.** | Weakest retrieval format, 50% guess floor, inflates apparent mastery. | 03 §1 (TF never the majority) |
| **Hard-coded Windows path inside the skill.** | Not portable; the skill cannot run anywhere else. | 05 (skill packaging) |
| **Truncates material at 40,000 chars** with a note. | Silently quizzes a fragment while presenting it as the document. | 05 (no silent truncation) |
| **Validation is "read it and check the schema"** — a human step, described and then trusted. | Will be skipped. | 05 Stage 4 (deterministic gate) |
| **No provenance.** No prompt version, model id, or generation timestamp per item. | Cannot trace a class of errors back to a prompt change. | 03 §9 `provenance` |

## The deeper critique

The prior art is a **question generator**, not a **learning system**. It answers
"can I get 10 questions out of this PDF?" — a demo question. The evidence base
says the learning comes from: retrieval *effort*, *feedback that explains*,
*delay*, and *repetition*. A static bank of questions with 1–3-sentence answers
exercises one of the four mechanisms and, worse, gives the learner a number that
looks like an outcome measure. Everything in 02–05 exists to close that gap.

Two specific things to keep from it, though: the schema-as-contract pattern, and
the "code assembles the field, not the model" pattern.

---

## Repo hygiene note

`learning-quiz-bank.zip` is untracked in the repo root and `.gitignore`d. It
should not be committed as a binary.

Resolved: the zip's useful content has been absorbed into
`skills/quiz4everything/` as a working implementation — the schema became
`references/item-schema.md` (extended), the prompt templates became
`references/item-generation.md` (with the gaps in this document closed by
`scripts/verify.py`). The zip itself is now redundant and can be deleted without
loss.

Kept as documentation of what was reviewed, and of which specific gaps were
judged worth closing, since that reasoning is not recoverable from the final
files.
