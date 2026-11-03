<!-- PASEO_CODEX_STACK_START -->
## Paseo + Codex orchestration

For development explicitly delegated through Paseo, use `codex-orchestrate` and
`codex-pocock-paseo`. Matt Pocock skills define the engineering process; Paseo
owns agent creation, workspaces and communication. Use installed skill paths
from the skill catalog; do not assume Claude plugin paths or slash commands.

Before any spec/issue/ticket operation (including direct Pocock skills), read
`references/issue-tracker.md` in the installed `codex-orchestrate` skill. If remote
issues are unavailable, continue with local `.scratch/<feature>/spec.md` and
`issues/<NN>-<slug>.md`; record the choice and reason in the project's tracker
instructions. Preserve explicit local choices, scope approval and existing work.

Use the `codex-*` Paseo profiles. Executors work on one scoped ticket in their
own worktree; they do not delegate again. Keep at most three writers, with
independent file ownership. Preserve the user's existing approvals and scope.

Project AGENTS.md and the agreed spec define checks and the integration branch.
For projects following the original AIO workflow, target `dev` with merge
commits. Do not create or change the project's branch policy without agreement.
Never force-push, discard unrelated changes, or weaken tests to complete a ticket.
The installed prefix rules add checks for common dangerous Git commands, but
are not a universal shell policy; retain server-side branch protection.

Use CodeGraph when its index is available; use rg/read when unavailable. In a
fresh worktree, allow the trusted SessionStart hook to initialize CodeGraph,
and use the adapter's manual fallback if needed. Use
`ponytail:ponytail-review` when installed before handing off a code change.
Reports must distinguish completed checks from checks that could not run.
<!-- PASEO_CODEX_STACK_END -->
