# quiz4everything

Turn reading material into practice that is actually worth doing.

Give it a PDF, pick a section, and it builds a question bank for that section —
then runs the testing-and-learning loop that the cognitive science says works:
retrieve before revealing, get feedback that explains, come back later.

## Status

**Theory and design only.** No implementation yet. The plan, the evidence base,
and the open questions live in [`docs/theory/`](docs/theory/).

## The intended loop

```
PDF ──► section outline ──► user picks one ──► items ──► practice ──► spaced review
```

## Read this first

- [`docs/theory/README.md`](docs/theory/README.md) — overview and document map
- [`docs/theory/01-evidence-base.md`](docs/theory/01-evidence-base.md) — what the
  testing-effect literature actually shows, with effect sizes and caveats
- [`docs/theory/02-design-rules.md`](docs/theory/02-design-rules.md) — the rules
  the implementation must satisfy
- [`docs/theory/06-open-questions.md`](docs/theory/06-open-questions.md) — what is
  still undecided

## Short version of the evidence

Retrieval practice beats re-reading by roughly half a standard deviation
(Hedges' *g* ≈ 0.50), the advantage grows with the delay before the test, it is
much larger when feedback explains the answer (*g* ≈ 0.73 vs 0.39), and it
transfers to new questions only partly (*d* ≈ 0.40). Learners under-use it
because re-reading feels more effective. The design rules exist to keep the tool
on the right side of those moderators.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
