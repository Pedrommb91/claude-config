"""Tests for notion_import.py. The fixture mimics the export structure with made-up data."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import notion_import as ni

PROJ_ID = "a" * 32
TICKET_ID = "b" * 32
CHILD_ID = "c" * 32
SESSION_ID = "d" * 32
WEEK_ID = "e" * 32


def _csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def make_export(root: Path, *, break_session_ticket: bool = False) -> Path:
    wl = root / "Worklog"
    for db in ni.PROPS:
        (wl / db).mkdir(parents=True)
    proj_rel = f"Demo (../Worklog%20Projects/Demo%20{PROJ_ID}.md)"
    ticket_rel = f"[Fix thing] (../Worklog%20Tickets/%5BFix%20thing%5D%20{TICKET_ID}.md)"
    if break_session_ticket:
        ticket_rel = f"[Gone] (../Worklog%20Tickets/Gone%20{'f' * 32}.md)"

    _csv(wl / f"Worklog Projects {'1' * 32}.csv", ["Name", "Status"], [["Demo", "Active"]])
    (wl / "Worklog Projects" / f"Demo {PROJ_ID}.md").write_text(
        "# Demo\n\nDescription: Demo project\nRepos: acme/one\nacme/two\nStatus: Active\n"
        "Ticket prefix: DEM\n"
    )
    _csv(wl / f"Worklog Tickets {'2' * 32}.csv", ["Name", "Key"], [["[Fix thing]", "dem-1"]])
    (wl / "Worklog Tickets" / f"[Fix thing] {TICKET_ID}.md").write_text(
        "# [Fix thing]\n\nBranch: dem-1-fix\nKey: dem-1\nLast session: September 28, 2026\n"
        f"Links: https://example.test/DEM-1\nNotes (Worklog%20Tickets/Notes%20{CHILD_ID}.csv)\nProject: {proj_rel}\nRepos: acme/one\n"
        "Status: In progress\nTicket ID: DEM-1\nType: Bug\n\n## Goal / Why\n\n"
        f"See [notes](%5BFix%20thing%5D/Notes%20{CHILD_ID}.md) and "
        f"[self](%5BFix%20thing%5D%20{TICKET_ID}.md) and "
        f"[[Fix thing] again](%5BFix%20thing%5D%20{TICKET_ID}.md).\n"
    )
    child_dir = wl / "Worklog Tickets" / "[Fix thing]"
    child_dir.mkdir()
    (child_dir / f"Notes {CHILD_ID}.md").write_text("# Notes\n\nChild body\n")
    _csv(wl / f"Worklog Sessions {'3' * 32}.csv", ["Name", "Date"], [["[DEM-1] Fix thing", "September 28, 2026"]])
    (wl / "Worklog Sessions" / f"[DEM-1] Fix thing {SESSION_ID}.md").write_text(
        f"# [DEM-1] Fix thing\n\nDate: September 28, 2026\nProject: {proj_rel}\n"
        f"Summary: Did the thing\nTicket: {ticket_rel}"
    )
    _csv(wl / f"Worklog Weeks {'4' * 32}.csv", ["Name", "Status"], [["2026-W40 · 28 Sep – 4 Oct", "Draft"]])
    (wl / "Worklog Weeks" / f"2026-W40 · 28 Sep – 4 Oct {WEEK_ID}.md").write_text(
        "# 2026-W40 · 28 Sep – 4 Oct\n\nStatus: Draft\nWeek start: September 28, 2026\n\n"
        "## Mon 28 Sep\n\n- [DEM-1] Fix thing\n"
    )
    return root


def test_safe_name_drops_unsafe_chars_and_cuts_on_word_boundary():
    assert ni.safe_name("[A][B] x: y/z") == "AB x yz"
    assert ni.safe_name("word " * 30, limit=12) == "word word"


def test_convert_writes_layout(tmp_path: Path):
    export, vault = make_export(tmp_path / "export"), tmp_path / "vault"
    report, counts = ni.convert(export, vault)
    assert report.issues == []
    assert counts == {"projects": 1, "tickets": 1, "ticket subpages": 1, "sessions": 1, "weeks": 1}
    wl = vault / "Worklog"
    assert "ticket_prefix: DEM" in (wl / "Projects" / "Demo.md").read_text()
    ticket = (wl / "Tickets" / "Demo" / "dem-1 - Fix thing.md").read_text()
    assert 'title: "[Fix thing]"' in ticket
    assert 'project: "[[Demo]]"' in ticket
    assert "last_session: 2026-09-28" in ticket
    assert "Branch:" not in ticket and "Ticket ID:" not in ticket  # property block stripped
    assert "[[Notes|notes]]" in ticket and "[[dem-1 - Fix thing|self]]" in ticket
    assert "[[dem-1 - Fix thing|Fix thing again]]" in ticket
    assert "%5B" not in ticket and CHILD_ID not in ticket
    assert 'links:\n  - "https://example.test/DEM-1"\n  - Notes\n' in ticket
    assert (wl / "Tickets" / "Demo" / "dem-1 - Fix thing" / "Notes.md").read_text().endswith("Child body\n")
    session = (wl / "Sessions" / "2026-09-28 dem-1.md").read_text()
    assert 'ticket: "[[dem-1 - Fix thing]]"' in session and 'project: "[[Demo]]"' in session
    week = (wl / "Weeks" / "2026-W40.md").read_text()
    assert "week_start: 2026-09-28" in week and "- [DEM-1] Fix thing" in week


def test_idempotent(tmp_path: Path):
    export, vault = make_export(tmp_path / "export"), tmp_path / "vault"
    ni.convert(export, vault)
    first = {p: p.read_bytes() for p in vault.rglob("*.md")}
    ni.convert(export, vault)
    assert first == {p: p.read_bytes() for p in vault.rglob("*.md")}


def test_missing_relation_is_reported_not_skipped_silently(tmp_path: Path, capsys):
    export, vault = make_export(tmp_path / "export", break_session_ticket=True), tmp_path / "vault"
    rc = ni.main(["--export", str(export), "--vault", str(vault)])
    assert rc == 1
    assert "Ticket relation missing or unknown" in capsys.readouterr().err
    assert not list((vault / "Worklog" / "Sessions").glob("*.md"))


def test_unknown_select_value_is_reported(tmp_path: Path):
    export = make_export(tmp_path / "export")
    page = next((export / "Worklog" / "Worklog Tickets").glob("*.md"))
    page.write_text(page.read_text().replace("Type: Bug", "Type: Weird"))
    report, _ = ni.convert(export, tmp_path / "vault")
    assert any("unknown ticket type 'Weird'" in i for i in report.issues)


def test_missing_export_dir(tmp_path: Path):
    assert ni.main(["--export", str(tmp_path / "nope"), "--vault", str(tmp_path / "v")]) == 2


@pytest.mark.parametrize("value,expected", [("Plain text", "Plain text"), ("a: b", '"a: b"'), ("yes", '"yes"')])
def test_yaml_str(value: str, expected: str):
    assert ni.yaml_str(value) == expected
