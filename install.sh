#!/usr/bin/env bash
# Installs the agent dev stack: RTK, CodeGraph, Playwright CLI, Ponytail, Matt Pocock skills,
# the orchestrate / pocock-paseo skills, hooks, git deny rules and Paseo agent profiles.
# Idempotent: safe to re-run. SKIP_INSTALL=1 only writes configs (no downloads).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
PASEO_HOME="${PASEO_HOME:-$HOME/.paseo}"
STAMP="$(date +%s)"
say() { printf '\n==> %s\n' "$*"; }

# Tested together on 2026-11-01. The installer pulls the LATEST versions; newer ones were not checked.
TESTED='Claude Code 2.1.316 | Paseo 0.14.0 | Node v26.13.0 | rtk 1.1.0 | codegraph 1.6.2
@playwright/cli 0.1.23 | ponytail plugin 5.3.3 | mattpocock-skills plugin 1.3.1
Paseo plugins: better-paseo f7dcded, prompt-manager 74d00ca, resources e3ecb0b, shell-yeah 1.3.1, usage-auto-resume b115098'
cat <<EOF
WARNING: this stack was tested only with these versions:
$TESTED
The installer installs the latest releases. If versions differ, behaviour was NOT verified:
skills may be renamed (orchestrate reads Pocock skills by name), CLI flags and hook formats may change.
Compare with the versions printed at the end and check the orchestrate / pocock-paseo skills after updates.
EOF

for c in git python3 node npm claude; do
  command -v "$c" >/dev/null || { echo "Missing required command: $c" >&2; exit 1; }
done

if [ "${SKIP_INSTALL:-0}" != 1 ]; then
  say "RTK"
  command -v rtk >/dev/null || curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  rtk init -g || true   # adds @RTK.md to CLAUDE.md; the Bash hook itself is written below

  say "CodeGraph + Playwright CLI"
  npm i -g @colbymchenry/codegraph @playwright/cli@latest
  codegraph install --target=claude --location=global --yes
  playwright-cli install --skills --global
  npx -y playwright install chromium

  say "Claude Code plugins: Ponytail, Matt Pocock skills"
  claude plugin marketplace add DietrichGebert/ponytail || true
  claude plugin install ponytail@ponytail || true
  claude plugin install mattpocock-skills@claude-plugins-official || true
fi

say "Hook, skills, CLAUDE.md"
mkdir -p "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/skills" "$CLAUDE_DIR/backups"
install -m 755 "$HERE/claude/hooks/codegraph-autoindex.sh" "$CLAUDE_DIR/hooks/"
cp -r "$HERE/claude/skills/orchestrate" "$HERE/claude/skills/pocock-paseo" "$CLAUDE_DIR/skills/"
touch "$CLAUDE_DIR/CLAUDE.md"
python3 - "$CLAUDE_DIR/CLAUDE.md" "$HERE/claude/CLAUDE.dev-stack.md" <<'PY'
import re, sys
path, block = sys.argv[1], open(sys.argv[2]).read().strip()
text = open(path).read()
pat = re.compile(r'<!-- DEV_STACK_START -->.*?<!-- DEV_STACK_END -->', re.S)
text = pat.sub(lambda m: block, text) if pat.search(text) else text.rstrip() + '\n\n' + block + '\n'
open(path, 'w').write(text)
PY

say "settings.json: hooks, git deny rules, Ponytail mode"
S="$CLAUDE_DIR/settings.json"
[ -f "$S" ] && cp "$S" "$CLAUDE_DIR/backups/settings.json.$STAMP" || echo '{}' > "$S"
python3 - "$S" <<'PY'
import json, sys
p = sys.argv[1]; s = json.load(open(p))
h = s.setdefault('hooks', {})
def add(event, entry):
    lst = h.setdefault(event, [])
    if entry not in lst: lst.append(entry)
add('PreToolUse', {"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]})
add('SessionStart', {"hooks": [{"type": "command", "command": "~/.claude/hooks/codegraph-autoindex.sh"}]})
deny = s.setdefault('permissions', {}).setdefault('deny', [])
for r in ["Bash(git push --force*)", "Bash(git push -f*)", "Bash(git push * --force*)", "Bash(git push * -f *)",
          "Bash(git push * -f)", "Bash(git push origin main*)", "Bash(git push origin HEAD:main*)", "Bash(git push * +*)",
          "Bash(git reset --hard*)", "Bash(git clean -f*)", "Bash(git clean -d*)", "Bash(git checkout -- .)",
          "Bash(git restore .)", "Bash(git branch -D main)", "Bash(git branch -D dev)", "Bash(gh repo delete*)"]:
    if r not in deny: deny.append(r)
s.setdefault('env', {})['PONYTAIL_DEFAULT_MODE'] = 'full'
json.dump(s, open(p, 'w'), indent=2)
PY

say "Global gitignore: .codegraph/"
IGN="$(git config --global core.excludesfile || true)"
[ -n "$IGN" ] || { IGN="$HOME/.gitignore_global"; git config --global core.excludesfile "$IGN"; }
IGN="${IGN/#\~/$HOME}"; touch "$IGN"
grep -qx '.codegraph/' "$IGN" || printf '\n# CodeGraph index\n.codegraph/\n' >> "$IGN"

say "Paseo built-in skills (only missing ones; Paseo updates its own)"
for d in "$HERE"/paseo/skills/*/; do
  [ -d "$CLAUDE_DIR/skills/$(basename "$d")" ] || cp -r "$d" "$CLAUDE_DIR/skills/"
done

if [ -f "$PASEO_HOME/config.json" ]; then
  say "Paseo settings and agent profiles"
  cp "$PASEO_HOME/config.json" "$PASEO_HOME/config.json.bak-$STAMP"
  python3 - "$PASEO_HOME/config.json" "$HERE/paseo/settings.json" "$HERE/paseo/agent-profiles.json" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p))
def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v
merge(c, json.load(open(sys.argv[2])))
new = json.load(open(sys.argv[3])); ids = {x['id'] for x in new}
d = c.setdefault('daemon', {})
d['agentProfiles'] = [x for x in d.get('agentProfiles', []) if x.get('id') not in ids] + new
json.dump(c, open(p, 'w'), indent=2, ensure_ascii=False)
PY
  if command -v paseo >/dev/null; then
    if [ "${SKIP_INSTALL:-0}" != 1 ]; then
      say "Paseo plugins"
      have="$(paseo plugin ls 2>/dev/null || true)"
      while read -r src; do
        [ -n "$src" ] && ! grep -q "$src" <<<"$have" && { paseo plugin install "$src" || echo "Failed: $src"; }
      done < "$HERE/paseo/plugins.txt"
    fi
    paseo reload >/dev/null 2>&1 || true
  fi
else
  echo "Paseo config not found at $PASEO_HOME/config.json; skipping profiles (install Paseo, then re-run)."
fi

say "Installed versions (compare with the tested ones above)"
for c in "claude --version" "paseo --version" "node --version" "rtk --version" "codegraph --version" "playwright-cli --version"; do
  printf '%-24s %s\n' "${c%% *}" "$($c 2>/dev/null | head -1 || echo missing)"
done
claude plugin list 2>/dev/null | grep -A1 -E 'ponytail@|mattpocock-skills@' | grep -v '^--' || true

say "Done. Restart: 'paseo daemon restart', then start a new 'claude' session."
