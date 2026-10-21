---
name: weeklog
description: Build the user's weekly work summary grouped by day from their Notion work log (Worklog Sessions), formatted as "[PROJ-123] Ticket title" lines ready to copy into time-tracking entries, and save it as a weekly page in Notion. Use this whenever the user runs /weeklog, asks for their week, "what did I work on this week/last week/on Tuesday", a timesheet summary, or wants to fill in or check their time entries.
---

# Weeklog: weekly by-day summary for time tracking

Reads the **Worklog Sessions** rows written by the `worklog` skill and produces a per-day
list of tickets for one week (Monday–Sunday). Read-only except for the weekly page.

## Notion structure used
- **Worklog Sessions** (read): `Name` (display label), `Date`, `Ticket` (relation),
  `Project` (relation), `Summary`
- **Worklog Tickets** (read): `Name` (title), `Ticket ID`, `Project`
- **Worklog Projects** (read): `Name`
- **Worklog Weeks** (write): `Name` (title, e.g. `2026-W40 · 28 Sep – 4 Oct`),
  `Week start` (date, the Monday), `Status` (select: Draft / Logged in <time_tool>)

If Worklog Weeks doesn't exist, offer to create it with this schema (only after the user agrees).
If Worklog Sessions doesn't exist, the `worklog` skill hasn't been set up yet: say so and stop.

## Config
Org-specific values are not hard-coded; they live in the untracked
`~/.claude/worklog.config.json`. Before step 1 run
`python3 ~/.claude/skills/worklog/scripts/setup.py --get`. On exit code 3 (no config yet),
run `python3 ~/.claude/skills/worklog/scripts/setup.py` (it opens dialogs; run it with a long
timeout, or ask the user in chat and use `setup.py --set key=value`), then continue.
Used here: `time_tool` (named `<time_tool>` below) and `daily_ticket_id`, `daily_title`,
`daily_project` for the recurring weekday entry (skip that entry if `daily_ticket_id` is empty).

## Workflow

### 1. Resolve the week
Argument → week:
- none / `this` → the week containing today
- `last` → the previous week
- a date (`2026-09-30`) → the week containing it
- an ISO week (`2026-W40`) → that week

Compute the dates with Python (portable across macOS and Linux):
```bash
python3 - "$ARG" <<'PY'
import sys, datetime as dt
a = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
t = dt.date.today()
if a in ("", "this"): d = t
elif a == "last": d = t - dt.timedelta(days=7)
elif "-w" in a:
    y, w = a.split("-w"); d = dt.date.fromisocalendar(int(y), int(w), 1)
else: d = dt.date.fromisoformat(a)
mon = d - dt.timedelta(days=d.weekday()); sun = mon + dt.timedelta(days=6)
y, w, _ = mon.isocalendar()
print(mon.isoformat(), sun.isoformat(), f"{y}-W{w:02d}")
PY
```

### 2. Fetch sessions
Query Worklog Sessions where `Date` is between Monday and Sunday (inclusive). For each row,
build the display label from the **related ticket's current** `Ticket ID` and `Name`
(so renamed/corrected tickets show correctly); fall back to the row's `Name`:
- With a Ticket ID: `[PROJ-123] <ticket title>`
- Without one: `<ticket title>`

**Recurring entries:** if configured, add `[<daily_ticket_id>] <daily_title>` (project
`<daily_project>`) to every weekday Mon–Fri, including days not yet worked. It isn't logged in
Worklog Sessions, and it never goes on Sat/Sun. If a session row for that ticket exists on a
day, don't list it twice.

### 3. Format
Group by day in date order. Within a day, sort by project, then Ticket ID (numerically, so
`PROJ-9` comes before `PROJ-10`), then title.
Show every weekday Mon–Fri; show Sat/Sun only if they have entries. When a day has tickets
from more than one project, add the project name as a sub-heading so each time entry maps
to the right project.

The copy block has **label lines only**: no bullets, no summaries, no indentation.

```
Week 2026-W40 · 28 Sep – 4 Oct

Mon 28 Sep
[PROJ-1] Team Daily
[PROJ-123] Migrate deploy workflow to OIDC
[PROJ-131] EKS 1.31 upgrade prep

Tue 29 Sep
EKS Platform
[PROJ-131] EKS 1.31 upgrade prep
Platform
[PROJ-1] Team Daily
Internal Tooling
Log shipping cost review

Wed 30 Sep
[PROJ-1] Team Daily
```

Each label line must match exactly: `[<TICKET-ID>] <ticket title>`, with nothing else on it,
so it can be pasted as-is.

Summaries aren't in the copy block, but they go on the Notion page. Re-check them for
anything sensitive (secrets, account IDs, internal hostnames, customer data), mask it, and
tell the user. Flag rows with an empty `Summary` ("no summary logged") instead of inventing one.

### 4. Save the weekly page
Look up Worklog Weeks by `Week start` = Monday.
- **Not found:** create it (Name, Week start, Status = Draft) with this body: one heading per
  day, the label lines (including the recurring entry) as bullets, and each session's summary as nested
  text under its bullet. The recurring entry has no summary.
- **Found, Status = Draft:** replace the body with the fresh summary (it's derived data).
- **Found, Status = Logged in <time_tool>:** if the new summary differs, show what changed and
  ask before overwriting, since the user may have already submitted those entries.

### 5. Reply
Print the formatted week in a code block (easy to copy), then the Notion page link.
Mention weekdays with no logged sessions (only the recurring entry) and rows missing summaries, if any.
Nothing more.

**Gap days:** if any weekday **before today** has no logged sessions, check whether work
happened: run `python3 ~/.claude/skills/worklog/scripts/backfill_sources.py <gap dates>`
(read-only), and for each gap day say whether commits or transcripts were found
(e.g. "Tue 29 Sep: 3 commits on proj-123-…, no session logged"). If anything was found, offer:
*"Backfill these days with /worklog?"* On yes, run the `worklog` skill's backfill mode for
those dates, then rebuild this week (steps 2–4) so the page and copy block include them.
Days with nothing found show only the recurring entry. Today and future days are never gaps.

When the user says they've entered the week in <time_tool>, set the page's Status to
"Logged in <time_tool>".

## Edge cases
- **Asked about one day** ("what did I do Tuesday?"): answer for that day only and don't
  save a weekly page unless asked.
- **Sessions logged late:** rows carry the work date, not the log date, so they land on
  the correct day automatically.
- **Notion MCP unavailable:** tell the user to run `/mcp` and authenticate.
