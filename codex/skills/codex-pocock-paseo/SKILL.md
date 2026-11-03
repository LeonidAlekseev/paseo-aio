---
name: codex-pocock-paseo
description: Translate Matt Pocock workflow roles into Codex agents managed by Paseo. Use with codex-orchestrate to select profiles, create worktrees, brief executors and reviewers, and collect results.
---

# Pocock → Paseo → Codex

Read the installed `paseo` skill for the current tool schema. Use Paseo's MCP
tools for delegation so work is visible in the user's Paseo client. Do not
substitute Codex's internal subagents or a detached codex exec process. If MCP
tools are missing, report the missing Paseo injection and start a new session
after fixing it; do not invent tool calls.

## Tracker handoff

Apply [the tracker policy](../codex-orchestrate/references/issue-tracker.md) before
briefing or updating a ticket. Use the tracker recorded by the coordinator;
executors do not reselect it. Local tickets are files under `.scratch/`, with
Status and Blocked by fields. Pass their absolute paths in the main checkout
(or an accessible read-only reference for a remote host). Only the coordinator
updates them. Issue unavailability does not prevent separately authorized PRs.

## Profiles

Call list_profiles and read profile notes for each launch.

| Role | Profile |
| --- | --- |
| Coordinator | codex-orchestrator |
| Architecture, migrations, extensive refactoring | codex-implementer-heavy |
| Typical feature, bug fix, UI, fixes after review | codex-implementer-medium |
| Local change in a few files | codex-implementer-light |
| Mechanical rename, boilerplate, small text change | codex-implementer-trivial |
| Sequential integration merge | codex-merger |
| Standards / Spec reviewer | codex-reviewer |
| Code exploration | codex-code-research |
| Web/API research with sources | codex-web-research |
| Image assets, if an image tool is available | codex-images |
| Independent architecture opinion | codex-advisor |
| Disputed review finding | codex-arbiter |

For create_agent, combine profile.provider and profile.model as provider/model.
Copy modeId and thinkingOptionId into settings; map featureValues to
settings.features only when present. Do not invent a profile argument or change
permission mode to work around an error. A reviewer's read-only brief is an
instruction, not an OS sandbox; the selected profile mode remains authoritative.

Independent passes with models from the same family are not cross-family review.
The user can edit model/effort in the profiles.
For a missing profile or unavailable model, report the mismatch and rediscover
provider capabilities before proposing a replacement.

## Placement and limits

Use the existing projectId and the agreed base ref. Create worktrees through
Paseo create_workspace, not git worktree add:

- Integration: isolation=worktree, mode=branch-off,
  branchName=integration/<spec>, baseBranch=<agreed remote ref>.
- Ticket: isolation=worktree, mode=branch-off,
  branchName=ticket/<id>-<slug>, baseBranch=refs/heads/integration/<spec>.
- Review the integration workspace after writers have stopped. Include its
  exact commit SHA in the brief, so both reviewers examine the same revision.
- Leave background unset unless the user explicitly wants hidden workspaces.

Pass the returned workspaceId to create_agent. For a remote host, keep serverId
with both workspaceId and agentId and use paths on that host.

At most three code writers and two reviewers/researchers run concurrently.
Merger operations on the integration workspace are sequential. Tickets sharing
files or a changing contract run sequentially. Start only approved tickets with
their prerequisites integrated; do not hide blocked dependencies.

## Executor brief

Include the selected tracker and ticket/spec URLs or file paths, scope,
worktree path, expected branch, base SHA,
dependencies, checks and required deliverables. Explicitly state:

1. Verify cwd and branch. On a mismatch, report it; never reset/discard changes.
2. The Codex SessionStart hook indexes new worktrees asynchronously after it is
   trusted. Until it finishes, use rg/read. If indexing did not start, run the
   installed `python3 ~/.codex/hooks/paseo-codegraph-autoindex.py </dev/null`
   (use the actual CODEX_HOME if customized); it locks per worktree. If it fails,
   report that and continue with rg/read. Never assume an index is ready.
3. Implement the scoped ticket, following the selected Pocock skill and the
   project's testing policy. Do not change unrelated files or weaken checks.
4. Run the installed ponytail:ponytail-review skill, if available, on the diff.
   Record unavailable tools rather than claiming their checks passed.
5. Merge the latest agreed integration branch without rebase, rerun affected
   checks and commit within authorization. Do not push to the target branch.
6. Do not create more agents or edit tracker state. Ask the coordinator for
   missing decisions. Report changes, actual checks, commit and remaining risks.

Review/research briefs say: do not edit repository files, commit or publish;
return findings with file/line references and evidence. Web research needs
actual web tools and citations, not just a model with a research label.

## Results and cleanup

Keep notifyOnFinish=true and use Paseo's completion callbacks. Answer questions
by send_agent_prompt to the same agent, with serverId when remote. Do not poll
in a tight loop or create a replacement agent simply because a reply is pending.

Verify results before marking a ticket done. Merge in the integration workspace,
run checks, then review the resulting revision. Archive ticket workspaces only
when their commits are preserved and there are no outstanding writes. Never
archive the user's active coordinator or an unrelated workspace.
