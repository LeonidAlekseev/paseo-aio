import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'codex/hooks/codegraph-autoindex.py'


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'worktree with spaces'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def fake_codegraph(self, body):
        binary = self.bin / 'codegraph'
        binary.write_text('#!' + sys.executable + '\n' + body)
        binary.chmod(0o755)

    def run_hook(self, cwd=None):
        return subprocess.run([sys.executable, str(HOOK)], cwd=self.root,
            input=json.dumps({'cwd': str(cwd or self.repo)}), env=self.env,
            capture_output=True, text=True, timeout=10)

    def test_event_cwd_and_repeat_indexing(self):
        self.fake_codegraph("from pathlib import Path\nPath('.codegraph').mkdir(exist_ok=True)\nPath('.codegraph/codegraph.db').touch()\nPath('count').write_text('once')\n")
        first = self.run_hook()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue((self.repo / '.codegraph').is_dir())
        self.assertIn('initialized', first.stdout)
        second = self.run_hook()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, '')
        self.assertEqual((self.repo / 'count').read_text(), 'once')

    def test_non_git_directory_is_ignored(self):
        self.fake_codegraph("raise RuntimeError('must not run')\n")
        result = self.run_hook(self.root)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')

    def test_index_failure_does_not_block_session(self):
        self.fake_codegraph("import sys\nprint('indexer failed', file=sys.stderr)\nsys.exit(1)\n")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertIn('use rg/read', result.stderr)
        self.assertNotIn('initialized', result.stdout)

    def test_empty_index_directory_does_not_suppress_retry(self):
        (self.repo / '.codegraph').mkdir()
        self.fake_codegraph("from pathlib import Path\nPath('.codegraph/codegraph.db').touch()\n")
        result = self.run_hook()
        self.assertIn('initialized', result.stdout)
        self.assertTrue((self.repo / '.codegraph/codegraph.db').is_file())

    def test_simultaneous_hooks_only_start_one_indexer(self):
        self.fake_codegraph("from pathlib import Path\nimport time\nwith open('count', 'a') as f: f.write('run\\n')\ntime.sleep(.3)\nPath('.codegraph').mkdir()\nPath('.codegraph/codegraph.db').touch()\n")
        processes = [subprocess.Popen([sys.executable, str(HOOK)], cwd=self.repo,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=self.env) for _ in range(2)]
        for process in processes:
            _, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, error)
        self.assertEqual((self.repo / 'count').read_text(), 'run\n')


if __name__ == '__main__':
    unittest.main()
