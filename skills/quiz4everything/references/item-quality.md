# Item quality

What separates an item that teaches from one that merely scores. `verify.py`
catches the mechanical faults; this file is about the rest.

## The stem

**Ask one thing.** A stem with two questions has no single right answer, and the
learner cannot tell which one was graded.

**Do not cue the answer.** The key should not be the longest option, the most
specific, the only one with a qualifier, or the grammatical continuation of the
stem. `verify.py` flags length spread; the others are on you.

**Do not negate unless negation is the point.** "Which is NOT…" measures reading
care under time pressure, which is rarely the concept. If you must, bold it and
keep it out of the double-negative trap.

**State enough context to be answerable from the span.** Not "What did the
authors find?" — which authors, which finding.

## Distractors

A distractor earns its place by being the answer a learner with a *specific*
misconception would choose. Ranked by usefulness:

1. **A neighbouring concept from the same material.** The learner who confused
   stability with retrievability picks it. This is the best kind.
2. **A reversal.** Right idea, wrong direction: difficulty high vs. low,
   increasing vs. decreasing.
3. **A plausible unit or scale error.** Days vs. reviews, proportion vs.
   percentage.
4. **A true statement that does not answer the stem.** Dangerous — it is
   defensible, which is why the adversarial pass hunts for it.
5. **A term from elsewhere in the document that sounds related.** Acceptable if
   the confusion is realistic.

Never use:

- joke options, or ones obviously too absurd to consider
- "all of the above" / "none of the above" (the verifier rejects these)
- a distractor that is only wrong because it is worded sloppily
- two distractors that are the same mistake twice

Keep all three options within about 40% of each other in length. A long correct
answer and two stubs is the single most common giveaway.

**Vary where the key sits.** If every item's answer is `A`, the learner can score
without reading, and they will learn to pick `A`. The verifier warns when all MCQ
keys occupy the same position, or when more than 70% share one. Spread across
`A`, `B`, `C` — but do not shove the key to `C` for every hard item either, since
that is the same bias in reverse.

## Worked examples

### Bad → good: cued stem

> **Bad.** "What is the term for the probability of recall at a moment in time?
> A. Retrievability B. Stability C. Difficulty"
>
> The stem is a dictionary definition pointing at one option. Anyone who has seen
> the word once picks A without understanding it.

> **Good.** "Two items have the same stability. Item A was reviewed one day ago,
> item B twenty days ago. Which has the higher retrievability, and why?"
> "A. Item A, because less time has elapsed B. Item B, because more time has
> passed C. Neither, because stability alone fixes retrievability"

This requires the model R = f(t, S), not word matching.

### Bad → good: unfalsifiable true/false

> **Bad.** "Feedback is important for learning. True/False."
>
> True, trivially, and every learner knows it before reading.

> **Good.** "Explanatory feedback produces larger gains than right/wrong feedback
> alone. True/False."
>
> A specific, checkable claim from the material, with a real chance of being
> misremembered.

### Bad → good: two defensible answers

> **Bad.** "What does FSRS use to schedule the next review?
> A. Stability B. Difficulty C. Retrievability"
>
> All three are inputs to the interval. The item has three keys.

> **Good.** "Holding difficulty constant, which change produces the larger
> stability gain: reviewing at retrievability 0.95 or at 0.70?"
> "A. Reviewing at 0.95 B. Reviewing at 0.70 C. They are equal"

One answer, and it tests the actual mechanism.

### Bad → good: explanation that restates

> **Bad.** `explanation_correct`: "The answer is B because reviewing at lower
> retrievability produces larger gains."

> **Good.** `explanation_correct`: "At low retrievability the memory is close to
> being lost, so a successful retrieval adds a lot of strength. At 0.95 there was
> little to gain, so the same review moves stability less."

### Bad → good: missing distractor rationale

> **Bad.** `distractor_rationale`: {"A": "incorrect"}

> **Good.** `distractor_rationale`: {"A": "treats high retrievability as high
> memory strength, reversing the relationship the model assumes"}

The rationale is the content the learner reads after missing. "Incorrect" tells
them nothing they did not already infer from the verdict.

## Calibrating `est_difficulty`

Set the expected proportion of learners answering correctly.

| value | means |
|---|---|
| 0.95 | everyone who read the section gets it |
| 0.80 | needs attention to a detail |
| 0.60 | needs the mechanism, not the label |
| 0.45 | needs integration across the section |
| 0.35 | too hard for a first pass; keep for later or drop |

Target a bank mean around 0.70–0.80. A bank where everything is 0.95 wastes
sessions; everything at 0.40 demoralises and produces lapses without learning.

The verifier warns outside 0.40–0.95.

## Traps that pass the verifier

These are valid JSON, correct quotes, real keys, and still bad items:

- **Testing the document rather than the subject.** "In which section does this
  appear?" is not knowledge.
- **Quoting a definition and asking for the quoted word.** Cued, not retrieval.
- **Items that any adult answers without the material.** Prior knowledge, so a
  correct answer is not evidence of learning from this document.
- **Splitting one fact into four items.** Inflates bank size and trains
  nothing.
- **"According to the passage" on every stem.** Signals that outside knowledge
  would work, which is fine, but repeating it wastes attention. Use it only where
  the claim is author-specific.
- **Borrowed authority.** "Research shows…" when the section only says one study
  found it. That changes the strength of the claim, and the learner will
  remember the stronger version.

## The final check

Ask: **what would a learner who missed this item now believe that they did not
before?** If the answer is a specific, correct idea, ship it. If it is "that I
was wrong", rewrite it.
