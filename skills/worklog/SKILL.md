---
name: worklog
description: Record what the user worked on and WHY into their Obsidian work log (the Workbench vault), one note per ticket (work item) grouped by project, appending a dated session entry each time and recording a daily session note used for the weekly time-tracking summary. Use this whenever the user runs /worklog, asks to "log this", "record this in the worklog", "update my work log", "document what we did", or accepts an end-of-task offer to log work. Also use it to backfill days the user forgot to log ("/worklog backfill", "I forgot to log Tuesday", "fill in the missing days", or when /weeklog offers it). Also use it when the user asks what they did on a ticket or project previously, since the log is the source of truth.
---

# Worklog: project/ticket journal in the vault

Each ticket is one Markdown note with a narrative session log (what/why/decisions).
Each day of work on a ticket is also one small note in `Worklog/Sessions/`, which powers the
weekly by-day summary (`/weeklog`) used for time-tracking entries.
The goal is a durable record of decisions and reasoning ("why"), not a commit log.

## Config
Org-specific values live in the untracked `~/.claude/worklog.config.json`, not in this file.
Before backfill mode (and in `weeklog` / `start-ticket`) run
`python3 ~/.claude/skills/worklog/scripts/setup.py --get`; on exit code 3 run
`python3 ~/.claude/skills/worklog/scripts/setup.py` (dialogs; long timeout) or ask in chat and
use `setup.py --set key=value`. Keys: `ticket_url_base`, `daily_ticket_id`, `daily_title`,
`daily_project`, `time_tool`, `repos_roots`, `vault_path`.

## Vault structure

The vault is the folder in `vault_path`; the worklog lives in its `Worklog/` subfolder. The
contract (field names, file naming, wikilinks, select values) is `Worklog/_schema.md` in the
vault: read it before writing a note by hand. In short:

- `Projects/<Project>.md`: `repos` (list of `owner/repo`, the repo → project registry),
  `ticket_prefix` (empty if the project has no ticket IDs), `status` (Active / Paused / Done),
  `description`
- `Tickets/<Project>/<key> - <title>.md`: `title` (ticket title only, without the ID),
  `ticket_id` (e.g. `PROJ-123`; omitted if the project has no prefix), `key` (unique slug),
  `project` (`"[[Project]]"`), `status` (In progress / Blocked / Done), `ticket_type`
  (Feature / Bug / Incident / Chore / Research), `repos`, `branch`, `links` (list),
  `last_session` (date). The body is the page template.
- `Sessions/<YYYY-MM-DD> <key>.md`: `date`, `ticket`, `project`, `summary` (one line,
  timesheet-ready, 120 characters at most). Written only through `vault.py upsert-session`.
- `Weeks/<YYYY-Www>.md`: written by the `weeklog` skill, not this one.

**Display label** for a ticket, used everywhere (session notes, weekly summary), built from
the ticket's frontmatter, never from the file name:
- With a Ticket ID: `[PROJ-123] <ticket title>`
- Without one: `<ticket title>`

**Lookups and session writes go through `vault.py`** (JSON on stdout, vault taken from
`vault_path`; `python3 ~/.claude/skills/worklog/scripts/vault.py --help`):
- `find-project --repo owner/repo`
- `find-ticket --project NAME (--id PROJ-1 | --key proj-1)` (ID first, then key) and
  `list-tickets --project NAME [--status "In progress"]`
- `sessions --from DATE --to DATE`
- `upsert-session --project NAME (--id | --key) --date DATE --summary TEXT`
- `find-week (--week 2026-W40 | --date DATE)`

Everything else (ticket and project notes) is edited with Read/Edit/Write. If `vault.py` says
the vault is missing, tell the user to run `setup.py` (`vault_path`); don't create it.
For the ticket note body layout, read `references/page-template.md`.

**File names** drop `[ ] # ^ | \ / :`, collapse repeated spaces and stop at 100 characters on
a word boundary. Frontmatter strings that contain `:`, `[`, `#`, quotes or look like
`yes`/`no`/numbers are double-quoted (JSON style).

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
Projects span multiple repos, and new projects appear often. The **`repos` list in
the project notes is the single source of truth** for which repo belongs to which project.
Never infer the project from the repo name alone.

1. **Explicit override:** if the user named a project in this request, use it.
   Otherwise, if the repo's CLAUDE.md or CLAUDE.local.md has `Worklog project: <name>`, use it.
2. **Registry lookup:** `vault.py find-project --repo <repo-id>` (whole entries,
   case-insensitive, so `acme/infra` doesn't match `acme/infra-modules`).
   - **Exactly one match:** use it. Mention it in the preview ("Project: EKS Platform").
   - **Several matches** (shared repo, e.g. a modules repo): ask which project this ticket
     belongs to. Don't save a default; ask each time for a new ticket. For an existing
     ticket found in step 3, use that ticket's project.
   - **No match** (new repo or new project): list the Active projects and ask:
     *"`<repo-id>` isn't mapped yet. Which project is it part of, or is it a new project?"*
     - Existing project: add the repo ID as a new item to that project note's `repos` list.
     - New project: ask for a name, a one-line description, and its ticket prefix
       (e.g. `PROJ`, or none), then create `Projects/<Name>.md` (`type: project`,
       `status: Active`, `repos` = repo ID, empty body).
     State the mapping change in the preview so the user confirms it with the entry.
     After this, the repo is never asked about again, on any machine.
3. Never create a project or change `repos` without the user's confirmation.

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

**Lookup**, within the project (not the repo): `vault.py find-ticket --project <P> --id <ID>
--key <key>` matches the ticket ID first, then the key. A ticket can span several repos of
the same project, and sessions from any of them append to the same note. If there's no
match, `vault.py list-tickets --project <P> --status "In progress"` and ask whether this
work continues one of them before creating a new note. Duplicates make `vault.py` fail:
list them and ask which one to use.
- **Found:** Read the ticket note (its `path`) so the new entry doesn't repeat earlier ones.
- **Not found:** ask for the ticket title if it isn't clear (for IDs, use the real ticket's
  title as the user gives it, not a paraphrase). Create
  `Tickets/<Project>/<key> - <title>.md` with Write: frontmatter in schema order (`type:
  ticket`, `title`, `ticket_id`, `key`, `project`, `status: In progress`, `ticket_type`
  inferred and stated in the preview, `repos`, `branch`, `links`; no `last_session` yet,
  `upsert-session` sets it) and the body skeleton from the template, including a
  **Goal / Why** section.

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
The vault is a git repo and may be pushed or synced, so treat it as shared.
Remove or mask before writing: secrets, tokens, passwords, private keys, connection
strings, AWS account IDs (→ `<account-id>`), ARNs containing account IDs, internal IPs and
hostnames, customer names or data, and anything copied from `.env`, kubeconfigs, or
Terraform state. This applies doubly to the session summary, which is copied into the time-tracking tool.
If an entry can't be useful without sensitive detail, describe it generically and tell the
user what was omitted.

### 6. Preview and confirm
Show the user: the target (project → display label, new or existing), any frontmatter and
registry changes, the session note (`<date> · <display label> · <summary>`), and the full
entry text. Write only after they confirm. Apply their edits if they request changes.

### 7. Write
Order: registry change (if any) → ticket note → session note.
- Append the entry at the END of the note's "Session log" section (chronological order).
  Never overwrite or rewrite earlier entries. Use Edit, not a full rewrite.
- Update ticket frontmatter with Edit: `status` if it changed, append new PR/doc URLs to
  `links`, add the repo ID to `repos` if missing, and `branch` if it changed. Don't touch
  `last_session`; `upsert-session` keeps it in sync.
- **Session note: one per ticket per day.** Run `vault.py upsert-session --project <P> --id
  <ID> --key <key> --date <date> --summary "<summary>"`. It creates the note, or merges
  the summary into the existing one (a second log the same day; up to 160 characters). It
  fails if a new summary is over 120 characters: shorten it and rerun.
- If the work is Done, fill in the note's **Outcome** section (1–3 lines).
- Reply with the ticket note path and a one-line summary. Nothing more.

### Backfill mode (missed days)
Use when the user didn't log one or more past days: `/worklog backfill [<date>|<from>..<to>]`,
"I forgot to log Tuesday", or when `/weeklog` offers it for gap days. The current conversation
doesn't cover those days, so rebuild them from local history instead.

1. **Pick the days.** If dates are given, use them. Otherwise take every weekday from the day
   after the latest session `date` (`vault.py sessions --from 2000-01-01 --to <today>`, take
   the last one) up to yesterday (max 10 weekdays; if more, ask).
   Drop days that already have session notes, unless the user named them.
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
   - `last_session` only moves forward; `upsert-session` handles that, so a backfilled
     earlier date never lowers it.
   - Session notes use the backfilled date (one per ticket per day; merged if one exists).
7. Reply with the ticket note path(s) and one line per backfilled day.

### Recall mode
If the user asks what happened on a ticket/project ("what did I decide about X?"), use
`vault.py find-ticket` / `list-tickets` / `sessions`, or Grep the `Worklog/` folder, then Read
the relevant notes and answer from them, citing the session dates. Do not write.

## Edge cases
- **Multiple tickets in one session:** ask which to log, or log a separate entry and session
  note to each.
- **Vault missing or `vault_path` unset:** `vault.py` says so. Tell the user to run `setup.py`
  (or `setup.py --set vault_path=...`) and stop; don't write notes anywhere else.
- **Duplicate tickets found:** list them and ask which one to use; don't guess.
- **Ticket ID corrected later:** in the ticket note update `ticket_id` and `key`, and rename
  the file to `<new key> - <title>.md` (and its subpage folder, if any). For each of that
  ticket's session notes rename `<date> <old key>.md` to `<date> <new key>.md`. Then fix every
  `[[<old file name>]]` link (Grep the vault) to the new name. The label is built from
  the ticket, so the weekly summary picks up the change by itself. Check the rename with
  `vault.py sessions` for a day it touches.
- **Repo moves to another project:** only when the user asks. Remove the repo ID from the old
  project's `repos` and add it to the new one; existing tickets stay where they are.
- **Repo renamed or remote changed:** if the new ID isn't mapped, ask whether it's the same repo
  as an existing entry and update that line instead of adding a new mapping.
