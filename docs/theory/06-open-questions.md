# 06 — Open questions

Decisions we cannot make from the literature, ordered by how much they block
work. Each has options and a recommended default so we are never stuck.

---

## Blocking: the testing protocol

**Q1. What does "testing" mean in this product?** The user has said the details
will come later; until then the design should stay protocol-agnostic. Three
candidate protocols, with different implications:

| Protocol | What the learner does | Optimises for | Cost |
|---|---|---|---|
| **A. Bank + spaced review** (Anki-like) | answer items, get feedback, items return on a schedule | durable retention | needs many items per concept, needs return visits |
| **B. Exam simulator** | timed paper, feedback at the end, format-matched | performance on a specific exam | cheap to build, weak learning effect (no per-item feedback) |
| **C. Socratic tutor** | answer, explain reasoning, get probed | understanding, transfer | expensive per item, hard to grade, best for hard concepts |

They are not exclusive — the recommended default is **A as the spine, with C
used for items the learner keeps failing, and B available as an optional mode
explicitly framed as format practice rather than learning.** Confirm with the
user before building anything.

**Q2. Is this for one learner (self-study) or a class?** Changes everything
about the data model: multi-learner introduces per-learner item statistics,
anonymised cohorts, and teacher review of items. Current assumption:
single-learner local tool.

**Q3. Where does the output live?** Options: (a) agent skill producing JSON
files, (b) local webapp, (c) both — skill generates, webapp practises. The
bundled prior art is (b)-with-a-skill-wrapper on Windows.

Settled: (a) is built, and it is file-based. No web page exists. Rather than
guessing whether one is wanted, the skill asks the learner once per project and
records the answer; if they ask for a page today, the honest reply is that it is
not built yet. Revisit if the ask turns out to be common — a page would mostly
lower the cost of returning for spaced review, which is where A4 is decided.

---

## Blocking: the unit of mastery

**Q4. Concept, item, or section?**
- Item-level is trivially measurable and pedagogically hollow.
- Section-level hides untouched ideas behind easy items.
- Concept-level requires concept boundaries, which requires either the outline
  or clustering — an extra pipeline stage and a place for errors to enter.

Recommended: concept-level, with concepts extracted in Stage 3 and *stored*, so
the boundary decision is reviewable. If that proves too expensive, fall back to
item-level but never call it "mastery" (04 §4).

**Q5. How much evidence counts as "learned"?** Options: 1 delayed correct
re-test; 2 consecutive delayed correct re-tests; delayed correct + a transfer
item. Recommended: 2 consecutive delayed (at increasing intervals) OR 1 delayed
+ 1 transfer. Record which criterion fired.

---

## Design choices needing a decision

**Q6. Do we re-show the source excerpt on every review, or only after a
failure?** Re-showing helps a failed item (DR-7). On a *successful* review it may
convert retrieval into recognition of the excerpt. Recommended: excerpt after
the attempt always, but collapsed by default on success so it does not become a
cue during answering.

**Q7. Language handling.** Follow the document language (current rule). But what
if the user reads English papers in a Chinese UI? Terminology should stay in the
source language; instructions in the UI language. Needs a concrete policy before
item generation is built.

**Q8. Auto-grading of short answers.** Rubric + LLM grader, then self-assessment
on uncertainty (DR-16). Open question: what is the acceptable false-negative rate
on correct answers? A misgraded correct answer is the worst failure mode. Proposal:
whenever grader confidence < threshold, always ask the learner rather than guess.

**Q9. How many items per concept?** More items per concept improves scheduling
flexibility (you can review a concept without repeating the identical item, which
also reduces item memorisation). Cost scales linearly. Proposal: 2–3 items per
concept for high-value concepts, 1 for enumerable facts.

**Q10. Should items ever be generated from figures/tables?** Currently excluded
(cannot validate the span). Revisit if the target documents are figure-heavy
(anatomy, chemistry, statistics).

---

## Assumptions we are making that should be tested

| # | Assumption | How to test cheaply | If wrong |
|---|---|---|---|
| A1 | LLM-generated items from a PDF can pass a strict span-verification gate at >80% | run the gate on 3 real PDFs, count pass rate | loosen QA → quality collapses; must fix generation prompt first |
| A2 | 3-option MCQs written by an LLM have workable distractors | measure `distractor_pick_rate`; non-functional if <5% | switch default format to cloze |
| A3 | Target 60–85% success is achievable by tuning `est_difficulty` | compare predicted vs observed on first 100 responses | recalibrate prior, keep the band |
| A4 | Users return for spaced review at all | measure D1/D7 return rate | the spaced part of the design is dead weight; pivot to single-session depth |
| A5 | Concept-level mastery is worth the extraction cost | compare concept count vs item count per section | fall back to sub-topic granularity from the outline |
| A6 | Auto-deriving the FSRS rating from correctness+latency is close enough to self-rating | compare on a sample where both are collected | collect explicit self-ratings |

A1 and A4 are the two that decide whether this product works at all. Test them
before building the scheduler.

---

## Deliberately out of scope (for now)

- Multi-user accounts, sharing banks, class dashboards.
- Adaptive item *generation* at review time (generate a fresh variant when an
  item is due). Attractive, but it removes the ability to measure item quality
  across learners and makes scheduling unstable. Revisit after A1/A4.
- Mobile app.
- Any claim of "personalised learning" beyond what the item statistics support.
- Grading students / academic integrity tooling. The evidence base here is about
  learning, and using the same machinery for surveillance assessment is a
  different product with different ethics.
