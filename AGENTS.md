# Paseo AIO

The Claude setup (`install.sh`, `claude/`, `paseo/`) and Codex setup
(`install-codex.sh`, `codex/`) coexist. Change the requested variant and preserve
the other's installation behavior.

## Agent skills

### Issue tracker

Use local Markdown in `.scratch/` for this repository.
Before creating or updating specs/tickets, read
`docs/agents/issue-tracker.md`. The GitHub origin is not the active issue tracker.
For tracker setup or changes in any project using this stack, follow
`codex/skills/codex-orchestrate/references/issue-tracker.md`: unavailable remote
issues fall back to local files rather than blocking work.

### Triage labels

Use the default five triage roles in `docs/agents/triage-labels.md`.

### Domain docs

This repository has one domain context. Before domain research or architecture
work, read `docs/agents/domain.md` for glossary and ADR conventions.

### Paseo orchestration

For delegated development, use `codex-orchestrate` and `codex-pocock-paseo`.
Before creating agents or worktrees, read `docs/agents/orchestration.md`.

## Validation

Run the shell syntax and Python test commands in `.github/workflows/codex.yml`.
For installer changes, also run `./install-codex.sh` (preview only) against a
reachable daemon. Check write/rollback behavior with temporary fixtures, not by
reapplying a real user's configuration. Test changed command arguments against
the installed CLI using a non-mutating mode when available.

Describe checks that require installed tools separately from tests that run in
plain CI. Keep English and Russian setup instructions consistent when behavior
changes.
