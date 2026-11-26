# Item generation contract

You are writing practice items for **one section** of a document. You have the
section text and its `section_id`. Produce a bank JSON file.

Everything here is a constraint, not a suggestion. `verify.py` enforces most of
it mechanically and will reject items that break it.

## The one rule that overrides the others

> **Emit fewer items rather than invent one.**

There is no target count that justifies a fabricated question. If the section
supports four honest items, deliver four. Write the reason in
`shortfall_reason`:

```json
"shortfall_reason": "Section is 240 words of definition; 4 items cover it without repetition."
```

Being short and honest is correct. Being short and silent is a bug.

## Step 1 — Find the concepts first

Before writing items, extract **2–4 concepts** from the section. A concept is a
thing that can be known or not known: "retrievability is a probability", "the
testing effect grows with delay", "difficulty is proportion correct".

Concepts are the unit of mastery, so this step is not bookkeeping. Write them
down with ids:

```json
"concepts": [
  {"id": "c1", "name": "Retrievability as probability", "span_hint": "Retrievability is the probability of recall..."}
]
```

Then attach items to concepts. Two or three items per concept is right for a
concept that matters; one is acceptable. Ten items on one concept wastes the
learner's session.

If the section contains no distinguishable concepts — it is a table of contents,
a list of references, an acknowledgements page — generate **zero** items and say
so.

## Step 2 — Assign levels, honestly

| level | asks the learner to | example |
|---|---|---|
| `L1` | recall a stated fact | "What does FSRS stand for?" |
| `L2` | explain or paraphrase | "Why does spacing beat massing?" |
| `L3` | apply to a new case | "A learner reviews at R=0.95. What does FSRS predict?" |
| `L4` | discriminate or integrate | "Which of these two claims does the passage support?" |

Target mix for a bank of 6–10 items: **at most 60% L1**, at least one L3 or L4.
`verify.py` warns above 60% L1 and rejects a bank with no production format.

Each section in `document.json` carries `est_items` (roughly one item per 90
words of prose). Treat it as a starting point, not a target: a dense definitional
paragraph supports more items than its word count suggests, and an airy
narrative supports fewer. The span requirement decides, not the estimate.

Do not label a paraphrase `L3` to improve the mix. The level is a claim about
what the learner must do.

## Step 3 — Choose formats

| type | guess floor | use when |
|---|---|---|
| `mcq` | 1/3 | discriminating between close alternatives |
| `cloze` | ~0 | a term or value must be produced from context |
| `short_answer` | 0 | an explanation, in the learner's words |
| `true_false` | 1/2 | a specific claim is right or wrong |
| `numeric` | 0 | a number with a unit |
| `ordering` | varies | a process has a correct sequence |

Hard limits from the verifier:

- `true_false` ≤ 34% of the bank. Its 50% guess floor inflates apparent mastery.
- No bank may be 100% `mcq`.
- At least one of `cloze`, `short_answer`, `numeric` must be present.
- No single topic may exceed 30% of the bank.

A comfortable bank of 8: 4 mcq, 2 cloze, 1 short_answer, 1 true_false. Adjust to
what the section actually supports — a definitional section does not need a
numeric item, and you should not manufacture one.

## Step 4 — Write the span first, then the item

This order prevents the most common failure. Take a **verbatim quote of 40+
characters** from the section that contains the fact the item tests. Then write
the item so that the quote is sufficient to answer it.

Do not write the item and then hunt for supporting text. That is how invented
items happen.

The span must:

- be copied exactly, character for character, from `document.json`
- sit inside the declared `section_id`
- be at least 40 characters
- be enough, on its own, to answer the item

## Step 5 — Fill every field

See `references/item-schema.md` for the exact shape. Every item needs:

`id`, `type`, `level`, `topic`, `concept_id`, `section_id`, `stem`,
`source_span{quote,page}`, `key`, `explanation_correct`, `takeaway`,
`est_difficulty`, `language`, `provenance`, and for MCQ
`distractor_rationale`.

Missing `provenance`, `concept_id` or `est_difficulty` produces warnings that
degrade the bank's usefulness later. Fill them.

## Step 6 — Self-check before running the verifier

Read each item and ask:

1. Could someone answer it **without** the section? Then it is trivia or prior
   knowledge — drop it.
2. Could someone answer it from the **stem alone**? Then the answer is cued —
   rewrite it.
3. Is there a second defensible answer? Then it is broken — fix or drop.
4. Does the explanation say **why**, or only restate the answer? Restating is
   not feedback.
5. For each distractor: what belief makes it attractive? If you cannot say,
   replace it.

The verifier catches mechanics. It cannot catch a question that is technically
valid and teaches nothing.

## Language

All item text follows the document's language. `document.json` carries `lang`
(`en` or `zh`) and the verifier rejects mismatches. Do not translate a Chinese
source into English items, and do not mix scripts inside one item.

## What a thin section looks like

**300-word empirical abstract, user asked for 12 items.**

Deliver 4–5. Write:

```json
"shortfall_reason": "Abstract states one finding and its effect size. 5 items cover the finding, the method, the population, the effect size, and the caveat; further items would test the same point twice or invent detail."
```

**A section that is entirely a figure caption or a table.**

Deliver 0. Write:

```json
"shortfall_reason": "Section is a table; the extractor returns linear text that does not preserve row/column relationships. Items here would test layout guessing."
```

Neither of these is a failure. Silently padding them would be.
