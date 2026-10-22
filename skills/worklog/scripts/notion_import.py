#!/usr/bin/env python3
"""Convert a Notion "Markdown & CSV" export of the four worklog databases into the vault layout.

    notion_import.py --export <dir> --vault <dir>

The layout and field names are defined in <vault>/Worklog/_schema.md. The export is only
read. Re-running overwrites files with identical content. Rows that cannot be mapped are
reported on stderr and the exit code is 1; nothing is dropped silently.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote

ID_RE = re.compile(r"([0-9a-f]{32})(?:\.(?:md|csv))?$")
REL_ID_RE = re.compile(r"([0-9a-f]{32})\.(?:md|csv)\)")
MD_LINK_RE = re.compile(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+\.md)\)")
NOTION_REF_RE = re.compile(r"\s*\([^()]*\.(?:csv|md)\)\s*$")
UNSAFE_NAME_RE = re.compile(r"[\[\]#^|\\/:]")
WEEK_RE = re.compile(r"^(\d{4}-W\d{2})")

PROJECT_STATUS = {"Active", "Paused", "Done"}
TICKET_STATUS = {"In progress", "Blocked", "Done"}
TICKET_TYPE = {"Feature", "Bug", "Incident", "Chore", "Research"}
WEEK_STATUS_RE = re.compile(r"^(Draft|Logged in .+)$")

PROPS = {
    "Worklog Projects": ["Description", "Repos", "Sessions", "Status", "Ticket prefix", "Tickets"],
    "Worklog Tickets": [
        "Branch", "Key", "Last session", "Links", "Project", "Repos", "Sessions", "Status",
        "Ticket ID", "Type",
    ],
    "Worklog Sessions": ["Date", "Project", "Summary", "Ticket"],
    "Worklog Weeks": ["Status", "Week start"],
}


@dataclass
class Page:
    notion_id: str
    title: str
    props: dict[str, str]
    body: str
    path: Path


@dataclass
class Report:
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.issues.append(msg)

    def warn(self, msg: str) -> None:
        """Data was converted as-is; the note is informational and does not fail the run."""
        self.warnings.append(msg)


def safe_name(text: str, limit: int = 100) -> str:
    name = " ".join(UNSAFE_NAME_RE.sub("", text).split())
    if len(name) <= limit:
        return name
    cut = name[:limit]
    if name[limit] != " " and " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip()


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%B %d, %Y").date()


def yaml_str(value: str) -> str:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ./_-]*", value) and value.lower() not in {
        "true", "false", "null", "yes", "no", "on", "off",
    }:
        return value
    return json.dumps(value, ensure_ascii=False)


def frontmatter(fields: list[tuple[str, object]]) -> str:
    lines = ["---"]
    for key, val in fields:
        if val is None or val == "" or (val == [] and key not in {"repos", "links"}):
            continue
        if isinstance(val, list):
            if not val:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            lines.extend(f"  - {yaml_str(v)}" for v in val)
        elif isinstance(val, date):
            lines.append(f"{key}: {val.isoformat()}")
        else:
            lines.append(f"{key}: {yaml_str(str(val))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def split_page(text: str, prop_names: list[str] | None) -> tuple[str, dict[str, str], str]:
    """Return (title, properties, body). Strips the `# Title` line and the property block."""
    lines = text.lstrip("﻿").split("\n")
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    props: dict[str, str] = {}
    if prop_names:
        names = {n for n in prop_names}
        current = None
        i = 0
        while i < len(lines) and lines[i].strip():
            m = re.match(r"^([A-Z][A-Za-z ]*?): ?(.*)$", lines[i])
            if m and m.group(1) in names:
                current = m.group(1)
                props[current] = m.group(2)
            elif current:
                props[current] += "\n" + lines[i]
            else:
                break
            i += 1
        lines = lines[i:]
    return title, props, "\n".join(lines).strip("\n")


def read_pages(db_dir: Path, db: str) -> list[Page]:
    pages = []
    for path in sorted(db_dir.glob("*.md")):
        m = ID_RE.search(path.stem)
        if not m:
            continue
        title, props, body = split_page(path.read_text(encoding="utf-8"), PROPS[db])
        pages.append(Page(m.group(1), title, props, body, path))
    return pages


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def relation_ids(value: str) -> list[str]:
    return REL_ID_RE.findall(value or "")


def find_db(root: Path, db: str) -> tuple[Path, Path] | None:
    dirs = [p for p in root.rglob(db) if p.is_dir()]
    csvs = [p for p in root.rglob(f"{db} *.csv") if not p.stem.endswith("_all")]
    if not dirs or not csvs:
        return None
    return dirs[0], csvs[0]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def split_links(value: str) -> list[str]:
    """One entry per line; trailing Notion page references are dropped, free text is kept."""
    lines = (NOTION_REF_RE.sub("", ln).strip() for ln in value.splitlines())
    return [ln for ln in lines if ln]


def rewrite_links(body: str, targets: dict[str, str], where: str, report: Report) -> str:
    def repl(m: re.Match[str]) -> str:
        text, href = m.group(1).replace("[", "").replace("]", ""), unquote(m.group(2))
        id_match = ID_RE.search(Path(href).stem)
        if not id_match:
            return m.group(0)
        stem = targets.get(id_match.group(1))
        if stem is None:
            report.add(f"{where}: internal link to unknown page {href!r}; kept the link text only")
            return text
        return f"[[{stem}]]" if not text or text == stem else f"[[{stem}|{text}]]"

    return MD_LINK_RE.sub(repl, body)


def check_select(value: str, allowed: set[str], label: str, where: str, report: Report) -> None:
    if value and value not in allowed:
        report.add(f"{where}: unknown {label} {value!r}")


def convert(export: Path, vault: Path) -> tuple[Report, dict[str, int]]:
    report = Report()
    counts: dict[str, int] = {}
    wl = vault / "Worklog"
    dbs: dict[str, tuple[Path, Path]] = {}
    for db in PROPS:
        found = find_db(export, db)
        if found is None:
            report.add(f"{db}: folder or CSV not found in the export")
            continue
        dbs[db] = found

    pages = {db: read_pages(d, db) for db, (d, _) in dbs.items()}
    for db, (_, csv_path) in dbs.items():
        rows = read_csv(csv_path)
        names_csv = sorted(r["Name"] for r in rows)
        names_md = sorted(p.title for p in pages[db])
        if len(rows) != len(pages[db]):
            report.add(f"{db}: {len(rows)} CSV rows but {len(pages[db])} pages")
        elif names_csv != names_md:
            report.add(f"{db}: CSV row names differ from page titles")

    # ---- Projects
    project_stem: dict[str, str] = {}
    for p in pages.get("Worklog Projects", []):
        stem = safe_name(p.title)
        project_stem[p.notion_id] = stem
        status = p.props.get("Status", "")
        check_select(status, PROJECT_STATUS, "project status", f"project {p.title}", report)
        repos = [r.strip() for r in p.props.get("Repos", "").split("\n") if r.strip()]
        write(wl / "Projects" / f"{stem}.md", frontmatter([
            ("type", "project"), ("repos", repos), ("ticket_prefix", p.props.get("Ticket prefix", "")),
            ("status", status), ("description", " ".join(p.props.get("Description", "").split())),
        ]))
        counts["projects"] = counts.get("projects", 0) + 1

    # ---- Tickets
    ticket_stem: dict[str, str] = {}
    ticket_key: dict[str, str] = {}
    ticket_project: dict[str, str] = {}
    targets: dict[str, str] = {}
    ticket_pages = pages.get("Worklog Tickets", [])
    valid_tickets = []
    seen_keys: dict[str, str] = {}
    for p in ticket_pages:
        where = f"ticket {p.title!r}"
        key = p.props.get("Key", "").strip()
        proj_ids = relation_ids(p.props.get("Project", ""))
        if not key:
            report.add(f"{where}: no Key, row not converted")
            continue
        if key in seen_keys:
            report.add(f"{where}: duplicate Key {key!r} (also {seen_keys[key]!r}), row not converted")
            continue
        if not proj_ids or proj_ids[0] not in project_stem:
            report.add(f"{where}: Project relation missing or unknown, row not converted")
            continue
        seen_keys[key] = p.title
        stem = safe_name(f"{key} - {p.title}")
        ticket_stem[p.notion_id] = stem
        ticket_key[p.notion_id] = key
        ticket_project[p.notion_id] = project_stem[proj_ids[0]]
        targets[p.notion_id] = stem
        valid_tickets.append(p)

    child_pages: list[tuple[Page, Page]] = []
    for p in valid_tickets:
        child_dir = p.path.with_suffix("")
        if not child_dir.is_dir():
            # Notion truncates folder names differently from file names; match on the title prefix.
            base = p.path.name.rsplit(" ", 1)[0]
            child_dir = next((d for d in p.path.parent.iterdir() if d.is_dir() and base.startswith(d.name)), child_dir)
        if child_dir.is_dir():
            for cp in sorted(child_dir.glob("*.md")):
                m = ID_RE.search(cp.stem)
                if not m:
                    continue
                title, _, body = split_page(cp.read_text(encoding="utf-8"), None)
                child = Page(m.group(1), title, {}, body, cp)
                targets[child.notion_id] = safe_name(title)
                child_pages.append((p, child))

    for p in valid_tickets:
        where = f"ticket {p.title!r}"
        status = p.props.get("Status", "")
        ttype = p.props.get("Type", "")
        check_select(status, TICKET_STATUS, "ticket status", where, report)
        check_select(ttype, TICKET_TYPE, "ticket type", where, report)
        last = p.props.get("Last session", "").strip()
        body = rewrite_links(p.body, targets, where, report)
        write(wl / "Tickets" / ticket_project[p.notion_id] / f"{ticket_stem[p.notion_id]}.md",
              frontmatter([
                  ("type", "ticket"), ("title", p.title), ("ticket_id", p.props.get("Ticket ID", "")),
                  ("key", ticket_key[p.notion_id]),
                  ("project", f"[[{ticket_project[p.notion_id]}]]"), ("status", status),
                  ("ticket_type", ttype),
                  ("repos", [r.strip() for r in p.props.get("Repos", "").split("\n") if r.strip()]),
                  ("branch", p.props.get("Branch", "").strip()),
                  ("links", split_links(p.props.get("Links", ""))),
                  ("last_session", parse_date(last) if last else None),
              ]) + "\n" + body + "\n")
        counts["tickets"] = counts.get("tickets", 0) + 1

    for parent, child in child_pages:
        body = rewrite_links(child.body, targets, f"subpage {child.title!r}", report)
        write(wl / "Tickets" / ticket_project[parent.notion_id] / ticket_stem[parent.notion_id]
              / f"{safe_name(child.title)}.md",
              frontmatter([
                  ("type", "ticket_note"), ("title", child.title),
                  ("ticket", f"[[{ticket_stem[parent.notion_id]}]]"),
              ]) + "\n" + body + "\n")
        counts["ticket subpages"] = counts.get("ticket subpages", 0) + 1

    # ---- Sessions
    written: dict[str, Page] = {}
    for p in pages.get("Worklog Sessions", []):
        where = f"session {p.title!r}"
        t_ids = relation_ids(p.props.get("Ticket", ""))
        pr_ids = relation_ids(p.props.get("Project", ""))
        if not t_ids or t_ids[0] not in ticket_stem:
            report.add(f"{where}: Ticket relation missing or unknown, row not converted")
            continue
        if not pr_ids or pr_ids[0] not in project_stem:
            report.add(f"{where}: Project relation missing or unknown, row not converted")
            continue
        raw_date = p.props.get("Date", "").strip()
        try:
            day = parse_date(raw_date)
        except ValueError:
            report.add(f"{where}: unparseable Date {raw_date!r}, row not converted")
            continue
        summary = " ".join(p.props.get("Summary", "").split())
        if len(summary) > 120:
            report.warn(f"{where}: summary is {len(summary)} characters (limit 120), kept as is")
        name = f"{day.isoformat()} {ticket_key[t_ids[0]]}"
        if name in written:
            report.add(f"{where}: second session for {name}; summaries merged")
            prev = written[name]
            summary = f"{prev.props['Summary']}; {summary}"
        p.props["Summary"] = summary
        written[name] = p
        write(wl / "Sessions" / f"{name}.md", frontmatter([
            ("type", "session"), ("date", day), ("ticket", f"[[{ticket_stem[t_ids[0]]}]]"),
            ("project", f"[[{project_stem[pr_ids[0]]}]]"), ("summary", summary),
        ]))
    counts["sessions"] = len(written)

    # ---- Weeks
    for p in pages.get("Worklog Weeks", []):
        where = f"week {p.title!r}"
        m = WEEK_RE.match(p.title)
        raw = p.props.get("Week start", "").strip()
        if not m or not raw:
            report.add(f"{where}: no week id in the name or no Week start, row not converted")
            continue
        status = p.props.get("Status", "")
        if status and not WEEK_STATUS_RE.match(status):
            report.add(f"{where}: unknown week status {status!r}")
        write(wl / "Weeks" / f"{m.group(1)}.md", frontmatter([
            ("type", "week"), ("title", p.title), ("week_start", parse_date(raw)), ("status", status),
        ]) + "\n" + p.body + "\n")
        counts["weeks"] = counts.get("weeks", 0) + 1

    return report, counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", type=Path, required=True, help="unzipped Notion export directory")
    ap.add_argument("--vault", type=Path, required=True, help="Obsidian vault root")
    args = ap.parse_args(argv)
    if not args.export.is_dir():
        print(f"error: export directory not found: {args.export}", file=sys.stderr)
        return 2
    report, counts = convert(args.export, args.vault)
    print("converted: " + ", ".join(f"{n} {k}" for k, n in counts.items()))
    for note in report.warnings:
        print(f"note: {note}", file=sys.stderr)
    for issue in report.issues:
        print(f"UNMAPPED: {issue}", file=sys.stderr)
    return 1 if report.issues else 0


if __name__ == "__main__":
    sys.exit(main())
