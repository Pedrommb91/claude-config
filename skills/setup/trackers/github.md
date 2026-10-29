# Tracker: GitHub

Issues and specs live as GitHub issues. Use the `gh` CLI for all operations; it infers the repo from `git remote -v` when run inside a clone.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body-file - --label a --label b <<'EOF' ... EOF`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <n> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,labels --jq '[.[] | {number, title, labels: [.labels[].name]}]'` with `--label` / `--state` filters. Add `body,comments` only when you need them.
- **Comment**: `gh issue comment <n> --body "..."`
- **Apply / remove labels**: `gh issue edit <n> --add-label "..."` / `--remove-label "..."`
- **Create a label**: `gh label create "<name>" --color <hex> --description "..."` (skip if `gh label list --search "<name>"` already shows it).
- **Close**: `gh issue close <n> --comment "..."`
- **Database id** (needed by the REST calls below): `gh api repos/{owner}/{repo}/issues/<n> --jq .id`. Not the `#number`, not the `node_id`.

## Specs and their issues

- **Spec issue**: `gh issue create` with labels `spec`, `spec:<slug>` and a category; no state label. Create `spec:<slug>` first if missing.
- **Child issue under the spec**: `gh issue create --parent <spec#> ...` (`gh` 2.94+), or `gh issue edit <spec#> --add-sub-issue <child#>` afterwards. Older `gh`: `gh api --method POST repos/{owner}/{repo}/issues/<spec#>/sub_issues -F sub_issue_id=<child-db-id>`. Without sub-issues, put `Part of #<spec>` at the top of the child body.
- **Blocking edge**: native issue dependencies: `gh api --method POST repos/{owner}/{repo}/issues/<blocked#>/dependencies/blocked_by -F issue_id=<blocker-db-id>`. Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the body. An issue is unblocked when every blocker is closed.
- **List a spec's issues**: `gh issue list --label "spec:<slug>" --state all`.
- **Frontier** (what can start now): open issues labelled `spec:<slug>` and `ready-for-agent`, with no open blocker (`issue_dependencies_summary.blocked_by == 0` from `gh api repos/{owner}/{repo}/issues/<n>`, or no open issue on the `Blocked by` line) and no assignee.

## Pull requests as a triage surface

Read the `**PRs as a request surface:**` line of the `## Agent skills` block. When `yes`, PRs run through the same labels and states as issues:

- **Read a PR**: `gh pr view <n> --comments` and `gh pr diff <n>`.
- **List external PRs**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, labels: [.labels[].name]}'`.
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label` / `--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs: resolve a bare `#42` with `gh pr view 42`, falling back to `gh issue view 42`.

## Skill verbs

- "Publish to the tracker" → create a GitHub issue.
- "Fetch the issue" → **Read an issue** above.
