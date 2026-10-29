# Tracker: GitLab

Issues and specs live as GitLab issues. Use the [`glab`](https://gitlab.com/gitlab-org/cli) CLI for all operations; it infers the project from `git remote -v` when run inside a clone.

## Conventions

- **Create an issue**: `glab issue create --title "..." --description "..." --label "a,b"`. Use a heredoc for multi-line descriptions.
- **Read an issue**: `glab issue view <n> --comments` (`-F json` for machine-readable output).
- **List issues**: `glab issue list -O json` with `--label` filters.
- **Comment**: `glab issue note <n> --message "..."`. GitLab calls comments "notes".
- **Apply / remove labels**: `glab issue update <n> --label "..."` / `--unlabel "..."`.
- **Create a label**: `glab label create --name "<name>" --color "#<hex>"`.
- **Close**: `glab issue close <n>` takes no comment, so post the explanation with `glab issue note` first.
- **Merge requests**: `glab mr create|view|note|...`, the same shape as `gh pr ...` with `note`/`--message` in place of `comment`/`--body`.

## Specs and their issues

- **Spec issue**: labels `spec`, `spec::<slug>` (scoped label) and a category; no state label.
- **Child issue under the spec**: put `Part of #<spec>` at the top of the description and add a relates-to link (`glab issue note <child> --message "/relate #<spec>"`). On tiers with epics, the user may prefer an epic as the spec; follow the block if it says so.
- **Blocking edge**: native blocking link via quick action: `glab issue note <blocked> --message "/blocked_by #<blocker>"` (Premium/Ultimate). On the free tier, fall back to a `Blocked by: #<n>, #<n>` line at the top of the description. An issue is unblocked when every blocker is closed.
- **List a spec's issues**: `glab issue list --label "spec::<slug>" --all -O json`.
- **Frontier**: open issues labelled `spec::<slug>` and `ready-for-agent`, with no open blocker (`glab api projects/:id/issues/<iid>/links`, or the `Blocked by` line) and no assignee.

## Merge requests as a triage surface

Read the `**PRs as a request surface:**` line of the `## Agent skills` block. When `yes`, MRs run through the same labels and states:

- **Read an MR**: `glab mr view <n> --comments` and `glab mr diff <n>`.
- **List external MRs**: `glab mr list -F json`, keeping only MRs whose author is not a project member.
- **Comment / label / close**: `glab mr note`, `glab mr update --label` / `--unlabel`, `glab mr close`.

GitLab numbers issues and MRs separately, so `#42` is an issue and `!42` an MR.

## Skill verbs

- "Publish to the tracker" → create a GitLab issue.
- "Fetch the issue" → `glab issue view <n> --comments`.
