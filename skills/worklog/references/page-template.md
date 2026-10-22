# Ticket note template

The frontmatter `title` is the ticket title only (e.g. `Migrate deploy workflow to OIDC`); the
`ticket_id` field holds `PROJ-123`. The display label `[PROJ-123] <title>` is built from both.
This is the note body, below the frontmatter (see `Worklog/_schema.md` in the vault).

## New note body (create once)

```markdown
## Goal / Why
<1–3 sentences: the problem, who/what it affects, why it matters now.>

## Outcome
_Filled in when the ticket is Done: what shipped, measurable result, follow-ups._

## Key decisions
<Running list, one line each, updated when a session makes a lasting decision:>
- <YYYY-MM-DD> <decision> — <why> (see session)

## Session log
```

## Session entry (append each session under "Session log")

```markdown
### YYYY-MM-DD — <short session title>
**What:** <what was done, 1–3 bullets, concrete>
**Why:** <the reasoning or trigger for this work today>
**Decisions & trade-offs:**
- <chose X over Y because Z>
**Changes:** `<owner/repo>`: <files/resources touched, e.g. `.github/workflows/deploy.yml`> · <PR/commit links>
(one line per repo when a session touches several)
**Commands / config worth keeping:** <only non-obvious, sanitized snippets; omit if none>
**Problems hit:** <errors and the fix/root cause; omit if none>
**Next:** <open questions, follow-ups, blockers>
```

Omit empty fields instead of writing "none". If a session made a lasting decision, also add
one line to **Key decisions** at the top of the page.

## Example entry

```markdown
### 2026-09-28 — Switch deploy workflow to OIDC
**What:**
- Replaced static AWS keys in `deploy.yml` with `aws-actions/configure-aws-credentials` + OIDC
- Added IAM role `gha-deploy-staging` scoped to the repo's `main` branch
**Why:** Static keys were flagged in the security review; rotating them was manual and error-prone.
**Decisions & trade-offs:**
- Trust policy restricted with `sub: repo:<org>/<repo>:ref:refs/heads/main` rather than `repo:<org>/<repo>:*`, so PR builds can't assume the deploy role.
- Kept one role per environment instead of one shared role, for blast-radius isolation (slightly more Terraform).
**Changes:** `acme/app-api`: `.github/workflows/deploy.yml` · PR #142
`acme/platform-infra`: `iam/github-oidc.tf` · PR #87
**Problems hit:** `Not authorized to perform sts:AssumeRoleWithWebIdentity` — workflow lacked `permissions: id-token: write`.
**Next:** Apply the same pattern to the prod workflow; delete the old IAM user's keys after one week.
```
