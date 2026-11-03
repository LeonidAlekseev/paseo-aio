# Orchestration in this repository

## Project and launch

Use the Paseo project whose path is this Git root, not the enclosing non-Git
directory. Resolve its projectId with `paseo project ls`; machine-specific IDs
do not belong in repository configuration.

Start the coordinator in this repository's local workspace with the
`codex-orchestrator` profile. Before delegation, verify that the session exposes
Paseo's `list_profiles`, `create_workspace`, `create_agent` and completion tools.
Installed skills and a successful CLI connection alone do not prove MCP
injection. If the tools are absent, fix session injection before launching
children; do not substitute an untracked process.

Read every selected profile's notes. The repository uses the installed
`codex-*` roles; model, reasoning and permission mode come from those profiles.

## Current review boundary

The Codex port is being reviewed as uncommitted changes on `codex-port`.
The user has withheld permission to commit and push until checking the result.
Setting up orchestration does not lift that restriction. Work on the local
checkout and return diffs/check results until the user changes this instruction.

New worktrees contain committed files from their base revision, not this dirty
checkout. Do not assign a ticket requiring the Codex port to a fresh worktree
and assume those files exist. A read-only review can inspect the current local
workspace after writers are idle; implementation delegation needs an explicitly
agreed snapshot/commit first.

## Branches and integration

The remote default is `origin/main`; there is no `dev` branch. Keep the current
`codex-port` work intact. Before the first implementation batch, agree whether
integration targets the port branch, main, or a new dev branch. Setup itself
creates no integration branch, PR, merge or release.

Once the base and scope are approved, use Paseo-managed worktrees and the
adapter's ticket dependency rules. Serialize integration merges and changes to
the same files. Keep local spec/ticket paths anchored in the main checkout as
described in `issue-tracker.md`. Apply its shared fallback policy if a remote
tracker is selected later and becomes unavailable; local tracking does not
require GitHub/Gitea issue access.

## Checks and reports

Run the checks in root `AGENTS.md`. A ticket report includes scope, changed files,
commands actually run, results and remaining limitations. Record unexecuted
browser, plugin, hook-trust or multi-agent checks as unverified.

Publish, merge, close tickets and archive workspaces only within the user's
authorization and after preserving their work.
