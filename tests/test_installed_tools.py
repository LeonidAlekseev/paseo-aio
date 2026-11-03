"""Optional contract checks against real installed CLIs, without config writes."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "codex/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstalledToolTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('paseo'), 'Paseo is not installed')
    def test_generated_profiles_and_providers_pass_paseo_schema(self):
        config = installer.merge_paseo({'version': 1}, installer.profiles())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            before = json.dumps(config)
            path.write_text(before)
            result = subprocess.run(['paseo', 'daemon', 'config', 'get', '--home', folder],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            parsed = json.loads(result.stdout)['value']
            self.assertEqual(parsed['agents']['providers'], config['agents']['providers'])
            self.assertEqual(parsed['daemon']['agentProfiles'], config['daemon']['agentProfiles'])
            self.assertEqual(path.read_text(), before)

    @unittest.skipUnless(shutil.which('codex'), 'Codex is not installed')
    def test_role_launch_arguments_are_accepted_by_codex(self):
        config = installer.merge_paseo({}, installer.profiles())
        with tempfile.TemporaryDirectory() as folder:
            for provider, role in config['agents']['providers'].items():
                with self.subTest(provider=provider):
                    result = subprocess.run(role['command'] + ['features', 'list'],
                                            cwd=folder, env=dict(os.environ, CODEX_HOME=folder),
                                            capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('rtk'), 'RTK is not installed')
    def test_installer_rtk_arguments_are_accepted(self):
        script = Path(__file__).resolve().parents[1] / 'codex/install-tools.sh'
        commands = [shlex.split(line.strip()) for line in script.read_text().splitlines()
                    if line.strip().startswith('rtk init ')]
        self.assertEqual(len(commands), 1)
        # Exercise the installer's actual arguments. RTK --help lists flags
        # that are individually valid but incompatible with --codex.
        result = subprocess.run(commands[0] + ['--dry-run'], capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Nothing written', result.stdout)


if __name__ == '__main__':
    unittest.main()
