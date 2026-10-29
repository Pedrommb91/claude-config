# Labels

The skills speak in canonical role names. The `**Labels:**` line of the `## Agent skills` block says `defaults` or lists overrides (`defaults, except needs-triage → bug:triage`); when a skill names a role, apply the label string the block maps it to.

| Role              | Default label     | Colour   | Meaning                                       |
| ----------------- | ----------------- | -------- | --------------------------------------------- |
| `bug`             | `bug`             | `d73a4a` | Something is broken                           |
| `enhancement`     | `enhancement`     | `a2eeef` | New feature or improvement                    |
| `needs-triage`    | `needs-triage`    | `fbca04` | Maintainer needs to evaluate                  |
| `needs-info`      | `needs-info`      | `d4c5f9` | Waiting on the reporter for more information  |
| `ready-for-agent` | `ready-for-agent` | `0e8a16` | Fully specified, ready for an AFK agent       |
| `ready-for-human` | `ready-for-human` | `1d76db` | Needs human implementation                    |
| `wontfix`         | `wontfix`         | `ffffff` | Will not be actioned                          |
| `spec`            | `spec`            | `5319e7` | A spec: the parent of a set of issues         |
| `spec:<slug>`     | `spec:<slug>`     | `c5def5` | Groups a spec and all of its issues           |

`/setup` creates every label except `spec:<slug>`; `/spec` creates that one per spec. On GitLab use the scoped form `spec::<slug>`.

## Rules

- A triaged issue carries exactly one category role and one state role.
- A **spec issue** carries `spec`, `spec:<slug>` and a category, and **no state role**: it is a container, so an agent looking for `ready-for-agent` work never picks it up. Close it when its last child closes.
- A **child issue** of a spec carries `spec:<slug>`, a category and a state role (normally `ready-for-agent`).
- No size, priority or type labels beyond these; size goes in the issue body.
- Local tracker: roles are recorded as `Status:` / `Category:` lines in the file instead of labels (see trackers/local.md).
