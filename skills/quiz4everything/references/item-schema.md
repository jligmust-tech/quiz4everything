# Bank and item schema

Exact JSON the scripts read. `verify.py` checks the item fields listed as
*checked*; `session.py` reads the rest at practice time.

## Bank file

```json
{
  "id": "bank-s1-20261126T101500",
  "doc_id": "9f2c1ab3de",
  "section_id": "s1",
  "title": "1.1 Definitions",
  "language": "en",
  "created": "2026-11-26T10:15:00Z",
  "concepts": [
    {"id": "c1", "name": "Retrievability as probability"}
  ],
  "meta": {
    "requested": 8,
    "generated": 6,
    "shortfall_reason": "Section is 240 words of definition; 6 items cover it without repeating a point."
  },
  "provenance": {
    "model": "claude-sonnet-4.5",
    "prompt_version": "item-generation/v1",
    "generated_at": "2026-11-26T10:15:00Z"
  },
  "items": []
}
```

`id` matters: `session.py add` uses it as the stored filename. Re-adding a bank
with the same `id` overwrites it.

Both `items` and `questions` are accepted on read, so the old
`learning-quiz-bank` schema still loads. Emit `items` in new work.

## Item — required fields

| field | type | checked | notes |
|---|---|---|---|
| `id` | string | yes | unique across all banks in `quiz-data` |
| `type` | string | yes | `mcq`, `cloze`, `short_answer`, `true_false`, `numeric`, `ordering` |
| `level` | string | yes | `L1`, `L2`, `L3`, `L4` |
| `topic` | string | yes | ≤30% of the bank per topic |
| `stem` | string | yes | non-empty |
| `source_span` | object | yes | must be an object with `quote` |
| `language` | string | yes | must equal `document.json`'s `lang` |
| `key` | varies | yes | see per-type below |
| `explanation_correct` | string | yes | ≥15 characters |
| `takeaway` | string | yes | ≥15 characters |
| `section_id` | string | warns if unknown | must be a real section |
| `concept_id` | string | warns if missing | without it the item cannot count toward mastery |
| `est_difficulty` | number | warns | expected proportion correct, 0.40–0.95 |
| `provenance` | object | warns | `model`, `prompt_version`, `generated_at` |

## `source_span`

```json
"source_span": {
  "quote": "Retrievability is the probability of recall at a moment in time.",
  "page": 3
}
```

`quote` is verified against the document text, whitespace-insensitively. Exactly
matching text is best; a near match (similarity ≥0.90) passes with a warning;
anything lower is rejected. `page` is a soft check — a mismatch warns.

The quote must also appear **inside the declared section**. A correct quote from
a different section is rejected, because the item would be unanswerable for a
learner who only has that section.

Minimum length 40 characters. Shorter quotes are rejected as unverifiable.

## Per-type structure

### mcq

```json
{
  "type": "mcq",
  "stem": "A learner reviews an item at retrievability 0.95. What does FSRS predict?",
  "options": ["A small stability gain", "A large stability gain", "A certain lapse"],
  "key": "A",
  "distractor_rationale": {
    "B": "reads retention as a measure of need rather than a measure of strength",
    "C": "conflates high retrievability with forgetting"
  }
}
```

- exactly **3** options, in the `A`/`B`/`C` order given
- `key` is one of `A`, `B`, `C` (full option text is tolerated but do not use it)
- no duplicate options, no "all/none of the above"
- option lengths within 40% of each other, or it cues the answer
- `distractor_rationale` must cover **every** non-key option

### true_false

```json
{
  "type": "true_false",
  "stem": "Retrievability increases as time since the last review increases.",
  "options": ["True", "False"],
  "key": "False",
  "distractor_rationale": {"True": "confuses elapsed time with remembered strength"}
}
```

`options` must be exactly `["True", "False"]`, key exactly `True` or `False`.
Cap at 34% of the bank.

### cloze

```json
{
  "type": "cloze",
  "stem": "Spaced repetition exploits the ______ curve.",
  "key": "forgetting",
  "accept": ["the forgetting curve", "forgetting curve"]
}
```

- the stem must contain `___` (three or more underscores)
- the key must **not** appear in the stem
- `accept` is optional and lists answers that should also count as fully correct
- case-insensitive; a substring relationship counts as partial credit

### short_answer

```json
{
  "type": "short_answer",
  "stem": "Why does testing produce better retention than re-reading?",
  "key": "Retrieval strengthens the memory trace and reveals what is not yet retrievable.",
  "rubric": ["retrieval", "strengthens"]
}
```

- `rubric` phrases are checked by substring; all present → correct, some → partly
- with no rubric the grader falls back to token overlap, then asks the learner
- this is the format most likely to need `--self` at practice time, which is
  expected behaviour, not a bug

### numeric

```json
{
  "type": "numeric",
  "stem": "What proportion of a 3-option MCQ is correct by guessing?",
  "key": {"value": 0.333, "unit": "proportion", "tolerance": 0.01}
}
```

`key` must be an object with `value` and `unit`; `tolerance` defaults to 1% of
the value.

### ordering

```json
{
  "type": "ordering",
  "stem": "Put the mastery ladder in ascending order.",
  "key": ["exposure", "attempted", "retained", "stable", "transferred"]
}
```

The learner answers comma- or `>`-separated.

## Explanations

Three fields do the teaching. All are required except `distractor_rationale`,
which is required for MCQ in practice.

```json
{
  "explanation_correct": "Stability grows slowly when retrievability is already high: the memory was not at risk, so there was little to gain.",
  "distractor_rationale": {
    "B": "reads retention as a measure of need rather than a measure of strength"
  },
  "takeaway": "High retrievability means little room for improvement."
}
```

- `explanation_correct` says **why** the key is right, not that it is right
- each `distractor_rationale` names the misconception, phrased to complete
  "would be chosen by someone who …"
- `takeaway` is one sentence the learner could reuse on a different question

Restating the answer is not an explanation. "The answer is A because A is
correct" fails the intent even when it passes the length check.
