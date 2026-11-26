# Scheduling reference

For answering "why is this item back today?" without inventing an explanation.

The learner never sets a rating and never sees a parameter. `session.py` derives
everything from whether the answer was right and how long it took.

## What the three state variables mean

| variable | range | plain meaning |
|---|---|---|
| **Retrievability** `R` | 0–1 | chance of recall right now |
| **Stability** `S` | days | time for `R` to fall to 0.9, with no review |
| **Difficulty** `D` | 1–10 | how hard this item is for this learner |

`R` decays with elapsed time and rises back toward 1 after a successful review.
Each successful retrieval buys more stability, but the gain shrinks as the item
becomes more stable — that is why intervals grow then plateau.

## The four ratings, and how they are derived

| observation | rating | label |
|---|---|---|
| wrong | 1 | Again |
| partly right | 2 | Hard |
| right but slow | 2 | Hard |
| right | 3 | Good |
| right and reported confident | 4 | Easy |

"Slow" is measured against the item's own p75 latency once there is history;
before that, no item is penalised for slowness.

Nothing here is learner-reported except the optional confidence flag. That is
deliberate: self-rated difficulty is poorly calibrated, and asking for it every
card is the main reason people abandon spaced-repetition tools.

## What an interval means

| interval | reads as |
|---|---|
| 1 day | first exposure or a lapse; it will be back tomorrow |
| ~4 days | initial success |
| 1–2 weeks | recalled once at delay |
| 1–2 months | holding |
| 6+ months | stable, rarely needs attention |

A lapse does not reset to zero. It cuts stability hard, usually to a few days,
and the ladder rebuilds faster than the first time because the item is not new.

## The mastery ladder

Counted per **concept**, not per item.

| level | requires |
|---|---|
| exposure | a review was recorded |
| attempted | any correct answer |
| retained | correct after a gap of at least one day |
| stable | two consecutive correct answers, both delayed |
| transferred | stable, plus a correct delayed answer on a *different* item of the same concept |

"Transferred" is the only level that supports a claim of understanding rather
than recall, which is why it needs a second item.

## Guess correction

Multiple choice and true/false have a floor. Observed accuracy is corrected:

```
p_corrected = max(0, (p_observed - 1/k) / (1 - 1/k))
```

with `k` the number of options. `stats` reports both, labelled. Never quote the
observed figure as knowledge — 33% on 3-option MCQ is chance.

## Desired retention

Default 0.90, adjustable with `--retention` (clamped 0.80–0.97). This is the only
scheduling knob worth exposing.

| setting | effect | when |
|---|---|---|
| 0.80 | longer intervals, fewer reviews | long horizon, low stakes |
| 0.90 | default | general study |
| 0.97 | short intervals, many reviews | exam within a week |

Raising it does not improve learning per review. It trades review volume for
recall probability, and the learner should know that trade.

## Answering the learner

- "Why is this back today?" → its stability has decayed to the target retention;
  the elapsed time is the interval that was scheduled.
- "Why did a wrong answer bring it back tomorrow?" → a lapse resets to a short
  interval by design, so a weak item is not left alone.
- "Why did this jump to two months?" → successive correct delayed reviews
  compound stability; that is the intended shape.
- "Can I just do all of them today?" → yes, and it will not help. Massed review
  feels productive because it is fluent (DR-2, DR-29); the schedule exists to
  defeat that feeling.

Never promise a specific retention number for a specific learner. These are
model estimates from population data, and the honest claim is directional.
