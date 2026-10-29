# Global instructions

## About me
Mid-to-senior backend engineer (Go, Python; some Java), currently working in DevOps:
GitHub Actions, AWS, and Kubernetes (CKAD). Skip programming basics; for AWS and
newer DevOps topics, explain the reasoning and trade-offs.

## Working style
- For non-trivial changes, outline the plan first and wait for approval before
  large refactors or multi-file changes.
- Prefer small, reviewable diffs. Don't reformat or rename unrelated code.
- Default to Go or Python for new scripts and tools unless the repo dictates otherwise.
- Follow the existing conventions of the repo over my general preferences.
- After changes, run the relevant checks and report results:
  - Go: `go build ./...`, `go vet ./...`, `go test ./...`
  - Python: `ruff check`, `pytest`
  - Terraform: `terraform fmt -check`, `terraform validate`
- If a check fails and the fix isn't obvious, stop and explain instead of guessing.
- Lead with the direct answer, then explain. Professional tone, balanced length.

## Safety rules (always)
- Never run mutating infra commands without asking first: `terraform apply`,
  `kubectl apply/delete/patch/scale`, `helm install/upgrade/uninstall`, or AWS CLI
  commands that create, modify, or delete resources. `plan`, `diff`,
  `--dry-run=server`, and read-only `get/describe/list` calls are fine.
- Before any infra command, state which AWS profile/account and kube context it targets.
- Never read, print, or commit secrets: `.env` files, kubeconfigs, AWS credentials,
  Terraform state, K8s Secret contents. If a secret is needed, ask me to provide it
  via an environment variable.
- Never force-push, rewrite published git history, or push directly to main/master.

## GitHub Actions
- Pin third-party actions to full commit SHAs (with a version comment).
- Declare minimal top-level `permissions:` and widen per job only when needed.
- Use OIDC (`aws-actions/configure-aws-credentials`) for AWS; never static keys.
- Add `concurrency:` for deploy workflows; set `timeout-minutes` on jobs.
- Avoid `pull_request_target` with checkout of untrusted code; never interpolate
  untrusted input (`github.event.*`) directly into `run:` scripts.

## Kubernetes
- Include resource requests/limits, liveness/readiness probes, and a non-root
  `securityContext` (readOnlyRootFilesystem, drop ALL capabilities) by default.
- Use current stable API versions and flag deprecated/removed ones for the
  cluster version in the repo's CLAUDE.md.

## AWS / IAM / Terraform
- Least privilege: call out any wildcard `Action` or `Resource` and justify it.
- Pin provider and module versions.
- Flag cost implications (NAT gateways, cross-AZ traffic, oversized instances,
  unbounded log retention, idle load balancers).

## Code quality
- Go: idiomatic error wrapping (`fmt.Errorf("...: %w", err)`), context propagation,
  no panics in library code.
- Python: type hints, explicit exceptions, no bare `except:`.
- Mention version-specific behavior (K8s API, action, SDK versions) when it matters.

## Work log
- When a task reaches a natural completion point (tests pass, PR opened, bug root-caused,
  decision made), ask once: "Log this to the worklog?" If yes, use the worklog skill.
- Don't offer for trivial tasks (typos, quick questions), and at most once per ticket per session.
- If I say "don't log this repo", stop offering for the rest of the session.

## Context gathering
- When you need context (locating code, tracing a flow, reading several files, repo-wide grep),
  delegate to the `context-scout` subagent instead of reading files in the main session.
- Read directly only when the target file and line range are already known, or before editing.
- Never use `general-purpose` for lookups or searches; use `context-scout`. Spawn a subagent
  only when it saves more context than it costs, and give it a narrow, explicit brief.

## Usage / context hygiene
- One ticket or PR per session. When a PR merges (or a task completes), say so and suggest
  `/clear` before starting the next one; state is carried by memory and git, not the chat.
- When context passes ~100k tokens mid-task, suggest `/compact` instead of continuing.
- Keep tool output small: `gh run view --log-failed | tail -n 80`, `go test -run <name>`,
  `| tail`/`| head` on long output. Don't re-poll CI across turns; use one
  `gh pr checks --watch` (or a background Monitor).
- Never ScheduleWakeup or poll for a background agent or command; the harness notifies on completion.
- For mechanical, pattern-following work (label maps, i18n wiring, renames), suggest
  switching to Sonnet via `/model`; keep Opus for specs, planning, and debugging.
