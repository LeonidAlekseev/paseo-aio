# Paseo AIO

**🇬🇧 English** | [🇷🇺 Русский](README.ru.md)

[![Claude Code](https://img.shields.io/badge/Claude%20Code-2.1.316-d97757)](https://claude.com/claude-code)
[![Paseo](https://img.shields.io/badge/Paseo-0.14.0-black)](https://paseo.sh)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)](#tested-versions)
[![Shell](https://img.shields.io/badge/install-bash-4EAA25?logo=gnubash&logoColor=white)](install.sh)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A one-command setup for orchestrated development in Claude Code. Matt Pocock's skills run the engineering process,
Paseo starts executor agents from model profiles, and an Opus 5.5 orchestrator plans the work, routes tickets and
merges the result into `dev`.

> [!WARNING]
> `install.sh` installs the **latest** releases of every tool, but the stack was tested only with the versions listed in
> [Tested Versions](#tested-versions). Newer versions were not checked. The installer prints a warning at the start and
> the installed versions at the end, so you can compare them.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Stack](#stack)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Model Routing](#model-routing)
- [How It Works](#how-it-works)
- [Git and Review](#git-and-review)
- [Safety](#safety)
- [Tested Versions](#tested-versions)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Layout](#layout)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Overview

You describe the task in plain words, such as "build feature X", "refactor module Y", "find this bug" or "research how
Z works". The `orchestrate` skill picks the matching Pocock flow: grilling, spec, tickets and implementation. It then
stops and waits for your approval. After you approve, it starts one Paseo agent per ticket, each in its own worktree,
with a model matched to the ticket's difficulty. When the work is done, it reviews the result and merges it into `dev`
with a merge commit.

Each concern has exactly one owner. Pocock owns the process, Paseo owns transport and worktrees, Ponytail owns code
size, CodeGraph owns code navigation and RTK owns output compression. Because of this, two tools never compete for the
same job.

## Features

- 🗣️ **Plain-language entry point**: ask in words. Slash commands still work.
- 🧭 **Pocock process**: `grill-me` → `to-spec` → `to-tickets` → `implement-spec`, with `wayfinder` for huge goals.
- 🚦 **Approval gate**: executors only take tickets labelled `ready-for-agent`, and that label is set only after your
  explicit "yes".
- 🤖 **Model routing**: 12 Paseo profiles map each task type to its model and thinking level.
- 🌳 **Worktree per ticket**: an integration branch per spec, tickets merged into it, then one PR into `dev`.
- 🧠 **CodeGraph in every worktree**: a SessionStart hook copies the index from the main checkout and syncs it.
- ✂️ **Ponytail**: minimal code, plus `/ponytail-review` before every hand-off.
- 📉 **RTK**: condensed command output saves context.
- 🛡️ **Git deny rules**: blocks force push, pushes to `main`, `reset --hard`, `clean -f` and similar commands.
- 🔁 **Idempotent installer**: you can re-run it at any time. It keeps your own `CLAUDE.md` content, other Paseo
  profiles and existing Paseo skills, and backs up configs before changing them.

## Stack

| Tool                                                           | Role                                                                                   |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [Matt Pocock skills](https://github.com/mattpocock/skills)     | Engineering process: spec, tickets, TDD, bug diagnosis, code review, triage            |
| [Paseo](https://paseo.sh)                                      | Transport: worktrees, executor agents from profiles, questions and answers, archiving  |
| [Ponytail](https://github.com/DietrichGebert/ponytail)         | Smallest working code, `/ponytail-review`                                              |
| [CodeGraph](https://github.com/colbymchenry/codegraph)         | Code graph over MCP, auto-indexed in every worktree                                    |
| [RTK](https://github.com/rtk-ai/rtk)                           | Compresses command output (git, tests, builds)                                         |
| [Playwright CLI](https://playwright.dev/agent-cli/installation) | Browser for e2e checks, screenshots and UI. Snapshots go to files, not into context    |

Not used, because they overlap with the tools above: Superpowers, OpenSpec, GSD, Context Mode, codebase-memory-mcp.

## Installation

### Prerequisites

- **git**, **python3**, **node** + **npm**, **[gh](https://cli.github.com)** (authenticated);
- **[Claude Code](https://claude.com/claude-code)**;
- **[Paseo](https://paseo.sh)** with the Claude, Codex and Antigravity providers connected.

### Install

```sh
git clone git@github.com:LeonidAlekseev/paseo-aio.git
cd paseo-aio
./install.sh
paseo daemon restart
claude                      # start a new session so hooks and MCP load
```

Write the configs only, without downloading anything:

```sh
SKIP_INSTALL=1 ./install.sh
```

What the installer does:

1. Installs RTK, CodeGraph, Playwright CLI with Chromium, and the Ponytail and Matt Pocock skills plugins.
2. Copies the `orchestrate` and `pocock-paseo` skills and the CodeGraph auto-index hook into `~/.claude/`.
3. Adds the RTK and CodeGraph hooks, the git deny rules and `PONYTAIL_DEFAULT_MODE=full` to `~/.claude/settings.json`.
   The previous file is backed up to `~/.claude/backups/`.
4. Writes the rules block between the `DEV_STACK` markers in `~/.claude/CLAUDE.md` and leaves the rest of the file as
   is.
5. Adds `.codegraph/` to the global gitignore.
6. Copies Paseo's built-in skills, but only the ones that are missing, because Paseo updates its own.
7. Merges the Paseo settings and profiles into `~/.paseo/config.json` (with a backup) and installs the Paseo plugins
   from `paseo/plugins.txt`.

### Paseo settings applied

| Setting                         | Value                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------- |
| Plugins                         | better-paseo, prompt-manager, resources, shell-yeah, usage-auto-resume       |
| MCP injected into agents        | on                                                                           |
| Browser tools                   | off. The browser is Playwright CLI                                           |
| Auto-archive after merge        | on                                                                           |
| Providers                       | Antigravity on. OpenCode, Pi and Muse off                                    |
| Agent profiles                  | 12, see [Model Routing](#model-routing)                                      |

The daemon address, CORS, relay and keys are never touched.

### Optional settings

These are not applied by the installer. Turn them on by hand if you want them:

- **Theme: Pure Black**. Choose it in the Paseo app settings. The theme is stored by the app, not by the daemon.
- **Dictation with local Whisper**. In the Paseo app settings, enable dictation with the local `whisper-turbo` model.

### Per repository

Tell the orchestrator once: "set up this repo for orchestration". Together with you, it will run
`setup-matt-pocock-skills`, which configures the GitHub issue tracker and the triage labels.

## Quick Start

```text
You:   Add CSV export to the reports page.
Agent: grill-me → spec #41 → tickets #42–#45

       ticket | goal            | difficulty → profile         | blocked by
       #42    | export service  | medium → implementer-medium  | —
       #43    | CSV formatter   | light  → implementer-light   | —
       #44    | button + route  | medium → implementer-medium  | #42 #43
       #45    | e2e test        | light  → implementer-light   | #44

       Approve?
You:   Yes.
Agent: integration/csv-export ← #42 #43 (parallel) → #44 → #45 → code-review → PR #46 → dev
```

## Usage

Ask in plain words. `orchestrate` maps the request to a flow:

| Request                            | Flow                                                                                  |
| ---------------------------------- | ------------------------------------------------------------------------------------- |
| Big feature                        | `grill-me` → `to-spec` → `to-tickets` → **approval** → `implement-spec`               |
| Huge or vague goal                 | `wayfinder` → then as above                                                           |
| Refactoring                        | `improve-codebase-architecture` → tickets → **approval** → `implementer-heavy`        |
| Small change                       | one ticket → **approval** → one executor, PR straight into `dev`                      |
| Bug                                | `diagnosing-bugs` → fix ticket → **approval** → executor                              |
| Review                             | `code-review` + `/ponytail-review`                                                    |
| "How does X work" in the code      | `code-research` profile (Sonnet)                                                      |
| Research that needs the internet   | `web-research` profile (Gemini)                                                       |
| Images or UI assets                | `images` profile (Codex)                                                              |
| Sort out issues                    | `triage`                                                                              |
| Release                            | PR `dev` → `main` after your approval                                                 |

Slash commands (`/to-spec`, `/grill-me`, `/wayfinder` and so on) run exactly as typed.

## Model Routing

| Profile               | Model                          | Thinking | Tasks                                                           |
| --------------------- | ------------------------------ | :------: | --------------------------------------------------------------- |
| `orchestrator`        | Opus 5.5                       |  medium  | Planning, routing, answering executor questions, merging         |
| `implementer-heavy`   | Opus 5.5                       |  medium  | Refactoring, extensive changes, migrations, public API          |
| `implementer-medium`  | Sonnet 5.5                     |  medium  | Typical features and bug fixes, UI code, fixes after review     |
| `implementer-light`   | Haiku 5.5                      |  medium  | Light changes, up to ~3 files                                   |
| `implementer-trivial` | Haiku 5.5                      |   low    | Renames, boilerplate, plain text rewrites                       |
| `merger`              | Haiku 5.5                      |  medium  | Merging tickets into the integration branch                     |
| `reviewer`            | Sonnet 5.5                     |  medium  | Standards and Spec axes of `code-review`                        |
| `code-research`       | Sonnet 5.5                     |  medium  | Researching the codebase                                        |
| `web-research`        | Gemini 3.8 Flash (Antigravity) |   high   | Research that needs the internet                                |
| `images`              | GPT-6-Luna (Codex)             |  medium  | Images, PNG with transparent background                         |
| `advisor`             | GPT-6-Luna (Codex)             |  medium  | Second opinion on architecture (a different model family)       |
| `arbiter`             | Fable 5.1                      |  medium  | Disputed review remarks and unresolved disputes                 |

Only Claude models write code. At most 3 code-writing agents run at the same time.

## How It Works

1. **🗣️ Request**: `orchestrate` classifies it and picks a flow.
2. **🔧 Preparation**: `git fetch`, checks that `dev` exists, and looks for work already in flight (open PRs, Paseo
   agents) to avoid duplicates.
3. **📝 Plan**: Pocock grills you, writes the spec and splits it into tickets with blocking edges, all in GitHub issues.
4. **✋ Approval**: the plan is shown as a table and the orchestrator stops. Approved tickets get `ready-for-agent`.
5. **🌳 Worktrees**: `integration/<spec>` is created from fresh `origin/dev`, plus one `ticket/<N>-<slug>` worktree per
   ticket, created through Paseo. CodeGraph indexes each worktree on start.
6. **🤖 Executors**: one agent per ticket, using the profile that matches its difficulty. Each executor follows `tdd`,
   runs the checks and `/ponytail-review`, merges the integration tip into its branch and reports back. Questions go to
   the orchestrator, which answers or asks you.
7. **🔀 Merge**: a `merger` agent merges each finished ticket into the integration branch. The ticket frontier advances.
8. **🔍 Review**: `code-review` runs two `reviewer` agents (Standards and Spec), then one fix round.
9. **🚀 Integration**: a PR from `integration/<spec>` into `dev` with a merge commit, and the tickets are closed.
10. **🧹 Cleanup**: Paseo archives agents and worktrees, and local branches and notes are removed.

## Git and Review

- **Branches**: `integration/<spec>` from `origin/dev`, `ticket/<N>-<slug>` from the integration branch. No rebase, no
  force push. `main` only changes on release.
- **Issues** are closed right after the merge into `dev`. There is no TODO file and no `in-dev` label.
- **Review pipeline**: tests → `/ponytail-review` by the executor → `code-review` at the end of the spec.
- **Conflict priority**: tests > spec/ticket > Ponytail > advisor/arbiter. One fix round per review. A repeated dispute
  goes to `arbiter`, and you decide if it is still unresolved.

## Safety

- **Approval gate**: nothing is implemented without your explicit approval. Silence is not approval.
- **Git deny rules** in `~/.claude/settings.json` block force push, pushes to `main`, `reset --hard`, `clean -f`,
  `checkout -- .`, `restore .`, deleting `main`/`dev` and `gh repo delete`.
- **Backups**: `settings.json` goes to `~/.claude/backups/`, and `config.json` is copied to
  `~/.paseo/config.json.bak-<time>`.
- **Non-Claude agents** (Gemini, Codex) run without RTK, Ponytail or deny rules, so they never get code-writing tasks.
- **Executors run in `auto` mode**. If the classifier blocks an action, the agent waits for the orchestrator.

> [!TIP]
> Deny rules match the beginning of a command. For real protection, also enable branch protection for `main` and `dev`
> on GitHub.

## Tested Versions

Tested together on 2026-11-01, on Linux:

| Component                   | Version                                                                                                         |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Claude Code                 | 2.1.316                                                                                                         |
| Paseo                       | 0.14.0                                                                                                          |
| Node                        | v26.13.0                                                                                                        |
| RTK                         | 1.1.0                                                                                                           |
| CodeGraph                   | 1.6.2                                                                                                           |
| @playwright/cli             | 0.1.23                                                                                                          |
| ponytail plugin             | 5.3.3                                                                                                           |
| mattpocock-skills plugin    | 1.3.1                                                                                                           |
| Paseo plugins               | better-paseo `f7dcded`, prompt-manager `74d00ca`, resources `e3ecb0b`, shell-yeah 1.3.1, usage-auto-resume `b115098` |

> [!CAUTION]
> Newer versions were not tested. After an update, check that `orchestrate` still finds the Pocock skills by name and
> that the hooks still fire.

## Troubleshooting

#### `/to-spec`, `/implement-spec` and other Pocock skills are missing

The plugin is not installed, or the session was started before it was installed. Run:

```sh
claude plugin install mattpocock-skills@claude-plugins-official
```

Then start a new `claude` session.

#### Plugin installation is blocked by the auto-mode classifier

Run the commands from step 1 of the installer yourself, in a terminal outside the agent session.

#### CodeGraph has no index in a worktree

The index is built in the background on session start. Check the log:

```sh
tail ~/.claude/hooks/codegraph-autoindex.log
```

#### `list_profiles` returns an empty list

Run `paseo daemon restart` and check that `~/.paseo/config.json` contains `daemon.agentProfiles`.

#### A profile fails to start: unknown model

The model IDs depend on what your providers offer. Compare them with `paseo provider models claude` (or `codex`,
`antigravity`) and edit `paseo/agent-profiles.json`.

#### `git push` is denied

A deny rule matched. A force push or a push to `main` is intentional and must be run by you in a terminal.

## FAQ

**Do I have to type slash commands?** No. Ask in words, and `orchestrate` reads the matching Pocock skill, including
the slash-only ones.

**Why one PR per spec instead of one per ticket?** It is Pocock's integration-branch model. Tickets merge into one
branch, and you review the whole feature at once.

**Can I change the models?** Yes. Edit `paseo/agent-profiles.json` and re-run `SKIP_INSTALL=1 ./install.sh`. The
`notes` field tells the orchestrator when to use each profile.

**Will the installer overwrite my CLAUDE.md?** No. It only replaces the block between `<!-- DEV_STACK_START -->` and
`<!-- DEV_STACK_END -->`.

**Does it work on macOS?** Probably, but it was tested only on Linux.

## Layout

```
install.sh                           installer
claude/CLAUDE.dev-stack.md           rules block for ~/.claude/CLAUDE.md
claude/hooks/codegraph-autoindex.sh  SessionStart: CodeGraph index in every worktree
claude/skills/orchestrate/           entry point: plain-language request → Pocock flow
claude/skills/pocock-paseo/          adapter: Pocock roles → Paseo agents by profile
paseo/agent-profiles.json            executor profiles
paseo/settings.json                  portable Paseo settings (no addresses or keys)
paseo/plugins.txt                    Paseo plugins (plugins.paseo.sh registry ids)
paseo/skills/                        snapshot of Paseo's built-in skills
```

## Acknowledgments

- [Matt Pocock skills](https://github.com/mattpocock/skills): the engineering process.
- [Paseo](https://paseo.sh): agent orchestration and worktrees.
- [Ponytail](https://github.com/DietrichGebert/ponytail), [CodeGraph](https://github.com/colbymchenry/codegraph),
  [RTK](https://github.com/rtk-ai/rtk), [Playwright CLI](https://playwright.dev/agent-cli/installation).
- Paseo plugins: [better-paseo](https://github.com/RoundRedDot/better-paseo),
  [prompt-manager](https://github.com/yannelli/paseo-prompt-manager),
  [resources](https://github.com/ZedObaia/paseo-plugins),
  [shell-yeah](https://plugins.paseo.sh), [usage-auto-resume](https://github.com/babo-jeonguk/paseo-usage-auto-resume).

## License

[MIT](LICENSE).

`paseo/skills/` is a snapshot of [Paseo](https://github.com/getpaseo/paseo)'s built-in skills. They are not covered by the
MIT license: they stay under Paseo's Apache License 2.0, see [paseo/skills/LICENSE](paseo/skills/LICENSE).
