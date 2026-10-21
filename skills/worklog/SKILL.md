---
name: worklog
description: Record what the user worked on and WHY into their Notion work log, one page per ticket (work item) grouped by project, appending a dated session entry each time and recording a daily session row used for the weekly time-tracking summary. Use this whenever the user runs /worklog, asks to "log this", "record this in Notion", "update my work log", "document what we did", or accepts an end-of-task offer to log work. Also use it to backfill days the user forgot to log ("/worklog backfill", "I forgot to log Tuesday", "fill in the missing days", or when /weeklog offers it). Also use it when the user asks what they did on a ticket or project previously, since the log is the source of truth.
---

# Worklog: project/ticket journal in Notion

Each ticket is one Notion page with a narrative session log (what/why/decisions).
Each day of work on a ticket is also one row in **Worklog Sessions**, which powers the
weekly by-day summary (`/weeklog`) used for time-tracking entries.
The goal is a durable record of decisions and reasoning ("why"), not a commit log.

## Config
Org-specific values live in the untracked `~/.claude/worklog.config.json`, not in this file.
Before backfill mode (and in `weeklog` / `start-ticket`) run
`python3 ~/.claude/skills/worklog/scripts/setup.py --get`; on exit code 3 run
`python3 ~/.claude/skills/worklog/scripts/setup.py` (dialogs; long timeout) or ask in chat and
use `setup.py --set key=value`. Keys: `ticket_url_base`, `daily_ticket_id`, `daily_title`,
`daily_project`, `time_tool`, `repos_roots`.

## Notion structure

Four databases in the user's Notion (via the Notion MCP server):

- **Worklog Projects**: `Name` (title), `Repos` (text: one `owner/repo` per line, the repo →
  project registry), `Ticket prefix` (text, e.g. `PROJ`; empty if the project has no ticket
  IDs), `Status` (select: Active / Paused / Done), `Description` (text)
- **Worklog Tickets**: `Name` (title: the ticket title only, without the ID),
  `Ticket ID` (text, e.g. `PROJ-123`; empty if the project has no prefix), `Key` (text, unique
  slug), `Project` (relation → Worklog Projects), `Status` (select: In progress / Blocked /
  Done), `Type` (select: Feature / Bug / Incident / Chore / Research), `Repos` (text: repo IDs
  touched, one per line), `Branch` (text), `Links` (text, PRs/docs), `Last session` (date)
- **Worklog Sessions**: `Name` (title: the display label, see below), `Date` (date),
  `Ticket` (relation → Worklog Tickets), `Project` (relation → Worklog Projects),
  `Summary` (text: one line, timesheet-ready)
- **Worklog Weeks**: written by the `weeklog` skill, not this one.

**Display label** for a ticket, used everywhere (session rows, weekly summary):
- With a Ticket ID: `[PROJ-123] <ticket title>`
- Without one: `<ticket title>`

Find the databases by searching Notion for their names. If they don't exist, stop and
tell the user; offer to create them with the schema above (only after they agree).
For the ticket page body layout, read `references/page-template.md`.

## Workflow

### 1. Gather context (read-only)
Run these, tolerating failures (e.g. not a git repo):
- `date +%F` → today's date (local). The user can override it ("log this for yesterday").
- `git remote get-url origin` → normalize to the **repo ID** `owner/repo`: strip the protocol,
  host, `git@host:` prefix and `.git` suffix, and lowercase it
  (`git@github.com:Acme/platform-infra.git` → `acme/platform-infra`).
  If there's no remote, fall back to the basename of `git rev-parse --show-toplevel`.
- `git branch --show-current`
- `git log --oneline -15` and `git diff --stat HEAD~5..HEAD 2>/dev/null` (or against the base branch)
- `gh pr view --json url,title 2>/dev/null` if `gh` is available

Then review this conversation: what was asked, what changed, what was decided and why.

### 2. Resolve the project
Projects span multiple repos, and new projects appear often. The **`Repos` property in
Worklog Projects is the single source of truth** for which repo belongs to which project.
Never infer the project from the repo name alone.

1. **Explicit override:** if the user named a project in this request, use it.
   Otherwise, if the repo's CLAUDE.md or CLAUDE.local.md has `Worklog project: <name>`, use it.
2. **Registry lookup:** query Worklog Projects for pages whose `Repos` contains the repo ID
   (match whole lines, case-insensitive, so `acme/infra` doesn't match `acme/infra-modules`).
   - **Exactly one match:** use it. Mention it in the preview ("Project: EKS Platform").
   - **Several matches** (shared repo, e.g. a modules repo): ask which project this ticket
     belongs to. Don't save a default; ask each time for a new ticket. For an existing
     ticket found in step 3, use that ticket's project.
   - **No match** (new repo or new project): list the Active projects and ask:
     *"`<repo-id>` isn't mapped yet. Which project is it part of, or is it a new project?"*
     - Existing project: append the repo ID as a new line to that project's `Repos`.
     - New project: ask for a name, a one-line description, and its ticket prefix
       (e.g. `PROJ`, or none), then create the project page (Status = Active, Repos = repo ID).
     State the mapping change in the preview so the user confirms it with the entry.
     After this, the repo is never asked about again, on any machine.
3. Never create a project or change `Repos` without the user's confirmation.

### 3. Resolve the ticket
**Ticket ID** (only if the project has a `Ticket prefix`):
1. An ID passed to /worklog (`/worklog PROJ-123`).
2. Otherwise, search the branch name case-insensitively for `<PREFIX>-<digits>`
   (`feat/proj-123-oidc-deploy` → `PROJ-123`). Normalize to uppercase.
3. Otherwise ask: *"Which `<PREFIX>` ticket is this? (e.g. PROJ-123)"*. Don't invent a number.
An ID with a different prefix than the project's is a sign the project is wrong: ask.

**Key** (always): the Ticket ID lowercased if there is one (`proj-123`); otherwise the
slug from a /worklog argument or the branch name with prefixes stripped (`feat/`, `fix/`,
`chore/`, `hotfix/`, `<user>/`). On `main`/`master`/`develop` or a generic branch, ask for
a key and title, suggesting one based on the work.

**Lookup**, within the project (not the repo): match by `Ticket ID` first, then by `Key`.
A ticket can span several repos of the same project, and sessions from any of them append
to the same page. If there's no match, list the project's In progress tickets and ask
whether this work continues one of them before creating a new page.
- **Found:** fetch the page so the new entry doesn't repeat earlier ones.
- **Not found:** ask for the ticket title if it isn't clear (for IDs, use the real ticket's
  title as the user gives it, not a paraphrase). Create the page (Name = title, Ticket ID,
  Key, Project, Status = In progress, Type inferred and stated in the preview, Branch) with
  the body skeleton from the template, including a **Goal / Why** section.

### 4. Draft the session entry and session summary
Use the entry format in `references/page-template.md`. Rules:
- **"Why" is mandatory.** Use the reasoning stated in the conversation. If the motivation
  for the work isn't clear, ask ONE question rather than inventing a reason.
- Record decisions with the alternatives considered and why they were rejected.
- Be specific: file paths, resource names, versions, error messages (trimmed).
- Keep it scannable: roughly 10–25 lines per session. Link to PRs/commits instead of pasting diffs.
- Don't restate what earlier sessions on the page already say.

Also draft the **session summary**: one line, max ~120 characters, past tense, written for a
timesheet reader (manager/client), no file paths or jargon beyond what's needed.
Example: `Replaced static AWS keys with OIDC in staging deploy; scoped IAM role to main branch`.

### 5. Sanitize (always)
Remove or mask before writing: secrets, tokens, passwords, private keys, connection
strings, AWS account IDs (→ `<account-id>`), ARNs containing account IDs, internal IPs and
hostnames, customer names or data, and anything copied from `.env`, kubeconfigs, or
Terraform state. This applies doubly to the session summary, which is copied into the time-tracking tool.
If an entry can't be useful without sensitive detail, describe it generically and tell the
user what was omitted.

### 6. Preview and confirm
Show the user: the target (project → display label, new or existing), any property and
registry changes, the session row (`<date> · <display label> · <summary>`), and the full
entry text. Write only after they confirm. Apply their edits if they request changes.

### 7. Write
Order: registry change (if any) → ticket page → session row.
- Append the entry at the END of the page's "Session log" section (chronological order).
  Never overwrite or rewrite earlier entries.
- Update ticket properties: `Last session` = session date, `Status` if it changed, append new
  PR/doc URLs to `Links`, add the repo ID to `Repos` if missing, and `Branch` if it changed.
- **Session row: one per ticket per day.** Query Worklog Sessions for this ticket and date.
  - None: create it (Name = display label, Date, Ticket, Project, Summary).
  - Exists (a second log the same day): merge into it by combining both summaries into one
    line (keep it ≤ ~160 chars); don't create a duplicate row.
- If the work is Done, fill in the page's **Outcome** section (1–3 lines).
- Reply with the Notion page link and a one-line summary. Nothing more.

### Backfill mode (missed days)
Use when the user didn't log one or more past days: `/worklog backfill [<date>|<from>..<to>]`,
"I forgot to log Tuesday", or when `/weeklog` offers it for gap days. The current conversation
doesn't cover those days, so rebuild them from local history instead.

1. **Pick the days.** If dates are given, use them. Otherwise take every weekday from the day
   after the latest `Date` in Worklog Sessions up to yesterday (max 10 weekdays; if more, ask).
   Drop days that already have session rows, unless the user named them.
2. **Collect sources** (read-only). Copy the output to the scratchpad if it's long:
   ```bash
   python3 ~/.claude/skills/worklog/scripts/backfill_sources.py <YYYY-MM-DD> [...] [--roots DIR ...]
   ```
   Without `--roots` it scans the `repos_roots` from the config.
   For each day it lists the user's commits in every git repo under the roots (with the
   branch each came from), branch checkouts from the reflog (work that wasn't committed), and
   Claude Code transcript excerpts from that day (user prompts and replies, grouped by
   folder and branch). Transcripts are where the "why" usually is. They can contain secrets
   pasted in chat, so step 5 (Sanitize) applies to everything drawn from them.
3. **Group into (day, ticket) pairs.** Map each branch to a ticket ID as in step 3 (`proj-123-…`
   → PROJ-123), and each repo to a project as in step 2 (registry rules and confirmations
   still apply). Activity on `main`/`integration` or a branch without an ID: ask which ticket,
   or let the user skip it. Pure branch checkouts with no commits or transcript activity are
   weak evidence: list them as "possible, confirm".
4. **Draft one entry and one session summary per pair**, using the normal format and rules.
   Be honest about the source: if no transcript explains the reason, don't invent one. Ask
   the user once, listing every pair that has no "why". If the user doesn't remember, write
   `**Why:** (backfilled from git history; reason not recorded)`.
5. **Preview all days together**: per day, the session rows, the full entries, and the
   evidence used (commit hashes, transcript time ranges). Write only after one confirmation;
   the user can drop or edit individual pairs.
6. **Write** as in step 7, with these differences:
   - Place each entry **in date order** within "Session log": insert it before the first
     existing entry with a later date, instead of appending at the end.
   - Set `Last session` only if the backfilled date is later than the current value.
   - Session rows use the backfilled date (one per ticket per day; merge if one exists).
7. Reply with the ticket page link(s) and one line per backfilled day.

### Recall mode
If the user asks what happened on a ticket/project ("what did I decide about X?"), search
and fetch the relevant pages and answer from them, citing the session dates. Do not write.

## Edge cases
- **Multiple tickets in one session:** ask which to log, or log a separate entry and session
  row to each.
- **Notion MCP unavailable or unauthenticated:** tell the user to run `/mcp` and authenticate;
  offer to save the drafted entry to `./.worklog-pending.md` (gitignored) so nothing is lost.
- **Duplicate tickets found:** list them and ask which one to use; don't guess.
- **Ticket ID corrected later:** update `Ticket ID`, `Key`, and the `Name` of that ticket's
  session rows so the weekly summary shows the right label.
- **Repo moves to another project:** only when the user asks. Remove the repo ID from the old
  project's `Repos` and add it to the new one; existing tickets stay where they are.
- **Repo renamed or remote changed:** if the new ID isn't mapped, ask whether it's the same repo
  as an existing entry and update that line instead of adding a new mapping.
