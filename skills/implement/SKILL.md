---
name: implement
description: "Implement one issue from /issues (or a Jira ticket started with /start-ticket) end to end: check it's on the frontier, branch, build it test-first with /tdd at the spec's seams, run the full checks, commit, run /review and fix its Critical/Required findings, then open a PR that closes the issue. One issue per run; stops at plan checkpoints for human review."
disable-model-invocation: true
---

# Implement

Take **one** issue and land it: tests first, reviewed, on a branch with a PR. The issue is the contract: its acceptance criteria define done, and anything beyond them becomes a new issue, not part of this one.

One issue per run, interactive. `/tdd` confirms seams with the user and plan checkpoints need human review, so this is not an AFK loop.

## Sources

The issue comes from one of two places:

- **Tracker issue** (from `/issues`): `#42`, an issue URL, or `<slug>/<NN>` for the local tracker. Read the repo's `## Agent skills` block for the tracker, notes root and labels (see the `setup` skill's [notes.md](../setup/notes.md)); if there's no block, tell the user to run `/setup`. Tracker operations are in `../setup/trackers/<github|gitlab|local>.md`; labels in [labels.md](../setup/labels.md).
- **Jira ticket**: `PROJ-123`. Jira isn't connected; the ticket lives in the work log vault as the note `/start-ticket` created. Vault access, `vault.py` and the project lookup are as in the `worklog` skill (`~/.claude/skills/worklog/SKILL.md`). The `## Agent skills` block is optional here: use its notes root for the glossary and decisions if it exists.

## Process

### 1. Resolve the issue

**Tracker issue.**

- With a ref: fetch it with body and comments. If it carries `spec:<slug>`, fetch the parent spec issue too, and read `<notes root>/Plans/<slug>.md` if it exists.
- Without a ref: if the current branch or conversation points to a spec, list its **frontier** (tracker doc) and let the user pick. Otherwise ask for a ref.

Refuse, and say why, when:

- It's a spec issue (label `spec`, or `Type: spec` locally): it's a container. Offer its frontier instead.
- A blocker is still open. Name it, and offer the frontier.
- It's closed, `wontfix`, or `needs-triage` / `needs-info`. Point to `/triage` for the last two.
- It's assigned to someone else, which means it's possibly mid-build in another session. Continue only on an explicit yes.
- It's `ready-for-human`: read out the reason in its body, and continue only on an explicit yes.

**Jira ticket.**

- Resolve the project from the repo (`vault.py find-project --repo <repo-id>`), then `vault.py find-ticket --project <P> --id <ID>`.
- Found: the note's `## Ticket description` is the spec, and its `## Key decisions` are binding. Use the note's `branch`.
- Not found: suggest `/start-ticket <ID>` first (it creates the note and the branch) and stop. If the user wants to skip it, ask them to paste the description with acceptance criteria, and don't invent any.
- If the description has no acceptance criteria, draft 2–4 from it and get them confirmed before step 3. They become the contract.

Then state the **title** and the **acceptance criteria** as a checklist, plus anything ambiguous. Don't start on an ambiguity that changes what gets built: ask.

### 2. Branch

Check `git status --porcelain` first. With uncommitted changes, stop and ask (stash, commit, or carry on with them). Never discard changes.

- Already on a branch for this issue (the Jira note's `branch`, or a name containing the issue number or ID): stay.
- On the default branch: `git fetch origin <default>`, then `git switch -c <branch> origin/<default>`. Follow the repo's branch convention; otherwise use `<type>/<n>-<issue-slug>` for tracker issues and `<type>/<ID>-<slug>` for Jira (type `feat` / `fix` / `chore` from the category, slug of 3–5 words from the title). Never commit to the default branch.
- On an unrelated branch: ask.

GitHub / GitLab: assign the issue to the user (`gh issue edit <n> --add-assignee @me`) so the frontier skips it. Don't add labels: there's no in-progress state.

### 3. Explore

Read the notes root's `Glossary.md` and the `Decisions/` that touch the area (skip silently if absent). Then find the code the issue touches. For anything beyond a couple of known files, delegate to the built-in `Explore` agent with a narrow brief (the issue's behaviour and the components it names), and keep the summary rather than the file dumps.

Find the repo's focused-test, build and lint commands. The issue's `## Verification` names them; otherwise take them from the repo's CLAUDE.md / Makefile / CI workflow.

If the issue needs prefactoring that it didn't plan for, propose it as a separate commit first, or a new issue if it's large. Don't bury it in the feature commits.

### 4. Build it test-first

Invoke the `tdd` skill and follow it. Pre-fill the seams instead of asking from a blank page:

- Tracker issue: the spec's `## Testing Decisions` (modules and seams).
- Jira ticket: propose seams from the code you explored.

Present them with the one-line "catches / misses" notes `tdd` asks for, and get them confirmed.

Drive the loop from the acceptance criteria: each criterion is at least one red → green slice, at the seam where a caller observes it. Keep a running checklist and tick criteria as their tests go green.

For infra issues (Terraform, Helm, K8s manifests, workflows), the seams and safety rules are in `tdd`: `terraform test` with `command = plan`, `helm template`, `--dry-run=server` against a context you've named to the user. Nothing here applies real resources.

### 5. Full checks

Run the repo's full checks, keeping output small (`| tail`):

- Go: `go build ./...`, `go vet ./...`, `go test ./...` (`-race` if the change touched goroutines)
- Python: `ruff check`, `pytest`
- Terraform: `terraform fmt -check`, `terraform validate`
- Plus anything the issue's `## Verification` lists (including the manual check: do it, or hand it to the user if it needs access you don't have)

If a check fails and the fix isn't obvious, stop and explain. Don't guess.

### 6. Commit

Commit to the issue branch in small, reviewable commits that follow the repo's commit style. Each one references the issue: `(#42)` for GitHub / GitLab, `PROJ-123:` or the repo's Jira convention. Don't push yet.

### 7. Review

Invoke the `review` skill with the default branch as the fixed point (merge-base). The Spec axis reads the issue from the commit refs. For Jira, paste the ticket description and the confirmed acceptance criteria when `review` asks.

- Fix every **Critical** and **Required** finding. For behaviour, write the test first, then fix. Then re-run step 5 and commit the fixes.
- List **Optional** and **Nit** findings for the user and don't act on them.
- A **creep** finding means removing the extra behaviour (or moving it to a new issue). Don't expand the issue to cover it.

### 8. Close out

Show what you're about to do and **ask before doing it**, because it's outward-facing:

- **Push** the branch and **open a PR** (`gh pr create` / `glab mr create`) against the default branch:
  - Title: the issue title, prefixed `[PROJ-123]` for Jira.
  - Body: what changed, the acceptance criteria with ticks, how it was verified (checks run, manual checks done or pending), open review items (Optional/Nit), and `Closes #42` for tracker issues or the Jira link for Jira.
  - Draft if any manual verification is still pending.
  - The issue closes when the PR merges. Don't close it by hand.
- **Local tracker**: no PR needed unless the user wants one. Set `Status: done` in the issue file and add a closing note under `## Comments` (what shipped, the branch and commits).
- **Jira**: remind the user to move the Jira ticket, since you can't.

Then report:

- **Frontier**: tracker issues that this one unblocks once merged.
- **Checkpoint**: if the plan note puts a checkpoint after this issue, say so and **stop**. Don't suggest the next issue until the user has reviewed. Otherwise suggest `/implement <next frontier issue>` in a fresh session (`/clear` first).
- **Spec**: if this was the spec's last open child, say the spec issue can close once the PR merges.

Finish with the global work-log offer ("Log this to the worklog?"). For Jira tickets the note already exists, so the session goes straight onto it.

## Red flags

- Production code written before a failing test for it
- Behaviour beyond the acceptance criteria ("while I'm here…"). Open a new issue instead.
- Starting an issue with an open blocker, or one assigned to someone else
- Skipping `/review`, or leaving a Critical/Required finding unfixed
- Editing another issue's scope, or closing the spec issue by hand while children are open
- Pushing, opening a PR, or changing tracker state without asking
- Committing to the default branch

## Before you finish

- [ ] Every acceptance criterion has a test at a confirmed seam, and they all pass
- [ ] The full checks pass, and the results were reported
- [ ] `/review` ran, and its Critical/Required findings are fixed
- [ ] Work is committed on the issue branch, referencing the issue
- [ ] PR opened with `Closes #n` (or local `Status: done`, or Jira reminder), after the user agreed
- [ ] Unblocked frontier and any checkpoint reported
