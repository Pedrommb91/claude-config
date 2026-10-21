#!/usr/bin/env python3
"""Collect what the user worked on for given past day(s), for /worklog backfill.

Read-only. For each day it prints, as Markdown:
  - commits authored by the user in every git repo under the search roots
  - branch checkouts from the reflog (work that may not have been committed)
  - Claude Code transcript excerpts (user prompts and assistant replies) from that day

Usage:
  backfill_sources.py 2026-09-29 [2026-09-30 ...] [--roots DIR ...]  (default: repos_roots from the worklog config)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

PROJECTS_DIR = Path.home() / ".claude" / "projects"
SKIP_DIRS = {"node_modules", ".terraform", ".venv", "venv", "vendor", "target", "dist", "build"}
TAG_RE = re.compile(r"<(system-reminder|ide_[a-z_]+|command-[a-z-]+|local-command-[a-z-]+)>.*?</\1>", re.S)
MSG_CHARS = 600
SESSION_CHARS = 8000


def run(cmd: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout if out.returncode == 0 else ""


def find_repos(roots: list[Path], max_depth: int = 3) -> list[Path]:
    repos: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if (d / ".git").exists():
            repos.append(d)
            return
        if depth >= max_depth:
            return
        try:
            children = sorted(p for p in d.iterdir() if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith("."))
        except OSError:
            return
        for c in children:
            walk(c, depth + 1)

    for r in roots:
        if r.is_dir():
            walk(r, 0)
    return repos


def repo_id(repo: Path) -> str:
    url = run(["git", "remote", "get-url", "origin"], repo).strip()
    if not url:
        return repo.name.lower()
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^[a-z+]+://[^/]+/", "", url)  # https://host/owner/repo
    url = re.sub(r"^[^@]+@[^:]+:", "", url)  # git@host:owner/repo
    return url.lower()


def git_activity(repo: Path, day: dt.date) -> tuple[list[str], list[str]]:
    email = run(["git", "config", "user.email"], repo).strip()
    name = run(["git", "config", "user.name"], repo).strip()
    authors = [f"--author={a}" for a in (email, name) if a]
    if not authors:
        return [], []
    since, until = f"{day} 00:00:00", f"{day} 23:59:59"
    commits = run(
        ["git", "log", "--all", "--source", *authors, f"--since={since}", f"--until={until}",
         "--date=format-local:%H:%M", "--format=%ad %h [%S] %s"],
        repo,
    ).splitlines()
    reflog = [
        line for line in run(["git", "log", "-g", "--date=iso-local", "--format=%gd|%gs"], repo).splitlines()
        if str(day) in line and "checkout:" in line
    ]
    checkouts = []
    for line in reflog:
        when, _, what = line.partition("|")
        m = re.search(r"(\d{2}:\d{2}):\d{2}", when)
        checkouts.append(f"{m.group(1) if m else '?'} {what.strip()}")
    return commits, sorted(checkouts)


def text_of(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    else:
        parts = []
    text = TAG_RE.sub("", "\n".join(parts)).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def transcripts(day: dt.date, roots: list[Path]) -> dict[tuple[str, str], list[str]]:
    """(cwd, git branch) -> transcript lines from that local day, for sessions under the roots."""
    found: dict[tuple[str, str], list[str]] = defaultdict(list)
    if not PROJECTS_DIR.is_dir():
        return found
    day_start = dt.datetime.combine(day, dt.time.min).timestamp()
    for f in PROJECTS_DIR.glob("*/*.jsonl"):
        try:
            if f.stat().st_mtime < day_start:
                continue  # not touched since the day began
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        used = 0
        for line in lines:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") not in ("user", "assistant") or o.get("isSidechain") or o.get("isMeta"):
                continue
            cwd = o.get("cwd", "")
            if not any(Path(cwd).is_relative_to(r) for r in roots):
                continue  # e.g. personal projects outside the work roots
            ts = o.get("timestamp")
            if not ts:
                continue
            try:
                local = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            except ValueError:
                continue
            if local.date() != day:
                continue
            text = text_of(o.get("message") or {})
            if not text or used >= SESSION_CHARS:
                continue
            text = text[:MSG_CHARS] + (" …" if len(text) > MSG_CHARS else "")
            used += len(text)
            who = "USER" if o["type"] == "user" else "CLAUDE"
            found[(cwd, o.get("gitBranch") or "?")].append(f"{local:%H:%M} {who}: {text}")
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("days", nargs="+", type=dt.date.fromisoformat, help="YYYY-MM-DD")
    ap.add_argument("--roots", nargs="+", help="folders containing git repos")
    args = ap.parse_args()

    if not args.roots:
        args.roots = [str(r) for r in config.repos_roots()]
    if not args.roots:
        ap.error("no folders to scan: pass --roots or set repos_roots via setup.py")

    roots = [Path(r).expanduser().resolve() for r in args.roots]
    repos = find_repos(roots)
    for day in sorted(set(args.days)):
        print(f"# {day:%a %d %b %Y}\n")
        any_git = False
        for repo in repos:
            commits, checkouts = git_activity(repo, day)
            if not commits and not checkouts:
                continue
            any_git = True
            print(f"## {repo_id(repo)}  ({repo})")
            for c in commits:
                print(f"- commit {c}")
            for c in checkouts:
                print(f"- {c}")
            print()
        if not any_git:
            print("_No commits or checkouts found._\n")

        sessions = transcripts(day, roots)
        if not sessions:
            print("_No Claude Code transcripts from this day._\n")
        for (cwd, branch), lines in sorted(sessions.items()):
            print(f"## Transcript: {cwd} (branch {branch})")
            for line in lines:
                print("    " + line.replace("\n", "\n    "))
            print()


if __name__ == "__main__":
    main()
