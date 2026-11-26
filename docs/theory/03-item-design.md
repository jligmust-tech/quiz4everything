# 03 — Item design

How to write an item that tests the thing the section actually teaches, and how
to reject the ones that don't. This file is the spec the generation skill and
the QA gate both implement.

---

## 1. Item types and when to use each

| Type | Retrieval demand | Guess floor | Best for | Avoid when |
|---|---|---|---|---|
| `mcq` (3 options) | recognition + discrimination | 33% | definitions, distinctions, "which is NOT", numeric facts with plausible neighbours | the concept has no natural set of confusable alternatives |
| `cloze` (delete-a-term) | cued production | ~0% | terminology, named entities, formulas, causally central terms | the blank is guessable from grammar |
| `short_answer` | free production | 0% | mechanisms, "explain why", procedures, comparisons | the source gives no canonical phrasing and grading is ambiguous |
| `true_false` | recognition (weakest) | 50% | quick calibration, misconceptions (present the misconception as the statement) | used as the only format — too weak |
| `ordering` / `matching` | relational | low | processes, sequences, taxonomies with ≥4 members | fewer than 4 members (becomes guessable) |
| `numeric` | production with tolerance | 0% | quantities, thresholds, effect sizes | unit ambiguity is unresolved |

Design intent: **at least one production type and one recognition type per
section** (DR-14). True/false is never the majority.

### Why 3 options for MCQ (DR-12)
Rodriguez (2005), meta-analysing 80 years / 56 studies: item discrimination and
test reliability are essentially unchanged going from 3 to 4 or 5 options, most
4th/5th options are chosen by <5% of examinees, and 3-option items let you fit
more items in the same time — which improves content coverage. For a
self-study tool the coverage argument dominates.

Consequence: the hard part of MCQ writing is not the number of options, it is
making **two** distractors that are genuinely tempting. If you cannot write two
plausible distractors, the item is probably a cloze item in disguise.

---

## 2. What a good stem does

1. **Asks one thing.** One interrogative, one blank, one decision.
2. **Is answerable from the cited span** without outside knowledge, unless the
   item is explicitly an application item (then the *rule* must be in the span).
3. **Does not leak the answer** through grammar, length, or article agreement
   ("a ___" excludes options starting with vowels).
4. **Uses the source's terminology**, not a paraphrase that quietly changes the
   claim. If the source says "correlational", the stem must not say "causes".
5. **Tests the load-bearing idea**, not a number that happens to appear on the
   page. Preference order: mechanism > distinction > procedure > definition >
   isolated fact > figure caption.

### Bloom-ish levels — how we tag them

| Level | Tag | What it requires | Generation strategy |
|---|---|---|---|
| Remember | `L1` | recall a stated fact/term | cloze or direct MCQ, span = the sentence |
| Understand | `L2` | explain, paraphrase, classify | short answer; MCQ on "which example is an instance of X" |
| Apply | `L3` | use a rule on a new case | stem supplies a novel scenario, key requires the span's rule |
| Analyze | `L4` | compare, distinguish, find the flaw | MCQ with a "which is the key difference" stem, or "which claim is inconsistent with the passage" |

**Rule:** a section bank should not be >60% `L1`. `L1` items feel productive and
inflate scores; `L3/L4` items are where transfer lives (Pan & Rickard 2018).
This is a design choice `[?]` anchored in the transfer literature.

---

## 3. Distractors

A distractor is a **diagnostic hypothesis about a misconception**. Good
distractor sources, in order:

1. **A neighbouring concept in the same document** that the section explicitly
   distinguishes ("mitosis vs meiosis", "precision vs recall").
2. **The reversed relation** — if the key is "A increases B", a distractor is
   "B increases A".
3. **A correct statement about a different thing** — true in the domain, wrong
   for this stem.
4. **A common real-world misconception** in the field — only if it appears in or
   is contradicted by the source.
5. **A plausible but wrong quantity** — off by an order of magnitude or by a
   unit, not by ±2%.

Never:
- a distractor that is absurd or jokey;
- a distractor that is subtly *also* correct (the absolute worst failure — see
  DR-10);
- a distractor that is longer/more detailed than the key (length cue);
- "all/none of the above";
- a distractor copied verbatim from a different section as if it belonged here.

**Test for a distractor:** can you write one sentence, drawn from the source,
explaining why a smart learner would pick it? If not, it is filler.

---

## 4. The answer key

- Exactly one defensible key.
- The key is **the same length and grammatical shape** as the distractors.
- The key's justification is a **verbatim span**, not a paraphrase.
- If the source is ambiguous or contradicts itself, **drop the item** and log it.
  Ambiguity is information about the document, not something to paper over.
- Numeric keys store value + unit + tolerance, never a formatted string.

---

## 5. Explanations

Required fields per item:

```
explanation_correct   why the key is right, citing the span
explanation_wrong[]   one entry per distractor: the misconception it encodes
takeaway              one sentence the learner should retain
source_span           {page, quote, offsets}
```

The explanation must answer "why is the other option tempting and where does
that reasoning break?" — that is the elaborative-feedback mechanism
(Pan & Rickard: +0.23 on transfer). A one-line "B is correct" is not feedback.

---

## 6. Acceptance checklist (the QA gate)

Machine-checkable, run on every generated item. Any failure = reject or repair.

| # | Check | On fail |
|---|---|---|
| 1 | `source_span` found verbatim in the parsed section | reject |
| 2 | key present in options, exactly once | reject |
| 3 | option count == 3 for MCQ; no duplicate/near-duplicate options | reject |
| 4 | stem and key not both containing the answer term for cloze | regenerate |
| 5 | options within ±40% character length of each other | regenerate |
| 6 | no "all/none of the above", no double negation | regenerate |
| 7 | item answerable from `source_span` alone (adversarial check) | reject |
| 8 | no second defensible key (adversarial check) | reject |
| 9 | difficulty estimate in 0.4–0.95 success band | re-tag |
| 10 | not a near-duplicate of another item in the bank (embedding sim < 0.9) | drop |
| 11 | language matches document language | reject |
| 12 | `takeaway` and all explanations non-empty and >15 chars | reject |

The adversarial checks (7, 8) are a separate model call with the instruction
"find a reason this item is unfair, ambiguous, or has a second correct answer".
Cheap, and it catches the failure mode that matters most.

---

## 7. Bad → good examples

### Example A — leaking, single-option-reasonable MCQ (bad)

> **Stem:** Which neurotransmitter is most associated with Parkinson's disease?
> A. Dopamine B. Serotonin C. Acetylcholine
>
> *Problems:* pure `L1` recall; no span cited; "most associated" is vague;
> distractor set is a generic list of neurotransmitters not tied to the passage.

**Better:**
> **Stem:** In the passage's model, loss of dopaminergic neurons in the substantia
> nigra produces tremor because…
> A. the basal ganglia receive reduced inhibitory input, releasing the thalamus
> B. striatal GABAergic neurons degenerate first, silencing the thalamus
> C. cortical motor areas lose their direct dopaminergic innervation
>
> *Why better:* `L2/L3`; requires the mechanism, not the name; each distractor is
> a specific alternative mechanism that a learner could plausibly construct; span
> = the mechanism paragraph.

### Example B — distractor that is accidentally true (bad, and dangerous)

> **Stem:** Which statement about the testing effect is supported by Rowland (2014)?
> A. Feedback increases the effect
> B. Testing is more effective than restudying
> C. Longer retention intervals reduce the effect
>
> *Problems:* A and B are both true; C is arguably true as stated (the *effect
> size* is larger at longer intervals — the wording is ambiguous). Unanswerable.

**Better:** make the stem a single precise claim:
> **Stem:** In Rowland's (2014) meta-analysis, the mean effect of testing versus
> restudying on retention was closest to which value?
> A. g = 0.20 B. g = 0.50 C. g = 0.90
>
> *Why better:* one fact, one key, numeric distractors chosen at plausible
> magnitudes, unambiguous.

### Example C — cloze that is guessable (bad)

> "The mitochondria is the ______ of the cell."
>
> *Problems:* "powerhouse" is famous; also article/idiom cues.

**Better:**
> "In the passage's account, ATP synthesis depends on a proton gradient across
> the ______ membrane."
> *Why better:* requires the specific structural term (inner mitochondrial),
> not a slogan.

---

## 8. Language and style

- Items follow the **document's language**; terminology stays in the source's
  language even if the UI is in another. `[?]`
- Second person, plain tense, no "the author states that…" padding.
- No item that depends on remembering a page number, figure number, or the
  author's name, unless the section is *about* citation practice.
- Math: LaTeX inline, rendered; numeric items declare units.

## 9. Item metadata (contract)

```jsonc
{
  "id": "q-<section>-<n>",
  "type": "mcq|cloze|short_answer|true_false|ordering|numeric",
  "level": "L1|L2|L3|L4",
  "topic": "sub-topic label from the outline",
  "stem": "...",
  "options": ["...", "...", "..."],        // MCQ/TF only
  "key": "B",                               // or value+tolerance for numeric
  "distractor_rationale": {                 // one per wrong option
    "A": "confuses X with Y (span: ...)"
  },
  "explanation_correct": "...",
  "takeaway": "...",
  "source_span": {"page": 4, "quote": "...", "start": 1203, "end": 1580},
  "est_difficulty": 0.72,                   // predicted P(correct) first exposure
  "language": "en",
  "provenance": {"model": "...", "prompt_version": "...", "generated_at": "..."}
}
```

`provenance` is non-negotiable: when an item is later found to be wrong we need
to know which prompt version produced the whole class of errors.
