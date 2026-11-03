"""Exercise tool setup with package downloads replaced by local command stubs."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'codex/install-tools.sh'


class ToolInstallTests(unittest.TestCase):
    def test_ponytail_payload_uses_pinned_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            binaries = home / 'bin'
            binaries.mkdir()
            for name in ('git', 'curl', 'node', 'npm', 'sh', 'rtk',
                         'codegraph', 'playwright-cli'):
                stub = binaries / name
                stub.write_text('#!/bin/sh\n'
                                'if [ "$FORBID_DOWNLOADS" = 1 ]; then\n'
                                '  case "${0##*/}" in npm|curl|sh) exit 77 ;; esac\n'
                                'fi\nexit 0\n')
                stub.chmod(0o755)
            codex_home = home / 'custom codex home'
            codex_home.mkdir()
            config = codex_home / 'config.toml'
            config.write_text('# user config\n')
            stub = binaries / 'codex'
            stub.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
home = Path(os.environ['CODEX_HOME'])
registration = home / 'registration.json'
if args == ['plugin', 'marketplace', 'list', '--json']:
    print(json.dumps({'marketplaces': [json.loads(registration.read_text())]
                      if registration.exists() else []}))
elif args == ['plugin', 'marketplace', 'remove', 'ponytail']:
    registration.unlink()
elif args[:3] == ['plugin', 'marketplace', 'add']:
    if args[3] == 'DietrichGebert/ponytail':
        # The upstream marketplace at PONYTAIL_REF points its payload at main.
        data = {'plugins': [{'name': 'ponytail', 'source': {'ref': 'main'}}]}
        source = {'sourceType': 'git', 'source': 'https://github.com/DietrichGebert/ponytail.git'}
    elif Path(args[3]).is_dir():
        data = json.loads((Path(args[3]) / '.agents/plugins/marketplace.json').read_text())
        source = {'sourceType': 'local', 'source': args[3]}
        (home / 'marketplace-path').write_text(args[3])
    else:
        sys.exit(0)
    if registration.exists():
        assert json.loads(registration.read_text())['marketplaceSource'] == source, 'Source conflict'
    registration.write_text(json.dumps({'name': 'ponytail', 'marketplaceSource': source}))
    (home / 'registered-marketplace.json').write_text(json.dumps(data))
elif args == ['plugin', 'add', 'ponytail@ponytail']:
    data = json.loads((home / 'registered-marketplace.json').read_text())
    plugin = next(p for p in data['plugins'] if p['name'] == 'ponytail')
    (home / 'installed-source.json').write_text(json.dumps(plugin['source']))
''')
            stub.chmod(0o755)
            env = dict(os.environ, HOME=folder, CODEX_HOME=str(codex_home),
                       PATH=str(binaries) + os.pathsep + os.environ['PATH'])
            command = ['bash', str(SCRIPT)]
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(list(codex_home.iterdir()), [config], 'Preview must not write')
            pin = next(line.split('=', 1)[1] for line in SCRIPT.read_text().splitlines()
                       if line.startswith('PONYTAIL_REF='))
            for migrate in (False, False, True, False):
                if migrate:
                    subprocess.run(['codex', 'plugin', 'marketplace', 'remove', 'ponytail'],
                                   env=env, check=True, capture_output=True)
                    subprocess.run(['codex', 'plugin', 'marketplace', 'add',
                                    'DietrichGebert/ponytail', '--ref', pin],
                                   env=env, check=True, capture_output=True)
                result = subprocess.run(command + ['--apply'], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                source = json.loads((codex_home / 'installed-source.json').read_text())
                self.assertEqual(source['ref'], pin)
                self.assertEqual(source['url'], 'https://github.com/DietrichGebert/ponytail.git')
                marketplace = Path((codex_home / 'marketplace-path').read_text())
                self.assertTrue((marketplace / '.agents/plugins/marketplace.json').is_file(),
                                'Registered marketplace must survive temporary cleanup')
                self.assertEqual(config.read_text(), '# user config\n')
            # Configuration must succeed without invoking any binary downloader.
            result = subprocess.run(command + ['--configure-only', '--apply'],
                                    env=dict(env, FORBID_DOWNLOADS='1'),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((codex_home / 'installed-source.json').read_text())['ref'], pin)

    def test_configure_only_rejects_binary_install_flags(self):
        for flag in ('--browser', '--binaries-only'):
            result = subprocess.run(['bash', str(SCRIPT), '--configure-only', flag],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('cannot be combined', result.stderr)

    def test_browser_install_sets_default_and_preserves_existing_config(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            binaries = home / 'bin'
            binaries.mkdir()
            for name in ('git', 'curl', 'node', 'npm', 'sh', 'npx', 'rtk',
                         'codegraph', 'playwright-cli'):
                stub = binaries / name
                stub.write_text('#!/bin/sh\nexit 0\n')
                stub.chmod(0o755)
            env = dict(os.environ, HOME=folder, PATH=str(binaries) + os.pathsep + os.environ['PATH'])
            command = ['bash', str(SCRIPT), '--binaries-only', '--browser']
            config = home / '.playwright/cli.config.json'
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertFalse(config.exists(), 'Preview must not create browser config')
            subprocess.run(command + ['--apply'], env=env, check=True, capture_output=True)
            self.assertEqual(json.loads(config.read_text())['browser']['browserName'], 'chromium')
            custom = '{"browser":{"browserName":"firefox"},"userSetting":true}\n'
            config.write_text(custom)
            subprocess.run(command + ['--apply'], env=env, check=True, capture_output=True)
            self.assertEqual(config.read_text(), custom)


if __name__ == '__main__':
    unittest.main()
