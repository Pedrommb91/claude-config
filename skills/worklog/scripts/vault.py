#!/usr/bin/env python3
"""Read/write helper for the Obsidian worklog vault (contract: Worklog/_schema.md).

All subcommands print JSON on stdout. Errors go to stderr with exit code 1.
The vault folder comes from --vault, else `vault_path` in ~/.claude/worklog.config.json.

  find-project --repo owner/repo
  find-ticket --project NAME (--id PROJ-1 | --key proj-1)
  list-tickets --project NAME [--status "In progress"]
  sessions --from YYYY-MM-DD --to YYYY-MM-DD
  upsert-session --project NAME (--id PROJ-1 | --key proj-1) --date YYYY-MM-DD --summary TEXT
  find-week (--week 2026-W40 | --date YYYY-MM-DD)

Only the standard library is used. The frontmatter parser handles the subset of YAML that
_schema.md allows: scalars, JSON-quoted strings, and block lists of scalars.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "worklog.config.json"
FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
WIKILINK_RE = re.compile(r"^\[\[([^\]]+)\]\]$")
SUMMARY_MAX = 120
MERGED_SUMMARY_MAX = 160


class VaultError(Exception):
    pass


# --- frontmatter ---------------------------------------------------------------------------


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"'):
        return json.loads(raw)
    return raw


def parse_note(text: str) -> tuple[dict[str, object], str]:
    """Return (frontmatter, body). Lists become list[str], everything else str."""
    m = FM_RE.match(text.lstrip("﻿"))
    if not m:
        return {}, text
    fields: dict[str, object] = {}
    key: str | None = None
    for line in m.group(1).split("\n"):
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None:
            lst = fields.setdefault(key, [])
            if isinstance(lst, list):
                lst.append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$", line)
        if not kv:
            continue
        key = kv.group(1)
        val = kv.group(2)
        if not val or val == "[]":
            fields[key] = []
        else:
            fields[key] = _scalar(val)
    return fields, m.group(2)


def yaml_str(value: str) -> str:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ./_-]*", value) and value.lower() not in {
        "true", "false", "null", "yes", "no", "on", "off",
    }:
        return value
    return json.dumps(value, ensure_ascii=False)


def render_note(fields: list[tuple[str, str]], body: str = "") -> str:
    lines = ["---"]
    for key, val in fields:
        if key == "date" or key == "last_session":
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {yaml_str(val)}")
    lines.append("---")
    out = "\n".join(lines) + "\n"
    return out + (body if body else "")


def read_note(path: Path) -> tuple[dict[str, object], str]:
    return parse_note(path.read_text(encoding="utf-8"))


def as_list(value: object) -> list[str]:
    return value if isinstance(value, list) else ([value] if value else [])


def as_str(value: object) -> str:
    return value if isinstance(value, str) else ""


# --- vault access --------------------------------------------------------------------------


def resolve_vault(arg: str | None) -> Path:
    raw = arg
    if not raw:
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("vault_path", "")
        except (OSError, ValueError):
            raw = ""
    if not raw:
        raise VaultError("no vault: pass --vault or set vault_path with setup.py")
    root = Path(raw).expanduser() / "Worklog"
    if not root.is_dir():
        raise VaultError(f"{root} does not exist")
    return root


def link_target(value: object) -> str:
    m = WIKILINK_RE.match(as_str(value))
    return m.group(1) if m else as_str(value)


def display_label(ticket_id: str, title: str) -> str:
    return f"[{ticket_id}] {title}" if ticket_id else title


def ticket_info(path: Path, fm: dict[str, object]) -> dict[str, object]:
    ticket_id = as_str(fm.get("ticket_id"))
    title = as_str(fm.get("title"))
    return {
        "file": path.stem,
        "path": str(path),
        "title": title,
        "ticket_id": ticket_id,
        "key": as_str(fm.get("key")),
        "label": display_label(ticket_id, title),
        "project": link_target(fm.get("project")),
        "status": as_str(fm.get("status")),
        "ticket_type": as_str(fm.get("ticket_type")),
        "repos": as_list(fm.get("repos")),
        "branch": as_str(fm.get("branch")),
        "links": as_list(fm.get("links")),
        "last_session": as_str(fm.get("last_session")),
    }


def all_tickets(root: Path) -> list[dict[str, object]]:
    out = []
    for path in sorted((root / "Tickets").glob("*/*.md")):
        fm, _ = read_note(path)
        if fm.get("type") == "ticket":
            out.append(ticket_info(path, fm))
    return out


def project_tickets(root: Path, project: str) -> list[dict[str, object]]:
    return [t for t in all_tickets(root) if t["project"].lower() == project.lower()]


def pick_ticket(
    root: Path, project: str, ticket_id: str | None, key: str | None
) -> dict[str, object] | None:
    """Ticket ID first, then key, within one project."""
    tickets = project_tickets(root, project)
    if ticket_id:
        hits = [t for t in tickets if str(t["ticket_id"]).lower() == ticket_id.lower()]
        if hits:
            return _only(hits, f"ticket id {ticket_id}")
    if key:
        hits = [t for t in tickets if str(t["key"]).lower() == key.lower()]
        if hits:
            return _only(hits, f"key {key}")
    return None


def _only(hits: list[dict[str, object]], what: str) -> dict[str, object]:
    if len(hits) > 1:
        names = ", ".join(str(h["file"]) for h in hits)
        raise VaultError(f"duplicate tickets for {what}: {names}")
    return hits[0]


# --- subcommands ---------------------------------------------------------------------------


def cmd_find_project(root: Path, args: argparse.Namespace) -> dict[str, object]:
    repo = args.repo.strip().lower()
    matches = []
    for path in sorted((root / "Projects").glob("*.md")):
        fm, _ = read_note(path)
        repos = [r.strip().lower() for r in as_list(fm.get("repos"))]
        if repo in repos:
            matches.append(
                {
                    "name": path.stem,
                    "path": str(path),
                    "ticket_prefix": as_str(fm.get("ticket_prefix")),
                    "status": as_str(fm.get("status")),
                    "repos": as_list(fm.get("repos")),
                }
            )
    return {"matches": matches}


def cmd_find_ticket(root: Path, args: argparse.Namespace) -> dict[str, object]:
    if not (args.id or args.key):
        raise VaultError("find-ticket needs --id or --key")
    return {"match": pick_ticket(root, args.project, args.id, args.key)}


def cmd_list_tickets(root: Path, args: argparse.Namespace) -> dict[str, object]:
    tickets = project_tickets(root, args.project)
    if args.status:
        tickets = [t for t in tickets if t["status"] == args.status]
    return {"tickets": tickets}


def id_sort_key(ticket_id: str) -> tuple[str, int]:
    m = re.match(r"^(.*?)-?(\d+)$", ticket_id)
    return (m.group(1).lower(), int(m.group(2))) if m else (ticket_id.lower(), 0)


def cmd_sessions(root: Path, args: argparse.Namespace) -> dict[str, object]:
    start, end = date.fromisoformat(args.from_), date.fromisoformat(args.to)
    tickets = {str(t["file"]): t for t in all_tickets(root)}
    rows = []
    for path in sorted((root / "Sessions").glob("*.md")):
        fm, _ = read_note(path)
        if fm.get("type") != "session":
            continue
        day = as_str(fm.get("date"))
        if not (start <= date.fromisoformat(day) <= end):
            continue
        ticket = tickets.get(link_target(fm.get("ticket")))
        rows.append(
            {
                "date": day,
                "path": str(path),
                "ticket_file": link_target(fm.get("ticket")),
                "ticket_found": ticket is not None,
                "ticket_id": ticket["ticket_id"] if ticket else "",
                "title": ticket["title"] if ticket else "",
                "label": ticket["label"] if ticket else path.stem,
                "project": link_target(fm.get("project")),
                "summary": as_str(fm.get("summary")),
            }
        )
    rows.sort(
        key=lambda r: (
            r["date"],
            str(r["project"]).lower(),
            id_sort_key(str(r["ticket_id"])),
            str(r["title"]).lower(),
        )
    )
    return {"sessions": rows}


def merge_summaries(old: str, new: str) -> str:
    if not old:
        return new
    if new.lower() in old.lower():
        return old
    if old.lower() in new.lower():
        return new
    merged = f"{old.rstrip('. ')}; {new[0].lower() + new[1:]}" if new else old
    if len(merged) > MERGED_SUMMARY_MAX:
        raise VaultError(
            f"merged summary is {len(merged)} chars (max {MERGED_SUMMARY_MAX}); shorten it"
        )
    return merged


def set_last_session(path: Path, day: str) -> bool:
    """Set `last_session` if `day` is newer. Edits only that line, so the rest stays as is."""
    text = path.read_text(encoding="utf-8")
    fm, _ = parse_note(text)
    current = as_str(fm.get("last_session"))
    if current and current >= day:
        return False
    if current:
        text = re.sub(r"(?m)^last_session:.*$", f"last_session: {day}", text, count=1)
    else:
        text = text.replace("\n---\n", f"\nlast_session: {day}\n---\n", 1)
    path.write_text(text, encoding="utf-8")
    return True


def cmd_upsert_session(root: Path, args: argparse.Namespace) -> dict[str, object]:
    day = date.fromisoformat(args.date).isoformat()
    summary = " ".join(args.summary.split())
    ticket = pick_ticket(root, args.project, args.id, args.key)
    if ticket is None:
        raise VaultError("ticket not found; create it first")
    path = root / "Sessions" / f"{day} {ticket['key']}.md"
    fields = [
        ("type", "session"),
        ("date", day),
        ("ticket", f"[[{ticket['file']}]]"),
        ("project", f"[[{ticket['project']}]]"),
    ]
    if path.exists():
        fm, body = read_note(path)
        old = as_str(fm.get("summary"))
        final = merge_summaries(old, summary)
        action = "unchanged" if final == old else "merged"
        path.write_text(render_note([*fields, ("summary", final)], body), encoding="utf-8")
    else:
        if len(summary) > SUMMARY_MAX:
            raise VaultError(f"summary is {len(summary)} chars (max {SUMMARY_MAX}); shorten it")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_note([*fields, ("summary", summary)]), encoding="utf-8")
        action, final = "created", summary
    bumped = set_last_session(Path(str(ticket["path"])), day)
    return {
        "action": action,
        "path": str(path),
        "summary": final,
        "ticket": ticket["file"],
        "last_session_updated": bumped,
    }


def iso_week_info(monday: date) -> dict[str, object]:
    year, week, _ = monday.isocalendar()
    sunday = monday + timedelta(days=6)

    def fmt(d: date) -> str:  # no %-d: it is not portable
        return f"{d.day} {d.strftime('%b')}"

    return {
        "week": f"{year}-W{week:02d}",
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "title": f"{year}-W{week:02d} · {fmt(monday)} – {fmt(sunday)}",
    }


def cmd_find_week(root: Path, args: argparse.Namespace) -> dict[str, object]:
    if args.week:
        year, week = args.week.upper().split("-W")
        monday = date.fromisocalendar(int(year), int(week), 1)
    elif args.date:
        d = date.fromisoformat(args.date)
        monday = d - timedelta(days=d.weekday())
    else:
        raise VaultError("find-week needs --week or --date")
    info = iso_week_info(monday)
    path = root / "Weeks" / f"{info['week']}.md"
    info["path"] = str(path)
    info["exists"] = path.exists()
    info["status"] = ""
    if path.exists():
        fm, _ = read_note(path)
        info["status"] = as_str(fm.get("status"))
    return info


# --- cli -----------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--vault", help="vault folder (contains Worklog/); default from config")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("find-project")
    s.add_argument("--repo", required=True)
    s.set_defaults(fn=cmd_find_project)

    s = sub.add_parser("find-ticket")
    s.add_argument("--project", required=True)
    s.add_argument("--id")
    s.add_argument("--key")
    s.set_defaults(fn=cmd_find_ticket)

    s = sub.add_parser("list-tickets")
    s.add_argument("--project", required=True)
    s.add_argument("--status")
    s.set_defaults(fn=cmd_list_tickets)

    s = sub.add_parser("sessions")
    s.add_argument("--from", dest="from_", required=True)
    s.add_argument("--to", required=True)
    s.set_defaults(fn=cmd_sessions)

    s = sub.add_parser("upsert-session")
    s.add_argument("--project", required=True)
    s.add_argument("--id")
    s.add_argument("--key")
    s.add_argument("--date", required=True)
    s.add_argument("--summary", required=True)
    s.set_defaults(fn=cmd_upsert_session)

    s = sub.add_parser("find-week")
    s.add_argument("--week")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_find_week)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.fn(resolve_vault(args.vault), args)
    except (VaultError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
