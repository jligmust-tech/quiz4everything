# quiz4everything — theory & design notes

**Status: v0.1 — theory only.** No implementation yet. This folder is the evidence
base that the question-generation skills will be built on.

## The product loop we are designing for

```
PDF / reading material
        │  (1) parse + segment
        ▼
   Section outline  ──► user picks ONE section
        │  (2) generate
        ▼
   Item bank for that section          (questions + answers + explanations + source spans)
        │  (3) practice
        ▼
   Testing & learning session          (retrieve → feedback → explain → re-ask later)
        │  (4) track
        ▼
   Mastery state per topic ──► next session / review queue
```

Two things are **not yet decided** and are deliberately left open
(see [06-open-questions.md](06-open-questions.md)): the exact testing
protocol the user has in mind, and the delivery surface (web app / CLI / agent skill).

## Documents

| File | What it covers |
|---|---|
| [01-evidence-base.md](01-evidence-base.md) | What the testing / retrieval-practice literature actually says, with effect sizes and their limits |
| [02-design-rules.md](02-design-rules.md) | Design rules `DR-*` derived from the evidence, each traceable to a citation |
| [03-item-design.md](03-item-design.md) | Item formats, stems, distractors, answer keys, acceptance checklist, bad→good examples |
| [04-schedule-and-mastery.md](04-schedule-and-mastery.md) | Spacing, FSRS/DSR, target success rate, mastery definition, item statistics |
| [05-pipeline.md](05-pipeline.md) | PDF → outline → items → session: stages, artifacts, QA gates, data model |
| [06-open-questions.md](06-open-questions.md) | Decisions needed, assumptions to test, experiment backlog |
| [07-prior-art.md](07-prior-art.md) | Review of the bundled `learning-quiz-bank.zip` (an earlier MCQ/TF generator) and the gap |
| [evidence.csv](evidence.csv) | Machine-readable effect sizes with provenance |

## One-paragraph summary

Retrieving information from memory produces better long-term retention than
spending the same time re-reading it. The effect is large enough to matter
(Hedges' *g* ≈ 0.50 lab, ≈ 0.50 classroom, and ≈ 0.51–0.70 depending on the
control condition), it grows with retention interval, it is much larger when
corrective feedback is given, and it transfers to *new* questions only partly
(*d* ≈ 0.40, and weaker without format/answer overlap). Learners systematically
under-use it because re-reading feels more productive. Therefore a PDF-to-quiz
tool is not a convenience feature — it is an intervention against a known
metacognitive bias. The design rules in `02-design-rules.md` exist to keep the
tool on the right side of the moderators that make the effect large rather than
small.

## Conventions used in these docs

- `DR-n` = design rule (testable requirement).
- `[E]` = supported by meta-analytic or multi-study evidence.
- `[W]` = weak / single-study / indirect evidence — treat as a hypothesis.
- `[?]` = our own judgement, not from the literature.
- Effect sizes are Hedges' *g* unless stated. Rough reading: 0.2 small, 0.5 medium, 0.8 large.

## License

Apache-2.0 (see `../LICENSE`).
