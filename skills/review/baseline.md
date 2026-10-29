# Review baseline

Standards that apply even when a repo documents nothing. Two rules bind them:

- **The repo overrides.** A documented repo standard always wins; where it endorses something below, suppress the finding.
- **Tooling first.** Skip anything a linter, pre-commit hook, or CI job in the repo already enforces.

## Stack rules

Breaches here are **Required** at least (**Critical** for security exposure and secrets; **Optional** for cost) unless the repo overrides them.

- **Go**: errors wrapped with `fmt.Errorf("...: %w", err)`; `context.Context` propagated, not replaced with `context.Background()` mid-call-chain; no `panic` in library code.
- **Python**: type hints on public functions; explicit exception types, no bare `except:`.
- **GitHub Actions**: third-party actions pinned to a full commit SHA with a version comment; minimal top-level `permissions:`, widened per job; AWS via OIDC (`aws-actions/configure-aws-credentials`), never static keys; `concurrency:` on deploy workflows; `timeout-minutes` on jobs; no `pull_request_target` checking out untrusted code; no `github.event.*` interpolated into `run:`.
- **Kubernetes**: resource requests/limits; liveness and readiness probes; non-root `securityContext` with `readOnlyRootFilesystem` and `capabilities.drop: [ALL]`; current stable API versions.
- **Terraform / IAM**: provider and module versions pinned; no wildcard `Action` or `Resource` without a justifying comment.
- **Security exposure**: no security groups or NACLs open to `0.0.0.0/0` beyond public LB listeners; no public S3 buckets or policies with `Principal: "*"`; encryption at rest on new storage; IMDSv2 required on instances; no `privileged`, `hostNetwork`, or `hostPath` pods; container images pinned by tag or digest, never `latest`; no secrets or tokens written to logs or workflow output.
- **Reliability**: outbound HTTP/gRPC/SDK calls carry a timeout or deadline; AWS SDK list/describe calls use paginators; retries have backoff and a cap; goroutines started in the diff have an exit path; no unbounded loops or fetches over external data.
- **Cost**: flag NAT gateways, cross-AZ traffic, oversized instances, unbounded log retention, idle load balancers introduced by the diff.
- **Secrets**: no credentials, tokens, kubeconfigs, or state files committed.

## Code smells

Fowler, _Refactoring_ ch.3. Always judgement calls, at most **Optional**: label each as "possible <smell>". Each reads _what it is_ → _how to fix_.

- **Mysterious Name**: a name that doesn't reveal what it does or holds. → rename; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape in more than one hunk or file. → extract the shared shape.
- **Feature Envy**: a function reaching into another type's data more than its own. → move it onto the data it envies.
- **Data Clumps**: the same few fields or params travel together. → bundle them into one type.
- **Primitive Obsession**: a primitive or string standing in for a domain concept. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs. → polymorphism, or one shared map.
- **Shotgun Surgery**: one logical change forces scattered edits across many files. → gather what changes together.
- **Divergent Change**: one file edited for several unrelated reasons. → split so each changes for one reason.
- **Speculative Generality**: abstraction, params, or hooks for needs the spec doesn't have. → delete; inline until a real need shows.
- **Message Chains**: long `a.B().C().D()` navigation the caller shouldn't depend on. → hide the walk behind one method.
- **Middle Man**: a type or function that mostly delegates onward. → cut it, call the real target.
- **Refused Bequest**: an implementer that ignores most of what it embeds or inherits. → drop it, use composition.
