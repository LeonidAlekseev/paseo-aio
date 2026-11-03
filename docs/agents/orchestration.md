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

## Branches and integration

Upstream contributions target `main`. Use the integration branch agreed for the
task and preserve existing work. Create ticket worktrees from a committed base
that contains their dependencies; uncommitted files in another checkout are
not inherited. Follow the user's authorization for commits and publication.

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
