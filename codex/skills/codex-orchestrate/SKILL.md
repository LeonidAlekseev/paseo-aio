---
name: codex-orchestrate
description: Coordinate an approved development task through Codex agents in Paseo using Matt Pocock skills, isolated worktrees, ticket dependencies and review. Use when the user requests Paseo orchestration or selects its coordinator profile.
---

# Codex orchestration through Paseo

Read `codex-pocock-paseo` before delegating. Use the installed Matt Pocock skill
catalog, including plugin-qualified names. Read the selected SKILL.md and the
references it calls for. Do not use paths under ~/.claude or infer that every
upstream slash command exists in Codex. If a required skill is missing, name it
and its installation step; do not claim to have run it.

## Choose the workflow

| Task | Pocock workflow |
| --- | --- |
| Feature | grill-me → to-spec → to-tickets → implement-spec |
| Large or unclear goal | wayfinder, then the feature workflow |
| Refactoring | improve-codebase-architecture → tickets → implement-spec |
| Bug | diagnosing-bugs → scoped fix → review |
| Review | code-review plus ponytail:ponytail-review when installed |
| Issue triage | triage |

For small tasks, keep the ticket and execution plan short. Research can be
performed by `codex-code-research` or `codex-web-research` with a read-only brief. Image tasks use `codex-images` and require an
available image tool; the Codex provider alone does not guarantee one.

## Prepare

Read the project's AGENTS.md and branch policy, then apply
[the tracker policy](references/issue-tracker.md). Unavailable remote issues
fall back to local Markdown; they are not a prerequisite for setup or execution.
Use the same policy when following setup-matt-pocock-skills: record the selected
tracker and map its publish/label/close operations to the local files. An
explicitly selected local tracker does not require remote authorization.

Discover the existing Paseo project/workspaces and agents. Check active tasks in
the selected tracker and open PRs when their host is accessible. Resume existing
work rather than duplicating it. Never create public issues or publish branches
merely to set up this stack.

Resolve the target branch from the project/user. The original AIO default is
dev; if absent, ask which integration branch to use before creating one. Fetch
the chosen remote, then create integration/<spec> from its current remote ref.
For a single ticket, a branch directly from the agreed target is sufficient.

## Agree scope and execute

Show the spec/ticket plan, dependencies, checks and risks when not already
approved. Reuse explicit approval already given for that scope. Set
ready-for-agent in the selected tracker only within that approval; silence is
not consent. Local tickets use file paths and Status fields, not server IDs.

Run one executor per unblocked ticket through the adapter. Parallelize only
independent tickets. The coordinator owns tracker and dependency updates;
executors report out-of-scope findings instead of implementing them.

On an executor question, answer from agreed requirements or inspect the code.
Escalate only missing product decisions or material scope changes to the user.
Retry transient failures at most three times; record what changed between
attempts. Continue independent tickets while a dependency is blocked.

## Review and integrate

Merge completed tickets into the integration workspace sequentially. Run the
project checks. Read code-review and launch its Standards and Spec reviewers
through Paseo, then consolidate findings and send a scoped fix request to an
executor. Do not mechanically let a passing test override a wrong requirement.
Resolve disputed findings against requirements and evidence; ask the user when
the dispute needs a product decision.

Prepare a PR to the agreed target. Publish and merge only within the user's
authorization, using the project's merge policy and confirmed CI results.
Close remote issues or resolve local tickets only after their required merge
and checks are verified. Releases to main require a release
request; a development task is not a release request.

Archive only idle agents and workspaces whose work is merged or otherwise
preserved. Keep local tracker history in the main checkout. Check for
uncommitted/unpushed changes first. Report PR links or local ticket paths, checks,
blocked work and any cleanup deliberately left pending.
