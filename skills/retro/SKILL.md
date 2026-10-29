---
name: retro
description: "Conduct a retrospective on a coding session and propose improvements to the agent's environment."
disable-model-invocation: true
---

# Retro

The user has asked for a **retrospective**. You are suggesting improvements to the coding agent's **environment** so future runs go better. You change the environment, never the code the session produced, and you only **propose**: nothing is edited until the user picks a candidate.

## Steps

1. **Find the session.** Default to the current one. Otherwise locate it in the logs:
   - Transcripts: `~/.claude/projects/<cwd with / replaced by ->/<session-id>.jsonl`. Subagent transcripts sit in `<session-id>/subagents/`, large tool outputs in `<session-id>/tool-results/`.
   - Pick by recency (`ls -t`) or by the `ai-title` / `last-prompt` records.
   - Read the transcript through `jq`, never `cat`. Tool calls are `tool_use` blocks in `assistant` messages; results are `tool_result` blocks in `user` messages; `.message.usage` carries token counts. Start with a skeleton (tool name + first ~80 chars of input, result length), then open only the moments that matter.
   - For a long past session, delegate the read to `context-scout` with a narrow brief: the file path, the categories below, and "return moments as `turn index: what happened`".

2. **Read the repo's steering and guardrails** before judging anything: the repo `CLAUDE.md` or `AGENTS.md`, the global `~/.claude/CLAUDE.md`, the memory index, `.claude/settings.json` (permissions, hooks), `CODING_STANDARDS.md` if present, `.pre-commit-config.yaml`, `Makefile`/`Taskfile.yml`, `.golangci.yml`/`pyproject.toml`, and `.github/workflows/`. A check that already exists but is unwired or silently broken is the finding, not a reinvention.

3. **Find the struggle.** Mark the moments where the agent searched too long, made a mistake, retried, got corrected by the user, burned tokens on a fat tool result, or lacked information. A smooth session has little to teach; say so rather than invent findings.

4. **Map each moment to a category** (below) and pick the cheapest fix that would have prevented it.

5. **Present the candidates** in order of severity, then ask which to apply. Apply only the ones picked, as small diffs, and run the relevant checks afterwards.

## Categories

- **Navigation**: how easy was it to find the right files? Are there hidden dependencies between files (a Terraform module and the workflow that applies it, a Helm values file and the Flux `HelmRelease` that overrides it)? Would a **navigation pointer** from a file the agent already reads help? _Use when_ the session took a long time to find a piece of information.

- **Automated checks**: could a check have caught the agent's mistake? Look at the repo's own commands first (`make lint`, `go vet`, `golangci-lint`, `ruff`, `pytest`, `terraform fmt -check`/`validate`, `tflint`, `actionlint`, `zizmor`, `kubeconform`, `helm lint`). A repo with no **guardrail** (no pre-commit hook and no CI job running its lint/typecheck/test) is itself a finding. _Use when_ the agent made a mistake a tool could catch, or the repo has no guardrail at all.

- **Coding standards**: classify the violation first.
  - **Mechanical** (a fixed pattern: unpinned action SHA, missing `permissions:`, `latest` image tag, missing resource limits, wildcard IAM `Action`, bare `except:`, unwrapped Go error): gets a deterministic check, full stop. Pick whichever is cheapest given what the repo already runs: a linter rule, a pre-commit hook, a CI job, or a policy check (`conftest`/`checkov`/`kube-linter`).
  - **Judgement call** (cross-file consistency, "matches the surrounding style", naming that fits the domain): goes in the repo's `CODING_STANDARDS.md`, which the **reviewer** reads. If that file doesn't exist yet, propose creating it (see **Steering bloat**) instead of adding the rule to `AGENTS.md`.
  - **Cross-repo judgement call** (applies to all your repos): goes in the review baseline, `~/.claude/skills/review/baseline.md`.
  _Use when_ the reviewer (the `reviewer` agent run by `/review`, the factory's gate role, or a PR reviewer) failed to catch a mistake, or the session's changes never went through `/review` at all.

- **Harness guardrails**: is a rule in a steering file actually mechanical at the tool level? "Never run `terraform apply`", "never read `.env`", "never force-push" are enforced better by `permissions.deny` / `ask` rules or a `PreToolUse` hook in `settings.json` than by prose. _Use when_ the agent broke, or nearly broke, a safety rule written as prose.

- **Steering bloat**: should instructions in the repo `CLAUDE.md`/`AGENTS.md` or global `~/.claude/CLAUDE.md` move to standards, a check, a harness guardrail, a skill, or a memory? A repo whose coding standards live in `AGENTS.md`/`CLAUDE.md` with no `CODING_STANDARDS.md` is itself a finding: every implementation session pays for rules only review needs. The fix is a split: move the standards into `CODING_STANDARDS.md`, leave `AGENTS.md` as a short index of **navigation pointers**; `/review` picks `CODING_STANDARDS.md` up automatically. Cross-repo rules in the global `~/.claude/CLAUDE.md` (stack conventions, not working style) move to the review baseline instead. _Use when_ a steering file is large or carries coding standards.

- **No-ops**: instructions that don't change behaviour versus the model's default. Delete the whole sentence. _Use when_ the steering files are large and unwieldy.

- **Tool economy**: were there expensive tool calls (whole-file reads, unpaged `gh run view --log`, `kubectl get -o yaml` on everything, full test suites when one test would do, exploration in the main session that `context-scout` should have done)? Is any CLI or MCP particularly token-inefficient? _Use when_ the agent made an expensive tool call.

- **Information access**: was a crucial piece of information out of reach? Candidates: a read-only AWS profile, a read-only kube context, `gh` access to CI logs, teeing local server/test output to a file, an MCP that needs auth (Atlassian/Jira). Grant read-only only; anything mutating stays behind a confirmation. _Use when_ the agent guessed or asked for something it could have looked up.

## Presenting candidates

For each candidate give:

- **Severity** (high / medium / low) and **category**.
- **Evidence**: the session moment that motivates it, quoted briefly with its turn.
- **Fix**: the exact file and change, the destination chosen per the table below.
- **Cost**: tokens it adds to every session (steering), or CI minutes/false-positive risk (checks).

Never more than ~7 candidates. Drop low-value ones rather than padding.

## Reference

### Implementation vs review

All work goes through two stages. The implementation agent carries the most **context pressure**: it explores, writes code, and debugs. The review agent receives a diff, so it has room to apply standards. Standards therefore belong to the reviewer, not the implementer's steering.

### Where fixes land

| Destination | Loaded | Use for |
| --- | --- | --- |
| Repo `CLAUDE.md` / `AGENTS.md` | Every session in the repo | **Navigation pointers** only, used sparingly |
| `~/.claude/CLAUDE.md` | Every session everywhere | Cross-repo working style; keep it shrinking |
| `settings.json` permissions/hooks | Enforced by the harness | Mechanical safety rules |
| Linter / pre-commit / CI job | On commit or PR | Mechanical code rules |
| `CODING_STANDARDS.md` | During review | Judgement calls; add pointers to docs if it passes ~1,000 lines |
| `~/.claude/skills/review/baseline.md` | During review, every repo | Cross-repo stack standards and smells |
| Docs (`docs/`) | When pointed to | Reference material; look for an existing doc first |
| Skill (`~/.claude/skills/` or repo `.claude/skills/`) | Description always, body on use | Procedures and user-invoked commands |
| Memory | Index every session | Facts about the user or project the repo can't record |

### Writing the fix

- State the target behaviour positively ("pin actions to a commit SHA"); a prohibition makes the banned behaviour more available.
- Keep one source of truth. If the repo (a `Makefile`, config file, `--help`) already says it, point to it instead of restating it.
- Prefer a short, precise word the model already knows over a sentence explaining it.
- Test each line: would the agent behave differently without it? If not, it's a no-op.
