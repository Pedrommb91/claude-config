---
name: start-ticket
description: Start work on a new Jira ticket. Jira isn't connected, so ask the user for the ticket details (ID, title, description, type) in native macOS form dialogs, build the Jira link from the ID, then create the ticket page in the Notion work log, create the git branch, and propose an implementation plan. Use this whenever the user runs /start-ticket, says "start a ticket", "start PROJ-123", "new ticket", "I'm picking up a ticket", or pastes a Jira ticket and wants to begin work on it.
---

# Start ticket: Jira ticket → Notion page + branch + plan

Jira can't be connected, so everything about the ticket comes from the user. Collect it
once, then set up the work so `/worklog` and `/weeklog` find the ticket later.
Notion databases, the project registry, the ticket page template and the sanitizing rules
are the same as in the `worklog` skill (`~/.claude/skills/worklog/SKILL.md` and
`~/.claude/skills/worklog/references/page-template.md`). Read both before step 3.

## 1. Ask for the ticket (form dialogs)

Don't ask in chat first. Open the form, which shows native macOS dialogs one after the
other: ID → title → description → type (list) → optional links/context. Pass the ID if the
user gave one (`/start-ticket PROJ-123`):

```bash
python3 ~/.claude/skills/start-ticket/scripts/ticket_form.py [--id PROJ-123]
```

Run it with a long timeout (600000 ms), because it waits for the user. It prints JSON with
`id`, `title`, `description`, `type`, `extra`, `link`. The link is always
`<ticket_url_base><ID>` (from the worklog config), built from the ID, so never ask for it;
it is empty if no base is configured. If there is no config yet, run
`python3 ~/.claude/skills/worklog/scripts/setup.py` first (see the `worklog` skill's Config section).
- **Exit 1 (cancelled):** stop. Say the ticket wasn't started.
- **Exit 2 (dialogs unavailable**, e.g. not macOS or no GUI session): fall back to asking in
  one chat message for the ID, the title (exactly as in Jira), the description with
  acceptance criteria, and optionally the type and related links.

Then validate:
- The ID must match `<PREFIX>-<digits>`, uppercase (the form already enforces this).
- Use the title verbatim. Don't paraphrase it, because it's the time-tracking label.
- If the description is empty or too vague to work from, ask ONE follow-up question about the
  goal and the definition of done. Don't invent requirements.

## 2. Gather repo context (read-only)

- `date +%F`
- Repo ID from `git remote get-url origin` (normalized as in worklog), `git branch --show-current`,
  `git status --porcelain`, default branch (`git symbolic-ref refs/remotes/origin/HEAD`,
  fall back to `main`).
- Existing branches for this ticket: `git branch -a --list "*<id>*" -i`.
- The repo's CLAUDE.md / README and recent `git log --oneline -10`, for the branch naming
  convention (e.g. `feat/PROJ-123-short-slug`) and commit style.

## 3. Resolve the project and check for an existing ticket

- Resolve the project from the repo ID exactly as worklog step 2 says (registry lookup in
  Worklog Projects; ask if there are no matches or several). Check that the ID prefix matches
  the project's `Ticket prefix`.
- Query Worklog Tickets for this `Ticket ID` within the project. If it exists, don't create a
  duplicate. Say so, show its status and last session, and offer to update its fields
  (description, links) and continue with the branch and plan steps.

## 4. Preview and confirm (one confirmation)

Show everything that will be created:
- **Notion:** project → `[PROJ-123] <title>` (new / existing), Type, Status = In progress,
  Links, and the page body (below).
- **Branch:** `<type>/<ID>-<slug>` off `origin/<default>`. Type prefix: `feat` for Feature,
  `fix` for Bug, `chore` for Chore, `docs`/`ci`/`refactor` if the ticket is clearly that.
  Slug: 3–5 lowercase words from the title, hyphenated, ≤ 40 chars. Follow the repo's
  convention if it differs.
- **Task brief:** 3–6 lines: what's being asked, acceptance criteria as a checklist,
  open questions or ambiguities spotted in the description.

Write nothing until the user confirms. Apply their edits.

## 5. Create the Notion ticket page

Properties: `Name` = title, `Ticket ID`, `Key` = ID lowercased, `Project`, `Status` = In
progress, `Type`, `Repos` = repo ID, `Branch`, `Links` = Jira link first, then other links
one per line. Don't set `Last session`, because no work has been logged yet.

Body: the worklog template, with the Jira description added after Goal / Why:

```markdown
## Goal / Why
<1–3 sentences from the description: the problem and why it matters. If the "why" isn't
in the description and the user didn't say, write "Not stated in the ticket.">

## Ticket description
<Jira link>
<The description as pasted, sanitized. Keep its structure and acceptance criteria.>

## Outcome
_Filled in when the ticket is Done: what shipped, measurable result, follow-ups._

## Key decisions

## Session log
```

Sanitize the description before writing (worklog step 5): mask account IDs, ARNs, internal
hosts and IPs, credentials, and customer data. Tell the user what was masked.

## 6. Create the branch

- If the working tree has uncommitted changes, stop and ask (stash, commit, or skip the
  branch). Never discard changes.
- If a branch for this ticket already exists (step 2), offer to switch to it instead.
- Otherwise: `git fetch origin <default>` then `git switch -c <branch> origin/<default>`.
- Don't push. The user pushes when there's something to push.

## 7. Propose a plan

Read the code the ticket touches (search the repo for the components named in the
description) and propose an implementation plan: the files to change, the approach and its
trade-offs, how it will be verified (the checks from the global CLAUDE.md), and the questions
for the ticket owner. Follow the user's working style: present the plan and **wait for
approval** before changing code.

End with: the Notion page link, the branch name, and the plan.

## Edge cases
- **Not in a git repo:** create the Notion page only. Ask which repo/project it belongs to.
- **Notion unavailable:** tell the user to authenticate via `/mcp`. Save the ticket details
  and page body to `./.worklog-pending.md` (gitignored) so `/worklog` can create the page later.
  Still create the branch and plan.
- **Ticket spans several repos:** create the page once. Branches are created per repo when
  work starts there; worklog adds each repo to `Repos`.
