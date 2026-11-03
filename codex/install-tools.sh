#!/usr/bin/env bash
# Pinned tools for Codex. Binary installation and user configuration can run
# separately. No daemon restart or agent launch.
set -euo pipefail
APPLY=0
BROWSER=0
BINARIES_ONLY=0
CONFIGURE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --browser) BROWSER=1 ;;
    --binaries-only) BINARIES_ONLY=1 ;;
    --configure-only) CONFIGURE_ONLY=1 ;;
    *) echo "Usage: $0 [--apply] [--browser] [--binaries-only | --configure-only]" >&2; exit 2 ;;
  esac
done
if [ "$CONFIGURE_ONLY" = 1 ] && { [ "$BINARIES_ONLY" = 1 ] || [ "$BROWSER" = 1 ]; }; then
  echo '--configure-only cannot be combined with --binaries-only or --browser' >&2
  exit 2
fi

CODEGRAPH_VERSION=1.6.2
PLAYWRIGHT_CLI_VERSION=0.1.23
# Must match the playwright dependency of @playwright/cli above; a stable
# Playwright release may download a different Chromium revision.
PLAYWRIGHT_VERSION=1.65.0-alpha-2026-10-30
RTK_VERSION=v1.1.0
RTK_REF=753a3b0e939f2e4490fc24e3a1984010f40a103c
POCOCK_REF=4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
PONYTAIL_REF=96608e078b2d5ea607c5c3b8b5a54d1c1fba6846

echo "RTK $RTK_VERSION; CodeGraph $CODEGRAPH_VERSION; Playwright CLI $PLAYWRIGHT_CLI_VERSION; browser=$BROWSER"
echo "Pocock $POCOCK_REF; Ponytail $PONYTAIL_REF; binaries-only=$BINARIES_ONLY"
echo "configure-only=$CONFIGURE_ONLY (plugins may still require network access)"
if [ "$APPLY" != 1 ]; then
  echo 'Preview only. Add --apply to install. Requires git, curl, python3, node/npm and Codex (runtime setup).'
  exit 0
fi
for command in git curl python3 node npm; do
  command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 1; }
done
if [ "$CONFIGURE_ONLY" = 1 ]; then
  for command in codegraph rtk playwright-cli; do
    command -v "$command" >/dev/null || { echo "Missing installed tool: $command" >&2; exit 1; }
  done
fi
if [ "$BINARIES_ONLY" != 1 ]; then
  command -v codex >/dev/null || { echo 'Missing: codex' >&2; exit 1; }
  codex plugin add --help >/dev/null
  # Preserve local config before third-party setup. This does not roll back
  # installed packages or marketplace caches; failures are surfaced as failures.
  stack_codex_dir="${CODEX_HOME:-$HOME/.codex}"
  stack_backup="$stack_codex_dir/backups/paseo-aio-tools/$(date -u +%Y%m%dT%H%M%S)-$$"
  mkdir -p "$stack_backup"
  chmod 700 "$stack_backup"
  for file in config.toml hooks.json AGENTS.md; do
    if [ -f "$stack_codex_dir/$file" ]; then
      cp -p "$stack_codex_dir/$file" "$stack_backup/$file"
      chmod 600 "$stack_backup/$file"
    fi
  done
  echo "Config backup: $stack_backup"
fi

stack_tmp="$(mktemp -d)"
trap 'rm -rf "$stack_tmp"' EXIT
if [ "$CONFIGURE_ONLY" != 1 ]; then
  npm install -g "@colbymchenry/codegraph@$CODEGRAPH_VERSION" "@playwright/cli@$PLAYWRIGHT_CLI_VERSION"
  curl -fsSL "https://raw.githubusercontent.com/rtk-ai/rtk/$RTK_REF/install.sh" -o "$stack_tmp/rtk-install.sh"
  RTK_VERSION="$RTK_VERSION" RTK_INSTALL_DIR="$(npm prefix -g)/bin" sh "$stack_tmp/rtk-install.sh"
fi

if [ "$BROWSER" = 1 ]; then
  npx --yes "playwright@$PLAYWRIGHT_VERSION" install --with-deps chromium
  # The CLI otherwise looks for Google Chrome, not the downloaded Chromium.
  if [ ! -e "$HOME/.playwright/cli.config.json" ]; then
    mkdir -p "$HOME/.playwright"
    (umask 077; set -o noclobber; printf '%s\n' '{"browser":{"browserName":"chromium"}}' > "$HOME/.playwright/cli.config.json")
  fi
fi
if [ "$BINARIES_ONLY" != 1 ]; then
  codegraph install --target=codex --location=global --yes
  # RTK 1.1.0 rejects --auto-patch in Codex mode.
  # Codex setup is already non-interactive; no extra patch flags are needed.
  rtk init -g --codex
  codex plugin marketplace add mattpocock/skills --ref "$POCOCK_REF"
  codex plugin add mattpocock-skills@mattpocock
  # Upstream's pinned marketplace still points the plugin payload at main.
  stack_ponytail_marketplace="$stack_codex_dir/marketplaces/paseo-aio-ponytail"
  mkdir -p "$stack_ponytail_marketplace/.agents/plugins"
  cat > "$stack_tmp/marketplace.json" <<EOF
{
  "name": "ponytail",
  "plugins": [{
    "name": "ponytail",
    "source": {
      "source": "url",
      "url": "https://github.com/DietrichGebert/ponytail.git",
      "ref": "$PONYTAIL_REF"
    },
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
  }]
}
EOF
  mv "$stack_tmp/marketplace.json" "$stack_ponytail_marketplace/.agents/plugins/marketplace.json"
  codex plugin marketplace list --json > "$stack_tmp/marketplaces.json"
  stack_replace_ponytail="$(python3 - "$stack_tmp/marketplaces.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    marketplaces = json.load(stream)['marketplaces']
upstream = {'sourceType': 'git', 'source': 'https://github.com/DietrichGebert/ponytail.git'}
print(any(m['name'] == 'ponytail' and m.get('marketplaceSource') == upstream for m in marketplaces))
PY
)"
  if [ "$stack_replace_ponytail" = True ]; then
    codex plugin marketplace remove ponytail
  fi
  codex plugin marketplace add "$stack_ponytail_marketplace"
  codex plugin add ponytail@ponytail
  playwright-cli install --skills=agents --global
  echo 'Review installed hooks with /hooks in Codex, then open a new session.'
fi
rtk --version
codegraph --version
playwright-cli --version
echo 'Tool installation finished. No daemon restart was performed.'
