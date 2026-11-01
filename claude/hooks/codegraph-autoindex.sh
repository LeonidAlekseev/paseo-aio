#!/usr/bin/env bash
# SessionStart: make sure the current git worktree has a CodeGraph index.
# New Paseo worktree -> copy the index from the main checkout and sync incrementally;
# no index anywhere -> build it from scratch. Runs in the background; never blocks the session.
set -u
command -v codegraph >/dev/null || exit 0
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -d "$root/.codegraph" ] && exit 0
case "$root" in "$HOME"|/) exit 0;; esac

main=$(dirname "$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")
log="$HOME/.claude/hooks/codegraph-autoindex.log"
(
  if [ "$main" != "$root" ] && [ -f "$main/.codegraph/codegraph.db" ]; then
    cp -r "$main/.codegraph" "$root/.codegraph" && codegraph sync "$root" --quiet
    echo "$(date -Is) copied+synced $root from $main"
  else
    codegraph init "$root" --yes >/dev/null 2>&1
    echo "$(date -Is) indexed $root"
  fi
) >>"$log" 2>&1 &
echo "CodeGraph: indexing $root in background; use grep/read until .codegraph/ appears."
exit 0
