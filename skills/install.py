#!/usr/bin/env python3
"""Install quiz4everything into one or more agents' skill directories.

Skill *format* is portable; skill *location* is not. Every agent scans its own
folder, so this script just puts the same folder in the right places.

Defaults to copying rather than symlinking, because `ln -s` fails on Windows
without Developer Mode or an elevated shell, and a copy is what the web/desktop
upload flows want anyway. Use --link if you want edits to propagate.

Usage
    python3 install.py --list
    python3 install.py                      # every agent detected on this machine
    python3 install.py --agent claude,codex
    python3 install.py --agent all --project ~/src/notes
    python3 install.py --agent claude --link
    python3 install.py --agent claude --uninstall

Exit codes: 0 ok, 1 nothing installed, 2 bad input.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

SKILL_NAME = "quiz4everything"
HERE = Path(__file__).resolve().parent
SOURCE = HERE / SKILL_NAME

# Where each agent looks. Personal = whole machine; project = one repo.
# Sourced from each vendor's docs (checked 2026-11). Several agents deliberately
# read each other's folders, which is why .agents/ and .claude/ cover the most.
AGENTS: dict[str, dict] = {
    "claude": {
        "label": "Claude Code",
        "personal": ".claude/skills",
        "project": ".claude/skills",
    },
    "codex": {
        "label": "OpenAI Codex",
        "personal": ".agents/skills",
        "project": ".agents/skills",
    },
    "cursor": {
        "label": "Cursor",
        "personal": ".cursor/skills",
        "project": ".agents/skills",
    },
    "gemini": {
        "label": "Gemini CLI",
        "personal": ".gemini/skills",
        "project": ".agents/skills",
    },
    "copilot": {
        "label": "GitHub Copilot / VS Code",
        "personal": ".copilot/skills",
        "project": ".github/skills",
    },
    "opencode": {
        "label": "OpenCode",
        "personal": ".config/opencode/skills",
        "project": ".agents/skills",
    },
}

# Agents whose personal dir is built from XDG-ish conventions on Linux/macOS but
# APPDATA on Windows. Only opencode differs meaningfully.
WINDOWS_PERSONAL = {
    "opencode": ("APPDATA", "opencode/skills"),
}


def personal_dir(agent: str) -> Path:
    if sys.platform == "win32" and agent in WINDOWS_PERSONAL:
        env, rest = WINDOWS_PERSONAL[agent]
        base = os.environ.get(env)
        if base:
            return Path(base) / rest
    return Path.home() / AGENTS[agent]["personal"]


def project_dir(agent: str, root: Path) -> Path:
    return root / AGENTS[agent]["project"]


def known_agents() -> list[str]:
    """Agents that appear to be installed, by looking for their config folder."""
    found = []
    for name in AGENTS:
        marker = Path.home() / ("." + ("config/opencode" if name == "opencode" else name))
        if marker.exists():
            found.append(name)
    return found


def _replace(dest: Path, use_link: bool) -> None:
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if use_link:
        try:
            os.symlink(SOURCE, dest, target_is_directory=True)
            return
        except (OSError, NotImplementedError):
            print(f"  ! symlink refused, copying instead ({dest})", file=sys.stderr)
    shutil.copytree(
        SOURCE,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def install(agent: str, scope: str, root: Path, use_link: bool) -> Path:
    dest = (personal_dir(agent) if scope == "personal" else project_dir(agent, root)) / SKILL_NAME
    _replace(dest, use_link)
    return dest


def uninstall(agent: str, scope: str, root: Path) -> bool:
    dest = (personal_dir(agent) if scope == "personal" else project_dir(agent, root)) / SKILL_NAME
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
        return True
    if dest.is_dir():
        shutil.rmtree(dest)
        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Install the quiz4everything skill for one or more coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Agents: " + ", ".join(f"{k} ({v['label']})" for k, v in AGENTS.items()),
    )
    ap.add_argument("--agent", default=None,
                    help="comma-separated agent names, or 'all' (default: detected)")
    ap.add_argument("--project", default=None,
                    help="install into this repo instead of your user folder")
    ap.add_argument("--link", action="store_true",
                    help="symlink instead of copy (needs Developer Mode on Windows)")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--list", action="store_true", help="show agents and target paths")
    args = ap.parse_args(argv)

    if not SOURCE.is_dir() or not (SOURCE / "SKILL.md").is_file():
        print(f"error: {SOURCE} does not look like a skill (no SKILL.md)", file=sys.stderr)
        return 2

    if args.list:
        print(f"source: {SOURCE}")
        for name, meta in AGENTS.items():
            print(f"  {name:9} {meta['label']:26} personal: {personal_dir(name)}")
        print(f"\ndetected on this machine: {', '.join(known_agents()) or 'none'}")
        return 0

    if args.agent in (None, "", "detected"):
        targets = known_agents()
        if not targets:
            print("error: no agent detected. Pass --agent (see --list).", file=sys.stderr)
            return 1
    elif args.agent == "all":
        targets = list(AGENTS)
    else:
        targets = [t.strip() for t in args.agent.split(",") if t.strip()]

    bad = [t for t in targets if t not in AGENTS]
    if bad:
        print(f"error: unknown agent(s): {', '.join(bad)}", file=sys.stderr)
        print("known: " + ", ".join(AGENTS), file=sys.stderr)
        return 2

    scope = "project" if args.project else "personal"
    root = Path(args.project).expanduser().resolve() if args.project else Path.cwd()

    action = "uninstall" if args.uninstall else "install"
    mode = "symlink" if (args.link and not args.uninstall) else "copy"
    print(f"{action}: {SKILL_NAME} ({scope}, {mode})")
    done = 0
    for name in targets:
        if args.uninstall:
            ok = uninstall(name, scope, root)
            print(f"  {'removed ' if ok else 'absent  '}{name:9} -> "
                  f"{(personal_dir(name) if scope == 'personal' else project_dir(name, root)) / SKILL_NAME}")
            done += 1 if ok else 0
        else:
            dest = install(name, scope, root, args.link)
            print(f"  installed {name:9} -> {dest}")
            done += 1

    if not done:
        print("nothing to do.", file=sys.stderr)
        return 1

    print("\nRestart the agent (or its skill list) to pick up the change.")
    print("Verify by asking: what can quiz4everything do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
