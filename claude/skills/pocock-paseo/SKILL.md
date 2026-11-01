---
name: pocock-paseo
description: Adapter that runs the subagent roles of Matt Pocock's skills (implement-spec, implement, code-review, research, exploration) as Paseo agents chosen by profile. Use whenever an orchestrator following a Pocock skill needs to start, brief, wait for, merge, or archive a subagent.
---

# Pocock → Paseo adapter

Pocock decides **what** happens and in which order. Paseo decides **who** runs it and **where**.
When a Pocock skill says "start a subagent", "in its own worktree" or "in the background", do it with Paseo as described here. Do not use the built-in Agent/Task tool for these roles.

## Reading Pocock skills

Many Pocock skills are slash-only (`disable-model-invocation`). When the orchestrator needs one, read the file and follow it:

```bash
find ~/.claude/plugins -path '*mattpocock*' -path '*/<skill-name>/SKILL.md' | head -1
```

Also read the files next to SKILL.md (for example `agents/`) when the skill references them.

## Roles → profiles

Call `list_profiles` and use the profile with the matching `id`.

| Pocock role / task | Profile id |
| :-- | :-- |
| Implementer, ticket of HIGH complexity: refactoring, extensive changes, migrations, public API, cross-module logic, architecture | `implementer-heavy` |
| Implementer, MEDIUM ticket: typical feature, bug fix, several modules, UI code, fixes after review | `implementer-medium` |
| Implementer, LIGHT ticket: up to ~3 files, local change, no API change | `implementer-light` |
| Implementer, TRIVIAL ticket: renames, boilerplate, plain text or doc rewrites | `implementer-trivial` |
| Ticket that produces images or UI assets (PNG, transparent background) | `images` |
| Merger (`implement-spec` step 5) | `merger`. Non-trivial conflict → `implementer-medium` |
| Exploration subagent / "how does X work" about **this codebase** | `code-research` |
| Research that needs **the internet**: docs, APIs, data collection, browsing | `web-research` |
| Standards and Spec reviewers (`code-review` step 4) | `reviewer` (two agents in parallel) |
| Second opinion on architecture (only when needed) | `advisor` |
| Disputed review remarks, hard or unresolved disputes | `arbiter` |

Turn the profile into a `create_agent` call. Copy the fields one by one and never invent missing values:
`provider: "<provider>/<model>"`, `settings.modeId`, `settings.thinkingOptionId`, `settings.features` ← `featureValues`.
If no profile matches, do not launch the agent. Tell the user instead.

## Limits and frontier

- At most **3 code-writing agents** (implementer, images, merger) at the same time. Read-only roles (reviewer, research, advisor, arbiter) do not count, but keep at most 2 of them at once.
- Do not run tickets in parallel if they touch the same files or the same contract. Check this with CodeGraph (`codegraph_explore`, or the `codegraph_impact` / `codegraph_files` tools). If unsure, run them one after another.
- Launch only tickets labelled `ready-for-agent` whose blocking tickets are already merged into the integration branch.

## Workspaces

Use the repo's existing Paseo project (`paseo project ls`, pass `projectId`). This way the worktrees do not show up as new projects in the sidebar. Never create worktrees with `git worktree add`.

- **Integration branch:** `create_workspace` `{ isolation: "worktree", mode: "branch-off", branchName: "integration/<spec-slug>", baseBranch: "origin/dev", projectId }`. Run `git fetch origin` first. Merger agents work here.
- **Ticket:** `create_workspace` `{ isolation: "worktree", mode: "branch-off", branchName: "ticket/<N>-<slug>", baseBranch: "refs/heads/integration/<spec-slug>", projectId }`.
- **Research and review:** reviewers run in the integration workspace. `web-research` and `code-research` get their own background workspace (`background: true`).
- **Notes** that every agent can read go outside the repo: `~/.paseo-notes/<repo>/<spec-slug>/`.

CodeGraph indexes new worktrees automatically when the agent starts (SessionStart hook). Nothing needs to be done for it.

## Implementer brief (send as `initialPrompt`)

Keep it short and pass pointers instead of copying content:

```
Ticket #<N> (<URL>), spec #<S>. Worktree: <path>, branch ticket/<N>-<slug>, based on integration/<spec-slug>.
Notes: ~/.paseo-notes/<repo>/<spec-slug>/ (if any).
1. Confirm your branch is based on integration/<spec-slug>; if not, reset onto it.
2. Build the ticket with the `tdd` skill. Use CodeGraph before grep.
3. Typecheck, lint and run the relevant tests; run the full suite once at the end. Never weaken tests.
4. Run /ponytail-review on your diff and fix what you accept (one round).
5. Run `git merge integration/<spec-slug>` (no rebase), re-run the checks, and commit.
6. Do not edit issues or labels. Do not change files outside the ticket's scope. If scope must grow, stop and ask.
7. Final report: what you did, the checks and their results, rejected review remarks with the reason, and findings outside scope (path:line, why, suggested action). Do not implement those findings.
If you need a decision, ask a question and stop. The orchestrator will answer.
```

## Waiting, questions, answers

- `notifyOnFinish` stays at `true`. End your turn and wait for the notification. Do not poll.
- When an agent asks a question, answer only from the spec, the tickets, the code and decisions already made, via `send_agent_prompt` to **the same** agent. If none of these has the answer, ask the user and pass the answer on. Record decisions made along the way as a comment on the ticket.
- A failed check or a non-critical failure is retried up to 3 times. After that, stop the ticket and report it to the user.

## Merge and review

- **Merger:** in the integration workspace, run `git merge --no-ff ticket/<N>-<slug>`, run the checks, and push `integration/<spec-slug>`. Then `archive_agent` and `archive_workspace` for the ticket.
- **code-review** at the end of the spec: read its SKILL.md. Steps 1–3 are done by the orchestrator (fixed point is `origin/dev`). Step 4 is two `reviewer` agents with the briefs from that skill. Step 5 is the orchestrator aggregating the reports.
- Fixes after review go to one new implementer, whose profile matches the size of the fixes.
- Review conflicts are decided by this priority: tests > spec/ticket > Ponytail > advisor/arbiter. A repeated dispute goes to `arbiter`. If that does not settle it, the user decides.
