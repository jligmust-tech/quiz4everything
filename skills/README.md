# quiz4everything skills

Agent skills that turn a document into practice, then run the practice.

This directory is the **installable** form of the design in
[`../docs/theory/`](../docs/theory/). It is deliberately a skill, not an app: no
server, no database, no account. State is files in a directory you choose.

## Install

The skill format is portable; the *location* is not. Every agent scans its own
folder, so use the installer, which knows them all:

```bash
python3 skills/install.py --list        # agents found, and where they'd go
python3 skills/install.py               # detected agents, user scope
python3 skills/install.py --agent all   # every known agent
```

Or install by hand into any one of these:

| agent | user folder | project folder |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.agents/skills/` |
| GitHub Copilot / VS Code | `~/.copilot/skills/` | `.github/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.agents/skills/` |

Four of those read each other's folders, so `.agents/skills/quiz4everything/`
alone covers Codex, Cursor, Gemini CLI and OpenCode; adding `.claude/skills/`
covers Claude Code, and `.github/skills/` covers Copilot.

```bash
# the one-folder version, if you only care about the .agents/ readers
cp -R skills/quiz4everything .agents/skills/quiz4everything
```

On Windows, `ln -s` needs Developer Mode, and `.claude/` and `.agents/` are
ordinary folders in your home directory — the installer copies by default for
that reason. Add `--link` if you want edits to propagate and your system allows
symlinks.

For the web and desktop apps (claude.ai, ChatGPT), zip the skill folder and upload
it; there is no folder to copy into.

Restart the agent so it picks up the new skill. Verify with a prompt like "what
can quiz4everything do".

## Requirements

- Python 3.10+
- `pypdf` for PDFs (`pip install pypdf`), or `pdftotext` on `PATH`

Markdown and plain text need neither. Check what is available:

```bash
python3 -c "import pypdf; print('pypdf', pypdf.__version__)"
which pdftotext
```

If neither is present, `ingest.py --engine pypdf` fails with exit 2 rather than
producing a silently empty document.

On Windows use `python` where the examples say `python3`, and
`where pdftotext` instead of `which`. If `pdftotext` is not on `PATH`, either add
the poppler `bin` folder to it or rely on `pypdf`, which needs no external binary.

The scripts adapt to the console: on a GBK or cp1252 terminal they switch the
stream to UTF-8 when possible and otherwise substitute unencodable characters, so
Chinese section titles print instead of raising `UnicodeEncodeError` mid-session.

## Layout

```
quiz4everything/
  SKILL.md                     what the agent reads first
  references/
    item-generation.md         the generation contract
    item-schema.md             exact JSON, field by field
    item-quality.md            distractor craft, worked bad->good examples
    scheduling.md              what intervals mean, how ratings are derived
  scripts/
    _console.py                terminal encoding shim (GBK/cp1252 safe)
    ingest.py                  document -> text + section outline
    verify.py                  deterministic QA gate + adversarial prompt builder
    schedule.py                FSRS-5, pure functions
    session.py                 practice, review, stats, non-interactive answers
```

## Use it without an agent

The scripts are usable directly, and that is a supported path, not a fallback.

```bash
S=skills/quiz4everything/scripts

python3 $S/ingest.py paper.pdf --out document.json
python3 $S/ingest.py paper.pdf --stats          # just look at the sections

# write bank-s3.json by hand or with any model, then:
python3 $S/verify.py --doc document.json --bank bank-s3.json --report qa.json
python3 $S/session.py init --data quiz-data --doc document.json
python3 $S/session.py add  --data quiz-data --bank bank-s3.json
python3 $S/session.py practice --data quiz-data --section s3
python3 $S/session.py review   --data quiz-data
python3 $S/session.py stats    --data quiz-data
```

`verify.py` exits 1 if any item fails, and prints why. It is designed to be run
in a loop while writing items.

## Two ways to practise

**Interactive** — `practice` / `review` without `--json`. A terminal loop that
prompts, grades, prints feedback, and re-asks what you missed. Latency is
measured around the prompt, so "right but slow" is detected.

**Agent-driven** — `practice --json` returns the queue and records nothing;
`session.py answer --item ID --response ...` records each answer and returns the
feedback payload as JSON. Same grader, same event format. This is how the skill
works inside a chat, where there is no TTY.

Both write identical events to `events.jsonl`, which is the only source of
truth. Delete derived files freely; delete that log and the history is gone.

## What is deterministic

Everything that must not be improvised:

| stage | script | why not a model |
|---|---|---|
| text extraction, page and section offsets | `ingest.py` | offsets must match the file byte for byte |
| span verification | `verify.py` | a model cannot certify its own quote exists |
| option and key structure, coverage, dedupe | `verify.py` | mechanical |
| intervals, stability, due dates | `schedule.py` | arithmetic, and reproducible |
| grading of closed formats | `session.py` | same answer must score the same twice |
| mastery levels, guess correction | `session.py stats` | must be auditable |

A model writes items and judges whether a second answer is defensible. That is
the division.

## Tests

There is no test suite. Verification is by hand, deliberately and by hand:

```bash
python3 scripts/schedule.py --self-test      # 22 assertions
```

`--self-test` checks the scheduler's invariants: R(S)=0.9, monotonicity, interval
inversion, lapse behaviour, rating ordering, retention clamping.

For the other scripts the check is behavioural, on a small fixture: ingest a
two-page PDF and its `.md` twin, confirm both produce the same four sections;
verify a bank containing one item with a fabricated span and confirm exactly that
item is rejected.

Portability is checked the same way, by making the failure happen:

```bash
PYTHONIOENCODING=gbk  python3 scripts/session.py stats --data qd   # console
PYTHONIOENCODING=ascii python3 scripts/ingest.py 中文.md --stats     # console
python3 scripts/session.py practice --data qd < /dev/null           # no TTY -> exit 3
```

Each of those crashed or misfired before `_console.py` existed; they are the
regression checks for it.

## Status

Working, not hardened. Known limits:

- tables and figures are excluded rather than interpreted — the linear text
  loses their meaning, so items from them would test layout guessing
- one learner per `quiz-data` directory
- no bank versioning; re-adding a bank with the same `id` overwrites it
- English and Chinese prose are supported; the heading heuristic is weakest on
  dense two-column academic PDFs

The `docs/theory/06-open-questions.md` file is still the honest list of what
remains undecided — notably the testing protocol, which the user has not yet
specified.

## License

Apache-2.0. See [`../LICENSE`](../LICENSE).
