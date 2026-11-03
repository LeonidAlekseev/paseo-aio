#!/usr/bin/env python3
"""Best-effort Codex SessionStart indexing; also usable manually in a worktree."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    if not shutil.which('codegraph'):
        return 0
    # Codex supplies cwd in the hook event; standalone calls use process cwd.
    event = {}
    if not sys.stdin.isatty():
        try:
            event = json.load(sys.stdin)
        except (ValueError, OSError):
            pass
    cwd = event.get('cwd', os.getcwd()) if isinstance(event, dict) else os.getcwd()
    try:
        result = subprocess.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            return 0
        root = Path(result.stdout.strip()).resolve()
        if root in (Path('/'), Path.home()) or (root / '.codegraph' / 'codegraph.db').is_file():
            return 0
        # A lock in the worktree's own git directory serializes simultaneous
        # SessionStart hooks without sharing indexes between different branches.
        gitdir = subprocess.run(['git', '-C', str(root), 'rev-parse', '--absolute-git-dir'],
                                check=True, capture_output=True, text=True, timeout=10)
        lock = Path(gitdir.stdout.strip()) / 'paseo-codegraph.lock'
        with lock.open('a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 0
            if (root / '.codegraph' / 'codegraph.db').is_file():
                return 0
            result = subprocess.run(['codegraph', 'init', '--yes'], cwd=root,
                                    capture_output=True, text=True, timeout=240)
            if result.returncode:
                print('CodeGraph index failed; use rg/read. ' + result.stderr[-1500:], file=sys.stderr)
            else:
                print('CodeGraph index initialized for ' + str(root))
    except (OSError, subprocess.SubprocessError) as error:
        print('CodeGraph index unavailable; use rg/read: ' + str(error), file=sys.stderr)
    # Optional indexing must not prevent a coding session from starting.
    return 0


if __name__ == '__main__':
    sys.exit(main())
