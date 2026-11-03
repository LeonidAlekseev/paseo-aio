# Paseo AIO for Codex

[Русский](README.codex.ru.md) · [Original Claude setup](README.md)

Native Codex support for the AIO workflow: Matt Pocock skills define the process,
Paseo manages worktrees and executor agents, and Codex handles every role.
The Claude installer and files remain available independently.

## Install

Prerequisites: Linux, Python 3, Git, Node/npm, curl, a running Paseo daemon and an
authenticated Codex CLI. Remote issue/PR operations require their host's
authenticated CLI; local task tracking does not. Run setup as the same OS user
that runs the daemon's Codex agents.

```bash
git clone https://github.com/LeonidAlekseev/paseo-aio.git
cd paseo-aio
bash install-codex.sh --with-tools --with-browser
```

The default is a **preview**: it verifies the model catalog and lists changes
without installing packages, changing files, launching agents or restarting the
daemon. To apply the same plan:

```bash
bash install-codex.sh --with-tools --with-browser --apply
paseo reload
```

Open Codex CLI as this user, use `/hooks` to review/trust new CodeGraph, RTK and
Ponytail hooks, then create a **new Codex session in Paseo**. The installer does
not manufacture hook trust. If `gh` is missing, install it with your OS package
manager and run `gh auth login` for GitHub workflows.

For config/skill updates without downloading tools:

```bash
bash install-codex.sh --apply
```

To configure already installed binaries and install the Codex plugins without
reinstalling binaries, use `bash install-codex.sh --configure-tools --apply`.
Plugin installation may still access the network. This option cannot be combined
with `--with-tools` or `--with-browser`. For separately provisioning binaries,
`bash codex/install-tools.sh --binaries-only --apply` skips Codex configuration.

## Profiles and skills

The twelve profiles in [codex/agent-profiles.json](codex/agent-profiles.json) use
Codex. Each profile selects a provider with the same ID, extending `codex` and
supplying its role instructions at launch. The installer uses the profile's name
and `notes` as instructions, so selecting a reviewer, implementer or researcher
also selects its behavior. IDs start with `codex-`; the original Claude profiles
and unrelated user profiles remain intact. Older custom profiles using the generic
`codex` provider are migrated to their corresponding role providers.

| Profile suffix | Model | Reasoning | Role |
| --- | --- | --- | --- |
| orchestrator | Astra | high | Plan, delegate, integrate |
| implementer-heavy | Astra | high | Architecture, migrations, large changes |
| implementer-medium | Sol | medium | Features, bugs, UI, review fixes |
| implementer-light | Sol | medium | Small local changes |
| implementer-trivial | Sol | low | Mechanical changes |
| merger | Sol | medium | Sequential integration merges |
| reviewer | Astra | high | Standards / Spec review |
| code-research | Sol | medium | Code exploration |
| web-research | Sol | medium | Documentation with sources |
| images | Sol | medium | Image assets, when an image tool exists |
| advisor | Astra | high | Independent architecture opinion |
| arbiter | Astra | high | Disputed review findings |

Astra means `gpt-6-astra`; Sol means `gpt-6.1-sol`. Astra covers the original
Opus 5.5 roles (orchestrator and heavy implementer), plus review, architecture
advice and arbitration. Model and reasoning settings are checked against the live
Codex catalog or the role's explicitly configured catalog. Edit the JSON to route roles to other
models, or override all roles with `--model MODEL --thinking EFFORT`. There is no
silent substitution when a model or reasoning setting is unavailable. Same-model
review is not cross-family review. An image/web profile does not provide missing
tools: the agent must check their availability.

When absent on a role provider, `models` and `additionalModels` are copied
from `codex`; existing role overrides, including empty lists, are preserved.
If a role's dynamic catalog cannot be verified from the live base catalog
(for example, different environment settings or removal of base model overrides),
installation stops before config writes. Supply an explicit non-empty `models`
list with `thinkingOptions` for that provider in that case. Catalog validation
does not prove that an account can successfully run a model.

Profiles added for the first time default to `auto-review`. Reinstallation
preserves each existing profile's permission mode from `~/.paseo/config.json`,
including when updating profile definitions with `--profiles`. To explicitly
set the mode for all installed Codex profiles:

```bash
bash install-codex.sh --mode full-access --apply
```

This choice survives subsequent installs without `--mode`. These profiles govern
new agents launched with them; they do not set the mode of existing sessions or
agents created without a profile. `full-access` disables the Codex filesystem
sandbox. Read-only role instructions are behavioral constraints, not enforced
read-only sandboxes.

Create a managed agent in Paseo and select **Profiles → Codex · Orchestrator**.
The provider automatically instructs it to use `codex-orchestrate` and
`codex-pocock-paseo` for development tasks. You can type the task directly,
without naming the skills. For initial project setup, start with:

```text
Set up this repository for Paseo orchestration.
Show the tracker, target branch and checks before changing them.
```

Then request a feature. The coordinator uses Pocock skills and
`codex-pocock-paseo` to launch approved tickets through Paseo. Existing scope
approval is preserved. At most three writers and two reviewers/researchers run
concurrently; overlapping tickets and integration merges are sequential.
The project determines its target branch; `dev` is the original AIO convention,
not a branch the installer silently creates. Publishing and releases remain
within the user's authorization.

Role instructions apply when creating a new agent with the selected profile.
Applying model settings to an existing generic Codex agent does not change its
launch provider. The coordinator still supplies each delegated task's scope,
workspace, checks and acceptance criteria.
These are launch defaults. A custom session `systemPrompt` or Paseo
`daemon.appendSystemPrompt` can override them; include the intended role in that
custom instruction and verify it in a new session.

## When remote issues are unavailable

The Codex instructions fall back to local Markdown if issues are disabled,
required access is denied, credentials/CLI are missing, or no tracker is set.
The agent announces the reason, records the local choice in
`docs/agents/issue-tracker.md`, and continues the approved work. It does not
require enabling issues or granting broader access. An explicit local choice
stays local; later availability does not automatically migrate tasks.

```text
.scratch/<feature>/spec.md
.scratch/<feature>/issues/01-<ticket>.md
.scratch/<feature>/issues/02-<ticket>.md
```

Tickets have Status, Blocked by, scope, checks and comments. The coordinator
owns these files in the main checkout and passes accessible references to
worktree agents. Existing remote tickets keep their source links; uncertain
remote writes are reconciled before retrying, to avoid duplicates. Git hosting
and authorized PRs remain independent of the task tracker.

The authoritative [tracker policy](codex/skills/codex-orchestrate/references/issue-tracker.md)
ships with the skill and applies to direct Pocock workflows as well. Its rules
cover status transitions, dependencies, completion and cleanup. This is an
agent workflow, not a background synchronization service.

## Installed files and preservation

- `~/.agents/skills/codex-orchestrate` and `codex-pocock-paseo`.
- Missing built-in Paseo skills, with their Apache license; existing skills stay
  untouched. These are a snapshot; the installed Paseo skill/tool schemas govern.
- A marker-delimited block in `~/.codex/AGENTS.md`; unrelated instructions remain.
  A non-empty `AGENTS.override.md` is reported because it would hide this file.
- A merged `SessionStart` hook in `~/.codex/hooks.json` and the indexer script.
  Existing hook events and handlers stay intact. Indexing is asynchronous,
  per-worktree and locked; failures fall back to rg/read. Indexes are not copied
  between branches. Existing indexes are maintained by CodeGraph's MCP service.
- `~/.codex/rules/paseo-aio.rules`: forbidden prefixes for common destructive Git
  commands, including some RTK forms. Prefix matching is not a general shell
  firewall and is not a replacement for server-side branch protection.
- `~/.paseo/config.json`: owned profiles, `daemon.mcp.injectIntoAgents`, and the
  role providers' base, labels and launch commands. Each command
  reuses the configured Codex binary and adds role-specific `developer_instructions`.
  Connection details, provider toggles, terminal settings, browser settings,
  auto-archive and unrelated profiles remain unchanged.

`CODEX_HOME` and `PASEO_HOME` are honored. Config-only staging also supports
`--codex-home`, `--skills-dir`, `--paseo-home`, `--profiles`. `--offline` is for
preview only; applying requires live model validation.

Changed files are backed up under `~/.codex/backups/paseo-aio/<timestamp>` with a
manifest of original paths. Backups are private. Config file writes are atomic;
a write failure rolls back files already written by that config operation.
Third-party tool installation is separate and is **not transactional**: it may
leave installed packages if a later tool fails. Its config snapshots are under
`~/.codex/backups/paseo-aio-tools`. Errors are not silently ignored.

For rollback, inspect the backup manifest, restore only the files you want, and
reload Paseo. An entry with `backup: null` was newly created. Do not overwrite
subsequent user edits with an old snapshot. Re-running config installation with
the same inputs is a no-op.

## Tools and optional Paseo plugins

`--with-tools` installs CodeGraph 1.6.2, RTK 1.1.0, Playwright CLI 0.1.23 and the
native Matt Pocock/Ponytail Codex plugins from pinned Git revisions. Pins live in
[codex/install-tools.sh](codex/install-tools.sh). RTK's download is checksum-checked.
Ponytail uses a local marketplace under `$CODEX_HOME/marketplaces/paseo-aio-ponytail`
(default `~/.codex/marketplaces/paseo-aio-ponytail`) that pins the plugin source
itself to the Git revision, replacing the upstream marketplace's `main` reference.
An existing upstream Ponytail marketplace registration is replaced automatically;
the plugin keeps its `ponytail@ponytail` identifier.
Playwright skills are installed for **agents**, not its default Claude target.
`--with-browser` downloads the Chromium revision matching the CLI's exact
Playwright dependency and installs OS dependencies; that step may require root
or sudo. Plugin updates outside this installer can change the pinned snapshots.
Browser setup also creates `~/.playwright/cli.config.json` when absent, selecting
the downloaded Chromium for `playwright-cli open`. Existing browser config is
preserved; use `--browser=chromium` if you want to override it for one launch.

The five original Paseo UI/automation plugins are optional. To install them
explicitly on the daemon (they run unsandboxed):

```bash
while IFS= read -r plugin; do
  paseo plugin install "$plugin" || break
done < paseo/plugins.txt
```

These registry versions are not pinned or integration-tested by the Codex port.
The core orchestration does not require them. The installer does not turn on
other model providers or disable Paseo's browser tools.

## Validation

```bash
python3 -m unittest discover -s tests -v
bash -n install-codex.sh codex/install-tools.sh
codex execpolicy check --rules codex/paseo-aio.rules -- git reset --hard HEAD
bash install-codex.sh
```

Unit tests cover preservation, repeat installs, backup/rollback, model rejection,
dry-run behavior and hook concurrency/failure. They do not prove a complete
multi-agent feature/PR cycle. Before deploying, verify in a disposable project:
skills discovery, trusted hooks, injected Paseo MCP, one child agent/worktree,
CodeGraph indexing, actual project checks and a returned review. Do not test
merges or pushes on production branches.

Plain CI runs shell syntax checks and fixture tests without downloading packages
or requiring a daemon. The optional RTK test uses the installed CLI's `--dry-run`
when available. Live preview, Paseo configuration schema and Codex launch argument
checks require installed tools; a preview never applies configuration. Package
installation, hook trust and a full delegation cycle need separate validation in
a disposable setup.

Official references: [Codex skills](https://learn.chatgpt.com/docs/build-skills),
[hooks](https://learn.chatgpt.com/docs/hooks),
[rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
[Paseo configuration](https://paseo.sh/docs/configuration).
