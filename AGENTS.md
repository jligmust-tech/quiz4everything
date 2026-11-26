# AGENTS.md

Guidance for coding agents working in this repository.

## What this is

`quiz4everything` turns a document into a verified quiz bank, then runs retrieval
practice and spaced review on it. Theory in `docs/theory/`, the working agent
skill in `skills/quiz4everything/`.

## Before you change behaviour

The skill's rules are not style preferences; each cites a design rule (`DR-*`) in
`docs/theory/02-design-rules.md`. If you find yourself relaxing one, read the rule
first and say why it no longer applies.

## Running and testing

```bash
python3 skills/quiz4everything/scripts/schedule.py --self-test   # 22 assertions
python3 skills/install.py --list                                  # install targets
```

There is no test suite. Verification is behavioural: ingest a small `.md` and its
PDF twin and confirm the same sections; put a fabricated quote in a bank and
confirm `verify.py` rejects exactly that item and nothing else.

## Hard constraints

- **Never commit the local `learningHelper` / `trainingHelper` source.** It is not
  part of this project. Only the skill is.
- Scripts must stay dependency-free apart from optional PDF extraction (`pypdf`
  or `pdftotext`). No network calls.
- Keep the scripts deterministic. Anything a model must not decide — span
  existence, option structure, intervals, grading of closed formats — belongs in
  Python, not in a prompt.
- Console output must survive a non-UTF-8 terminal. Import `_console` and call
  `_console.setup()` in `main()`; prefer ASCII separators from `_console`.

## Portability

The skill must work in Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot and
OpenCode, on macOS, Linux and Windows. That means: `python3` or `python`, path
quoting, no POSIX-only assumptions, and `SKILL.md` frontmatter that parses under
strict YAML.

## Communication

Write to the user in English, including code comments, commit messages, and
chat replies. The skill itself must still follow the *document* language for
generated items (see `DR` rules on language), but that is a product behaviour,
not a communication style.

## Docs

- `docs/theory/` — the evidence base and reasoning. Do not restate it in code
  comments; cite it.
- `skills/README.md` — install, layout, what is deterministic.
