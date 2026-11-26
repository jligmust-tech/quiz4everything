# 04 — Scheduling, mastery, and measurement

How often to re-ask, what "learned" means, and what we are allowed to claim.

---

## 1. Two different jobs

| Job | What it does | Model needed |
|---|---|---|
| **Diagnose** | find out what the learner does / doesn't know right now | item-response-ish, per-item accuracy |
| **Schedule** | decide when to show the item again | memory model over time (DSR/FSRS) |

Keep them separate. Conflating them is how products end up with "your score is
72%" meaning both "you got 72% today" and "you will remember 72% in a month" —
two claims, one number, neither honest (DR-28, DR-13).

---

## 2. Spacing: the interval is the design variable

- The optimal gap scales with the target retention horizon (Cepeda et al. 2006,
  839 assessments). Direction: well established. Exact multiplier: not settled.
- Rowland (2014): the testing effect is larger at ≥1 day than <1 day
  (g = 0.69 vs 0.41). So the second encounter matters more than the first.
- Yang (2021): more test repetitions and longer interventions → larger effects.

**Practical default ladder** `[?]` anchored to the above, not to any specific
scheduler: `same session (missed only) → +1d → +3d → +7d → +21d → +60d`.
Once a real memory model is in place, the ladder is replaced by
`next_interval(S, D, R)` and the ladder only serves as a cold-start fallback.

---

## 3. FSRS / DSR, in the minimum detail a designer needs

The open-source **FSRS** family (Ye, Su & Cao, KDD 2022; the model inside Anki)
tracks three numbers per item:

- **Stability `S`** — elapsed time for recall probability to fall to 90%.
- **Difficulty `D`** — how hard this item is for this learner (1–10).
- **Retrievability `R`** — probability of recall now, a function of time since
  last review and `S`.

Each review updates `(S, D)` from the rating and the *current* `R`. Three
properties that drive product decisions:

1. **Reviewing late is more valuable than reviewing early** (as long as recall
   succeeds): lower `R` at review → larger stability increase. This is the
   spacing effect formalised.
2. **Stability of growth saturates** — a very stable item gains little from
   another review. So identical review counts per item are wasteful.
3. **Difficulty is per-item, per-learner**, not a property of the text.

Implications we accept:
- `[W]` Use FSRS defaults; do not ask the user to tune 19–34 parameters. It
  is well-validated out of the box (trained on 10k–20k users' logs) and beats
  SM-2-style fixed multipliers.
- `[?]` Desired retention (default 0.90) is the one knob exposed, phrased as
  "how often do you want to review" with the review-load trade-off shown.

### Grading into the scheduler
We need a 4-level rating for each review (Again / Hard / Good / Easy). Do **not**
ask the learner to self-rate if we can derive it honestly:

| Observed | Rating |
|---|---|
| wrong, no partial credit | Again |
| wrong, semantically close (production) | Hard |
| correct but slow (> p75 latency) | Hard |
| correct, normal latency | Good |
| correct, fast + confident | Easy |

Self-rating is still offered for production items the auto-grader cannot judge.
`[?]` Deriving the rating keeps a single tap ("submit") as the whole interaction,
which matters for adherence more than rating precision does.

---

## 4. Mastery: what we can and cannot claim

Definitions, in increasing strength:

- **Exposure** — item shown. Meaningless alone.
- **Attempted correctly** — one correct response. Weak: guessable if MCQ.
- **Retained** — correct at a *delayed* re-test (≥1 day, ideally ≥7). This is
  the first point at which the testing-effect literature supports a claim.
- **Stable** — correct at two consecutive delayed re-tests with increasing
  intervals. Reasonable operational definition of "learned". `[?]`
- **Transferred** — correct on a *new* item testing the same concept in a
  different format. Best evidence of usable knowledge (Pan & Rickard 2018).

**Section mastery** = share of the section's *concepts* in `Stable` or better,
where concepts (not items) are the unit. Otherwise a section with 30 trivial
items looks mastered while its two hard ideas are untouched.

### Guess correction
For 3-option MCQ, chance = 1/3. A conservative corrected accuracy:
`p_corrected = max(0, (p_observed − 1/k) / (1 − 1/k))`. Never show the
uncorrected number as "mastery" (DR-13). Prefer reporting mastery from a mix of
formats and, where possible, only from production items.

### What we must not say
- Not "you have learned X" after one correct response.
- Not "you will remember X% in a month" from a single session (we have no
  calibration data for this learner).
- Not a percentage with 2 decimal places.

---

## 5. Item statistics we should collect from day one

Even at small scale, these are cheap and become the QA backbone:

| Statistic | Definition | Use |
|---|---|---|
| `p_value` | proportion correct, first exposure | difficulty calibration (DR-17) |
| `discrimination` | point-biserial between item score and rest-of-session score | kill ambiguous items |
| `distractor_pick_rate` | per-option selection frequency | a distractor picked by <5% is non-functional; a distractor picked by >40% flags a second key |
| `latency_p50/p90` | time to first response | detect guessing and reveal-spam |
| `flag_rate` | "this item is wrong" reports | human-in-the-loop QA |
| `retest_delta` | accuracy at delayed re-test minus first exposure | actual evidence the item *teaches* |

`distractor_pick_rate` is the single most useful number: it catches the
"accidentally true distractor" failure (DR-10) that our adversarial check may
miss, and it tells us which misconceptions learners actually hold — which is
itself good material for explanations.

---

## 6. Cold start

With no history, every estimate is a prior. Concretely:

1. `est_difficulty` from the generator (`basic` → 0.85, `advanced` → 0.55),
   clamped to 0.4–0.95.
2. First session: draw a mix, ~60% at/below target band, ~40% stretch.
3. After ~20 responses, refit per-item `p_value` empirically and stop trusting
   the generator's label.
4. After ~100 responses across a section, order items by observed difficulty
   rather than by generation order.

---

## 7. Session templates

**A. Learning session (first exposure to a section)** — 8 items, mixed format,
immediate feedback, then re-ask the missed ones once. Ends with calibration
report. Target 10–15 min.

**B. Review session (spaced)** — only items whose `R` has dropped below the
desired retention; immediate feedback; no re-ask in-session unless failed twice.
Target 5–10 min.

**C. Exam simulation** — no feedback until the end, timed, format-matched to the
user's stated target format. Used sparingly: it is a *diagnostic*, and the
learning benefit is smaller without per-item feedback (DR-4). Justify it as
"practice the format" not "learn faster". `[W]`

**D. Socratic drill** — one item at a time, learner must explain their reasoning
before the key is revealed; the explanation is graded for inclusion of the
mechanism. Highest-effort, highest-transfer. Use for the concepts the learner
keeps failing. `[W]`

---

## 8. Numbers to report, and their honest framing

| Shown | Computed from | Framing |
|---|---|---|
| Items due today | scheduler | "5 items to review" — no percent |
| Retention estimate | mean `R` over due items | "you're likely to recall ~X% of these" — only after ≥1 delayed re-test |
| Calibration | predicted vs actual per session | "you predicted 80%, scored 55%" — the metacognitive correction |
| Coverage | concepts with ≥1 attempt / concepts in section | honest gap indicator |
| Mastery | concepts at Stable+ | "8 of 12 concepts retained" — a count, not a vague percent |

---

## Open items

- Decide whether concept boundaries come from the outline or from clustering
  items by embedding + source span. (Blocks any mastery number.)
- Decide minimum evidence for "Stable": 2 delayed re-tests vs 1 delayed re-test
  plus a transfer item. See [06-open-questions.md](06-open-questions.md).
