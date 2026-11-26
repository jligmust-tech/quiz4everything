# 01 — Evidence base: the testing effect and retrieval practice

Scope: what is established well enough to design against, what is contested, and
where the numbers come from. Everything here is about *learning from being
tested*, not about assessment for grading.

---

## 1. The core claim

**Retrieval practice** (being tested on material) produces better long-term
retention than **restudying** the same material for the same amount of time.

The canonical demonstration is Roediger & Karpicke (2006): students read a prose
passage, then either re-read it or took a free-recall test. After 5 minutes,
re-reading won. After 1 week, the tested group retained substantially more.
The uncomfortable part: the re-reading group was *more confident* it would
remember. Subjective fluency and actual retention dissociate.

This matters for our product because it means the user's instinct ("let me read
the PDF once more") is the wrong instinct, and their instinct about quizzes
("quizzes are for grading, not learning") is also wrong. Karpicke, Butler &
Roediger (2009) found students overwhelmingly choose re-reading over
self-testing when asked how they study.

---

## 2. How big is the effect

Four independent syntheses, all converging on "medium":

| Synthesis | Corpus | Comparison | Effect |
|---|---|---|---|
| Rowland (2014), *Psych. Bull.* | 61 experiments, 159 effect sizes | testing vs restudy (lab) | **g = 0.50** [0.42, 0.58] |
| Adesope et al. (2017), *RER* | 272 effect sizes, N = 15,427 | practice test vs all non-testing controls | **g = 0.61** fixed-effects [0.58, 0.65]; 0.70 random-effects |
| Yang et al. (2021), *Psych. Bull.* | 222 studies, 573 effects, N = 48,478 | classroom quizzing vs control | **g = 0.499** |
| Pan & Rickard (2018), *Psych. Bull.* | 192 effects, 122 experiments, N = 10,382 | transfer to *new* questions | **d = 0.40** [0.31, 0.50] |

Note how the headline moves with the control condition:

- vs **restudying**: g = 0.51 (Adesope) / 0.33 (Yang, classroom where the control
  class also restudied)
- vs **filler or no activity**: g = 0.93 (Adesope) / 0.61 (Yang)
- vs **other elaborative strategies** (concept mapping, summarizing, note-taking):
  g = 0.095 — i.e. **no reliable advantage** (Yang)

> **Implication for us.** The honest comparison is testing *instead of re-reading*,
> so the defensible promise is ~0.4–0.5 SD, not 0.9 SD. Marketing a quiz tool as
> far superior to good note-taking is not supported.

Also relevant: Yang and colleagues report a separate meta-analysis (2023) in
which quizzing *reduced* test anxiety (g ≈ −0.52, 25 studies). Low-stakes
quizzing is not just neutral on affect; it appears mildly protective.

---

## 3. Why it works — the competing accounts

Five accounts, none of which fully explains the data. We should design so that
several of them are satisfied at once, rather than betting on one.

1. **Transfer-appropriate processing** — practice should resemble the target
   performance. Big moderator: format match. Yang: format-matched practice
   g = 0.531 vs mismatched 0.399. Pan & Rickard: *response congruency* (do the
   practice and criterion tests share answers?) is the strongest transfer
   moderator — no congruency d = 0.28, congruent d ≈ 0.58.
2. **Elaborative retrieval / mediator activation** — trying to recall activates
   related knowledge, building a richer retrieval route. Pan & Rickard:
   elaborated retrieval practice adds ~+0.23.
3. **Retrieval effort / desirable difficulty** (Bjork) — the harder the
   successful retrieval, the more it strengthens memory. Corollary: *failed*
   retrieval with no feedback does little. Rowland: feedback 0.73 vs no feedback
   0.39; and in the bifurcation model, no testing effect appears when initial
   retrievability is below ~50% without feedback.
4. **Additional exposure** — a test re-exposes you to the material, including
   the correct answer in feedback. Yang finds this accounts for part (not all)
   of the classroom effect; untested-but-related material still benefits
   (g = 0.321), which pure exposure cannot explain.
5. **Motivation / goal orientation** — being quizzed changes what students
   attend to. Yang treats this as a real, if hard-to-quantify, contributor.

**Design consequence:** feedback and answer elaboration are not optional
cosmetics. They are the difference between g = 0.39 and g = 0.73.

---

## 4. Moderators that matter for a PDF→quiz pipeline

Ranked by how much they change the outcome and how directly we control them.

### 4.1 Feedback — the largest lever we control [E]
- Rowland: with feedback g = 0.73, without 0.39.
- Yang: corrective feedback g = 0.537 vs no feedback 0.374.
- Feedback that explains *why* distractors are wrong is elaborative feedback,
  which Pan & Rickard associate with a further +0.23 on transfer.

### 4.2 Retention interval — timing of the test [E]
- Rowland: final test ≥ 1 day later g = 0.69; < 1 day g = 0.41.
- Immediate quizzing is fine for calibration; the *learning* payoff shows up
  when material is re-tested after a delay.
- Consequence: a single same-session quiz is the weakest version of this
  product. Spaced re-testing is where the effect lives.

### 4.3 Format of the practice item [E, but confounded]
Yang (classroom, practice format):
fill-in-the-blank 0.773 > short answer 0.638 > multiple choice 0.567 > free recall 0.238.

Adesope (lab) found the opposite ordering for MCQ vs short answer
(0.70 vs 0.48). These two results conflict; the most likely reason is that in
classroom studies the *final* exam format co-varies with the practice format.
Treat the ordering as "production formats (cloze/short answer) are at least as
good as recognition formats, and are better for transfer" rather than a precise
ranking. **The safe conclusion: don't build a recognition-only product.**

### 4.4 Item difficulty / initial retrievability [E]
- Testing effect appears when initial success is roughly 46–81% (Glaser &
  Richter, 2018, university teaching); below ~50% with no feedback, no effect
  (bifurcation model: Halamish & Bjork 2011; Kornell et al. 2011).
- Pan & Rickard: each +1 percentage point of initial accuracy adds ~+0.006 d to
  transfer.
- Too easy (≥95%) is wasted time; too hard (<50%) trains failure.
- Practical target band: **60–85% expected success**, with feedback always on
  below 85%.

### 4.5 Repetitions and spacing [E]
- Yang: number of test repetitions positively moderates the classroom effect;
  semester-long interventions (g > 0.5) beat single-class ones (0.385).
- Cepeda et al. (2006; 839 assessments, 317 experiments): the optimal gap
  between study episodes grows with the target retention interval. A widely
  used rule of thumb is a gap of roughly 10–20% of the desired retention
  horizon `[W]` — direction is well supported, exact ratio is not settled.
- Practical: re-ask missed items within the session, and schedule correct items
  at 1d → 3d → 7d → 21d unless a scheduler says otherwise.

### 4.6 Pre- vs post-reading quizzing [E]
Yang: post-class quizzing 0.536 vs pre-class 0.186. Pretesting has a real but
small "prequestion" benefit. Default to quizzing *after* the section is read;
use pretest only as a deliberate warm-up.

### 4.7 Material domain and learner level [E]
Yang: no significant variation across 31 subjects / 18 categories, and effects
held for primary through university students. So we do not need per-domain
theory — but we do need per-domain *content correctness* checking, which is a
different problem (see 05-pipeline QA).

---

## 5. Where the effect is weaker than the headline suggests

Be explicit about these; they are the arguments a skeptical user will make, and
they are partly right.

1. **Transfer is fragile.** Pan & Rickard's PET-PEESE correction substantially
   reduced the intercept: with no response congruency, no elaboration, and low
   initial accuracy, transfer may be near zero. Practising MCQs and then facing
   a novel application question is the *best* case, not the average case.
2. **Multiple-choice items can teach the wrong answer.** Roediger & Marsh (2005)
   showed that plausible lures on MC tests can later be endorsed as true
   ("negative suggestion effect"), especially with little feedback. Distractor
   quality is therefore a *safety* issue, not just a psychometrics issue.
3. **Recognition ≠ production.** A 3-option MCQ has a 33% blind-guess floor, so
   accuracy on MCQs overstates knowledge. Never report "you know 80% of this"
   from MCQ accuracy alone.
4. **Effect sizes in lab ≠ your app.** The lab studies control time-on-task,
   enforce compliance, and use experimenter-written items. An LLM writing items
   from a PDF introduces a new error source (invalid keys, unanswerable stems)
   that no meta-analysis covers.
5. **Novelty and Hawthorne effects** inflate early engagement metrics; the
   semester-long vs single-class gap in Yang suggests durable gains need durable
   use.

---

## 6. What this means in one table

| Question | Answer we will design to | Confidence |
|---|---|---|
| Is quizzing better than re-reading? | Yes, ~0.4–0.5 SD | high |
| Does it help on new questions? | Yes but smaller, ~0.3–0.6 d depending on format/answer overlap | medium |
| Should we give feedback? | Always, with explanation of wrong options | high |
| Should items be easy or hard? | Target 60–85% success | medium-high |
| MCQ only? | No — add cloze/short answer | medium |
| One quiz per section enough? | No — repeat and space | high |
| Should the quiz be graded? | Low stakes; grading pressure not required for the effect | medium |

---

## References

See [references.md](references.md). Key entries: Rowland 2014; Adesope et al.
2017; Yang et al. 2021; Pan & Rickard 2018; Roediger & Karpicke 2006; Roediger &
Marsh 2005; Cepeda et al. 2006; Bjork & Bjork 2011; Karpicke et al. 2009;
Glaser & Richter 2018; Rodriguez 2005; Ye et al. 2022.
