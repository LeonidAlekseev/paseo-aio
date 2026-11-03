# Issue tracker selection and local fallback

Apply this policy before setup, spec/ticket creation, triage, delegation or
completion updates, including when following a Matt Pocock skill directly.
Preserve any explicit project/user requirement for a different workflow.
Otherwise unavailable remote issues must not block local planning.

## Select and record

1. Read `docs/agents/issue-tracker.md` and any existing feature spec. An explicitly
   selected local tracker stays local; a Git remote or newly working credentials
   do not switch it back to the server.
2. For a remote tracker, check the intended repository with read-only calls to
   its actual CLI/API (GitHub: gh; Gitea: gt or tea; GitLab: glab). Confirm that
   issues are enabled and the operation needed by the task is available.
   Read-only work can continue with read-only access. Do not create a probe
   issue or request broader permissions merely to test access.
3. Use local Markdown when issues are disabled, needed access is denied,
   credentials/CLI/remote are missing, or no tracker is configured. Announce the
   reason and continue the authorized task without asking the user to enable
   issues or grant write access. For a transient network/server error, retry a
   read once before falling back. Missing requirements from an unreadable ticket
   still need an answer; do not invent its contents.
4. Record `Active tracker: local`, `Tracker root: .scratch/` and the reason in
   `docs/agents/issue-tracker.md`, preserving unrelated instructions and prior
   remote details. Create the file if needed. Record `Tracker: local` in each
   local feature spec. Future operations follow that selection instead of
   repeating the failed remote operation. A later migration is a user decision.

If a remote write times out, its outcome is unknown. Reconcile it with a read
before retrying. If reconciliation is unavailable, retain a local continuation
marked `needs-info` with the attempted operation; do not submit a second copy
or claim the remote write succeeded. For existing remote work, retain its URL
as `Source:` and reuse known local continuations. Leave remote state unchanged
until a separately authorized reconciliation/migration.

## Local files

One feature directory in the coordinator's main checkout:

```text
.scratch/<feature-slug>/
├── spec.md
└── issues/
    ├── 01-<ticket-slug>.md
    └── 02-<ticket-slug>.md
```

Use one file per ticket, numbered from `01`. Identify tickets by feature and
number (or file path), not a fabricated server `#number`. A ticket starts with:

```markdown
# 01 — Ticket title
Status: needs-triage
Spec: ../spec.md
Blocked by: none

## Scope
The approved change and its limits.

## Checks
Observable completion criteria and relevant commands.

## Comments
Decisions and execution reports, appended in order.
```

Use the project's triage mapping, or default to `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`, `wontfix`. Set `ready-for-agent` only for
approved scope; reuse approval already given. Use `claimed` while executing and
`resolved` only after agreed checks and required integration are confirmed.
Local tracking does not authorize commits, pushes, merges or a broader task.

`Blocked by: 01, 02` refers to tickets in the same feature; use explicit paths
for another feature. Start a dependent only after blockers are resolved and
their required code is in its base revision. On failure, record the blocker
and a pending state instead of marking the ticket resolved.

"Publish a spec/issue" means write the file; "fetch" means read it; "label"
means update Status; "comment" means append under Comments; "close" means mark
resolved after verifying completion. Never call gh/gt/glab issue commands for
local operations. For wayfinding, use a feature `map.md` with Notes,
Decisions-so-far and Fog; child tickets carry Type and append results under
Answer before the map links to them.

## Worktrees and pull requests

Only the coordinator writes tracker files. Give executors absolute spec/ticket
paths in the main checkout; uncommitted files are not inherited by worktrees.
For a remote host, supply an accessible read-only copy/reference and keep the
coordinator's files authoritative. Executors report results without maintaining
divergent tracker copies. Keep `.scratch/` records when archiving workspaces.

Local issues do not disable Git hosting or PRs. Code and PRs can remain on Gitea,
GitHub or GitLab when separately available and authorized. Use local ticket
identifiers in PR bodies, not `Closes #NN` for unrelated remote issues. Do not
publish local spec contents or migrate tasks to the server without authorization.
