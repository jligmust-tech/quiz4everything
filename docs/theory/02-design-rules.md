# 02 — Design rules

Every rule is a requirement that can be tested. Tag `[E]` = evidence-backed,
`[W]` = weak evidence, `[?]` = our judgement. Rationale cites
[01-evidence-base.md](01-evidence-base.md) and [references.md](references.md).

---

## A. Retrieval is the point

**DR-1** The primary user action on every item is **producing an answer before
seeing the answer**. Glance-and-flip is not retrieval. `[E]`
> Rowland 2014; Roediger & Karpicke 2006. The "flashcard turned over too early"
> failure mode is documented — flipping before an answer is formulated converts
> retrieval into re-reading.

**DR-2** Answer reveal requires an explicit commitment action (submit / reveal),
and the attempt is logged with latency. `[W]`
> Allows later detection of "reveal-spam" sessions, which produce engagement
> metrics but no learning.

**DR-3** Every item is answerable **without the source document at hand**. If an
item cannot be answered from memory + the stem alone, it is a cloze-in-context,
not a retrieval item. `[?]`

## B. Feedback

**DR-4** Corrective feedback is unconditional: after every response, show the
correct answer, the rationale, and the source excerpt. No "feedback on request"
mode as the default. `[E]`
> Rowland 2014 (0.73 vs 0.39); Yang 2021 (0.537 vs 0.374).

**DR-5** Wrong options get a reason, not just a red cross. For each distractor,
state the misconception it captures. `[E]`
> Pan & Rickard 2018: elaborated retrieval practice +0.23 on transfer.
> Roediger & Marsh 2005: unexplained lures can become false beliefs.

**DR-6** Feedback appears **after** the attempt, never before or during. `[E]`
> Feedback that pre-empts retrieval removes the retrieval event.

**DR-7** For a failed item, the feedback must include the surrounding context
(2–5 sentences of source), not just the correct option. `[W]`

## C. Item validity (this is the highest-risk area)

**DR-8** Every item must cite a `source_span` (page + character offsets or a
verbatim quote) that **contains** the evidence for the key. Items whose span
cannot be located in the parsed document are rejected automatically. `[?]`
> This is our main defence against hallucinated content, which no learning-
> science literature covers.

**DR-9** The key must be uniquely correct and the item answerable from the span
alone. An independent adversarial pass must fail to find a second defensible key.
`[?]`

**DR-10** Distractors must be *wrong for a reason that is named in the item
metadata*, not merely wrong. Reject any distractor that is accidentally true in
some plausible reading. `[E, via DR-5]`

**DR-11** No "all of the above" / "none of the above"; no negations in the stem
where avoidable; options grammatically parallel and similar in length. `[E, W]`
> Standard item-writing guidance (Haladyna et al. 2002); Haladyna & Rodriguez
> 2013. Weak as a learning claim, strong as a measurement claim.

**DR-12** Default to **3 options** for MCQ. `[E]`
> Rodriguez 2005 (80 years, 56 studies): 3-option items are as discriminating as
> 4–5 option items, allow more items per unit time, and 4th/5th options are
> usually non-functional. More items per session = better content coverage.

**DR-13** Do not report a mastery percentage derived only from MCQ accuracy.
Recognition has a guess floor. Either correct for guessing or mix in production
items. `[?]`
> See 04-schedule-and-mastery.md §4.

## D. Format mix

**DR-14** Each section's bank must contain at least two formats: MCQ **and** a
production format (cloze or short answer). `[E]`
> Yang 2021: fill-in-the-blank 0.773, short answer 0.638, MCQ 0.567. Adesope
> 2017 contradicts the MCQ-vs-SA ordering but not the value of production.
> Pan & Rickard 2018: format match is a strong transfer moderator, so offer the
> format that matches the user's real target (exam, viva, interview).

**DR-15** The user chooses the "target format" (e.g. "my exam is short answer"),
and the bank weights practice toward that format. `[E]`
> Transfer-appropriate processing; Yang's format-match moderator (0.531 vs 0.399).

**DR-16** Short-answer items are auto-graded with a rubric and, when the grader
is uncertain, escalated to self-assessment ("did you say X? yes / partly / no").
Never silently mark a semantically-correct answer wrong. `[?]`
> Misgrading a correct production answer is a worse failure than not scoring it:
> it teaches the learner that a correct memory is wrong.

## E. Difficulty

**DR-17** Target expected success rate **60–85%** per item at first exposure.
Items calibrated outside 40–95% are down- or up-weighted in the session. `[E]`
> Bifurcation model (Halamish & Bjork 2011; Kornell et al. 2011); Glaser &
> Richter 2018 (effect present at 46–81% retrievability); Pan & Rickard 2018
> (transfer rises with initial accuracy).

**DR-18** Difficulty is a property of the item *for this learner*, not a static
label. Start from a generation-time estimate (basic/advanced), update from
observed accuracy. `[?]`

**DR-19** Include a small number of "stretch" items (application / inference)
even if expected success is ~50%, but always with feedback. `[W]`
> Transfer to application questions is the strongest transfer case in Pan &
> Rickard — but only with feedback and answer overlap.

## F. Session shape

**DR-20** Session = short cycle: 5–10 items, immediate feedback, then a
review pass over missed items in the same session. `[?]`

**DR-21** Re-test every item at least once at a **later** session. A
single-exposure quiz is the weakest configuration. `[E]`
> Rowland 2014: ≥1 day retention interval g = 0.69 vs < 1 day 0.41. Yang 2021:
> more repetitions, longer interventions, larger effects.

**DR-22** Do not test the same item twice in a row within a session (massed
repetition); interleave other items between repeats. `[W]`
> Spacing literature; interleaving evidence is domain-dependent (Rohrer) so keep
> this as a soft rule.

**DR-23** Never show the whole answer key or a "review all answers" screen
before the user has attempted the items. `[E, DR-1]`

## G. Scheduling

**DR-24** Use a real memory model (FSRS-style DSR) rather than fixed intervals,
but ship with sensible defaults and no parameter-tuning required from the user.
`[W]`
> FSRS (Ye et al. 2022; Anki default scheduler) is well-validated on
> 20k+ users' review logs and needs no per-user optimisation to be better than
> fixed intervals. Exact FSRS version is an implementation choice.

**DR-25** Desired retention default **0.90**, configurable 0.80–0.97. Show the
trade-off in plain language ("more reviews / fewer reviews"), not the parameter.
`[W]`

**DR-26** All scheduling math must degrade gracefully with no history: first
review = same-session or next-day, not an arbitrary long interval. `[?]`

## H. Metacognition & honesty

**DR-27** After each session, show *calibration* (predicted vs actual), not just
score. `[E]`
> The core finding of Roediger & Karpicke 2006 is a metacognitive illusion;
> correcting it is part of the intervention's value.

**DR-28** Never claim a learning benefit from a session that has not yet been
retested after a delay. Session-1 score is a *diagnostic*, not an outcome. `[E]`

**DR-29** State clearly that the tool generates items from the user's document
and may contain errors; provide a one-click "this item is wrong" report that
also serves as our QA signal. `[?]`

**DR-30** Do not gamify in ways that reward volume over retention (streaks for
items answered, XP for sessions). Reward *retained* items. `[W]`
> Motivation is a real mechanism (Yang), but volume-chasing is exactly the
> behaviour the literature warns against.

## I. Content coverage

**DR-31** The section outline shown to the user must be derived from the
document's own structure where available (headings, numbered sections), with
LLM segmentation only as fallback. Show page ranges. `[?]`

**DR-32** Items are sampled to cover the section's sub-topics roughly evenly;
no more than ~30% of items from one sub-topic unless the user asked to focus. `[?]`
> Mirrors the "even coverage" constraint in the prior `learning-quiz-bank` prompt
> and the general item-sampling logic in achievement testing.

**DR-33** The user's chosen focus (a sub-section, "the methods part") restricts
generation. Focus must never be silently widened. `[?]`

## Open design questions that block implementation

See [06-open-questions.md](06-open-questions.md). The three that matter most:

1. What exactly does "testing" mean in the user's intended workflow — a graded
   exam simulator, a spaced-repetition loop, or Socratic tutoring?
2. Is the unit of mastery the *item*, the *concept*, or the *section*?
3. Where does the source text live at review time — do we re-show the excerpt on
   every review, or only on failure?
