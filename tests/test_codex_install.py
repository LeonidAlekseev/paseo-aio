import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'codex' / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.codex = self.root / 'codex home'
        self.skills = self.root / 'skills'
        self.paseo = self.root / 'paseo'
        self.codex.mkdir()
        self.paseo.mkdir()
        self.original = {'version': 1, 'daemon': {
            'listen': '127.0.0.1:6767', 'relay': {'enabled': True},
            'cors': {'allowedOrigins': ['https://example.test']},
            'agentProfiles': [{'id': 'my-personal-profile', 'provider': 'codex'}]},
            'agents': {'providers': {'claude': {'enabled': False}}}}
        self.config = self.paseo / 'config.json'
        self.config.write_text(json.dumps(self.original))
        (self.codex / 'AGENTS.md').write_text('My existing instructions.\n')
        (self.codex / 'hooks.json').write_text(json.dumps({'hooks': {
            'Stop': [{'hooks': [{'type': 'command', 'command': 'my-existing-hook'}]}]}}))

    def plan(self):
        return installer.build_plan(self.codex, self.skills, self.paseo, installer.profiles())

    def apply(self, plan):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.apply_plan(plan, self.codex / 'backups')

    def test_apply_preserves_config_instructions_hooks_and_existing_skills(self):
        existing = self.skills / 'paseo' / 'SKILL.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('A newer Paseo skill')
        self.apply(self.plan())
        result = json.loads(self.config.read_text())
        for name, settings in self.original['agents']['providers'].items():
            self.assertEqual(result['agents']['providers'][name], settings)
        for key in ('listen', 'relay', 'cors'):
            self.assertEqual(result['daemon'][key], self.original['daemon'][key])
        self.assertEqual(result['daemon']['agentProfiles'][0], self.original['daemon']['agentProfiles'][0])
        self.assertEqual(len(result['daemon']['agentProfiles']), 13)
        self.assertTrue(result['daemon']['mcp']['injectIntoAgents'])
        self.assertTrue((self.codex / 'AGENTS.md').read_text().startswith('My existing instructions.'))
        hooks = json.loads((self.codex / 'hooks.json').read_text())['hooks']
        self.assertEqual(hooks['Stop'][0]['hooks'][0]['command'], 'my-existing-hook')
        self.assertEqual(len(hooks['SessionStart']), 1)
        self.assertEqual(existing.read_text(), 'A newer Paseo skill')

    def test_orchestrator_provider_preserves_base_command_and_other_settings(self):
        providers = self.original['agents']['providers']
        providers['codex'] = {'command': ['/opt/custom-codex', '--config', 'existing=true'],
                              'env': {'KEEP': 'value'}}
        providers['codex-orchestrator'] = {'env': {'ROLE_SETTING': 'keep'}}
        self.original['agents']['idleRuntimeCleanup'] = {'enabled': False}
        self.config.write_text(json.dumps(self.original))
        self.apply(self.plan())
        agents = json.loads(self.config.read_text())['agents']
        self.assertEqual(agents['providers']['codex'], providers['codex'])
        self.assertEqual(agents['idleRuntimeCleanup'], {'enabled': False})
        role = agents['providers']['codex-orchestrator']
        self.assertEqual(role['extends'], 'codex')
        self.assertEqual(role['env'], {'ROLE_SETTING': 'keep'})
        self.assertEqual(role['command'][:-2], providers['codex']['command'])
        self.assertEqual(role['command'][-2], '-c')
        key, value = role['command'][-1].split('=', 1)
        self.assertEqual(key, 'developer_instructions')
        self.assertIn('codex-orchestrate', json.loads(value))
        self.assertIn('codex-pocock-paseo', json.loads(value))
        profile = next(p for p in installer.profiles() if p['id'] == 'codex-orchestrator')
        self.assertEqual(profile['provider'], 'codex-orchestrator')

    def test_every_role_receives_launch_instructions_and_preserves_settings(self):
        profiles = installer.profiles()
        profiles[-1]['name'] = 'Arbiter ⚖️ 🧑'
        profiles[-1]['notes'] = 'Check \"quotes\" and newlines.\nReturn evidence.'
        base = {'command': ['/opt/codex', '-c', 'existing=true'],
                'env': {'KEEP': 'base'},
                'models': [{'id': 'custom', 'thinkingOptions': [{'id': 'high'}]}]}
        self.original['agents']['providers']['codex'] = base
        for profile in profiles:
            self.original['agents']['providers'][profile['provider']] = {
                'env': {'ROLE_SETTING': 'keep'}, 'enabled': False}
        merged = installer.merge_paseo(self.original, profiles)
        self.assertEqual(merged['agents']['providers']['codex'], base)
        for profile in profiles:
            with self.subTest(role=profile['id']):
                role = merged['agents']['providers'][profile['provider']]
                self.assertEqual(profile['provider'], profile['id'])
                self.assertEqual(role['extends'], 'codex')
                self.assertEqual(role['env'], {'ROLE_SETTING': 'keep'})
                self.assertFalse(role['enabled'])
                self.assertEqual(role['models'], base['models'])
                self.assertEqual(role['command'][:-2], base['command'])
                # Codex parses -c values as TOML, not JSON.
                instructions = tomllib.loads(role['command'][-1])['developer_instructions']
                self.assertIn(profile['name'], instructions)
                self.assertIn(profile['notes'], instructions)
                if profile['id'] != 'codex-orchestrator':
                    self.assertIn('Do not delegate', instructions)
                self.assertNotIn('command', self.original['agents']['providers'][profile['provider']])

    def test_legacy_custom_profiles_migrate_to_role_providers(self):
        profiles = installer.profiles()
        for profile in profiles:
            profile['provider'] = 'codex'
        profiles[-1]['notes'] = 'Custom arbitration instructions'
        source = self.root / 'profiles.json'
        source.write_text(json.dumps(profiles))
        migrated = installer.profiles(source=source)
        self.assertTrue(all(p['provider'] == p['id'] for p in migrated))
        merged = installer.merge_paseo(self.original, migrated)
        self.assertIn('Custom arbitration instructions',
                      merged['agents']['providers']['codex-arbiter']['command'][-1])
        profiles[-1]['provider'] = 'claude'
        source.write_text(json.dumps(profiles))
        with self.assertRaisesRegex(ValueError, 'provider must be'):
            installer.profiles(source=source)

    def test_model_validation_checks_each_derived_catalog(self):
        profiles = installer.profiles()
        catalog = [{'id': p['model'], 'thinkingOptionIds': ['low', 'medium', 'high']}
                   for p in profiles]
        response = subprocess.CompletedProcess([], 0, json.dumps(catalog), '')
        with patch.object(installer.subprocess, 'run', return_value=response):
            for profile in profiles:
                with self.subTest(role=profile['id']):
                    merged = installer.merge_paseo(self.original, profiles)
                    merged['agents']['providers'][profile['provider']]['models'] = [{'id': 'unavailable'}]
                    with self.assertRaisesRegex(ValueError, 'not available for ' + profile['provider']):
                        installer.validate_models(profiles, self.paseo, merged)

    def test_second_install_is_a_noop(self):
        self.apply(self.plan())
        snapshot = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.apply(self.plan())
        self.assertEqual(snapshot, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cli_reinstall_preserves_modes_and_explicit_mode_overrides(self):
        args = ['install.py', '--apply', '--codex-home', str(self.codex),
                '--skills-dir', str(self.skills), '--paseo-home', str(self.paseo)]
        for flags, expected in [(['--mode', 'full-access'], 'full-access'),
                                ([], 'full-access'),
                                (['--mode', 'auto-review'], 'auto-review')]:
            with self.subTest(flags=flags, expected=expected):
                output = io.StringIO()
                with patch.object(sys, 'argv', args + flags), \
                        patch.object(installer, 'validate_models'), \
                        contextlib.redirect_stdout(output):
                    self.assertEqual(installer.main(), 0)
                items = json.loads(self.config.read_text())['daemon']['agentProfiles'][1:]
                self.assertTrue(all(p['modeId'] == expected for p in items))
                self.assertIn(f'codex-orchestrator: gpt-6-astra / high / {expected}',
                              output.getvalue())

    def test_preview_preserves_each_mode_and_defaults_only_new_profiles(self):
        existing = installer.profiles(mode='full-access')[:-1]
        existing[0]['modeId'] = 'auto'
        self.original['daemon']['agentProfiles'] += existing
        self.config.write_text(json.dumps(self.original))
        before = self.config.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / 'codex/install.py'),
            '--offline', '--codex-home', str(self.codex), '--skills-dir', str(self.skills),
            '--paseo-home', str(self.paseo)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('codex-orchestrator: gpt-6-astra / high / auto\n', result.stdout)
        self.assertIn('codex-implementer-heavy: gpt-6-astra / high / full-access', result.stdout)
        self.assertIn('codex-arbiter: gpt-6-astra / high / auto-review', result.stdout)
        self.assertEqual(self.config.read_bytes(), before)

    def test_nested_skill_reference_is_installed_and_updated(self):
        relative = Path('codex-orchestrate/references/issue-tracker.md')
        target = self.skills / relative
        target.parent.mkdir(parents=True)
        target.write_text('Old tracker policy')
        unrelated = target.parent / 'user-notes.md'
        unrelated.write_text('Keep my notes')
        self.apply(self.plan())
        self.assertEqual(target.read_bytes(), (ROOT / 'codex/skills' / relative).read_bytes())
        self.assertEqual(unrelated.read_text(), 'Keep my notes')

    def test_changed_profiles_replace_only_owned_ids(self):
        self.apply(self.plan())
        changed = installer.profiles(model='another-model', mode='full-access')
        self.apply(installer.build_plan(self.codex, self.skills, self.paseo, changed, mode='full-access'))
        items = json.loads(self.config.read_text())['daemon']['agentProfiles']
        self.assertEqual(len(items), 13)
        self.assertEqual(items[0], self.original['daemon']['agentProfiles'][0])
        self.assertTrue(all(p['model'] == 'another-model' for p in items[1:]))
        self.assertTrue(all(p['modeId'] == 'full-access' for p in items[1:]))

    def test_invalid_saved_mode_requires_explicit_override(self):
        existing = installer.profiles()
        existing[0]['modeId'] = 'unknown-mode'
        self.original['daemon']['agentProfiles'] += existing
        self.config.write_text(json.dumps(self.original))
        with self.assertRaisesRegex(ValueError, 'unsupported saved mode'):
            self.plan()
        self.apply(installer.build_plan(self.codex, self.skills, self.paseo,
                                        installer.profiles(), mode='auto-review'))
        items = json.loads(self.config.read_text())['daemon']['agentProfiles'][1:]
        self.assertTrue(all(p['modeId'] == 'auto-review' for p in items))

    def test_backup_captures_original_bytes(self):
        original = self.config.read_bytes()
        self.apply(self.plan())
        manifest = next((self.codex / 'backups').glob('*/manifest.json'))
        entry = next(e for e in json.loads(manifest.read_text()) if e['path'] == str(self.config))
        self.assertEqual(Path(entry['backup']).read_bytes(), original)
        self.assertEqual(manifest.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(Path(entry['backup']).stat().st_mode & 0o777, 0o600)

    def test_write_failure_rolls_back_written_files(self):
        first, second = self.root / 'first', self.root / 'second'
        first.write_text('original')
        actual = installer.atomic_write
        def fail_second(path, data, mode):
            if path == second:
                raise OSError('simulated disk error')
            actual(path, data, mode)
        with patch.object(installer, 'atomic_write', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.apply({first: b'changed', second: b'new'})
        self.assertEqual(first.read_text(), 'original')
        self.assertFalse(second.exists())

    def test_failed_builtin_install_can_retry(self):
        existing = self.skills / 'user-skill'
        existing.mkdir(parents=True)
        content = existing / 'notes'
        content.write_text('keep')
        empty = self.skills / 'empty-user-dir'
        empty.mkdir()
        target = self.skills / 'paseo' / 'LICENSE'
        actual = installer.atomic_write

        def fail_license(path, data, mode):
            if path == target:
                raise OSError('simulated disk error')
            actual(path, data, mode)

        with patch.object(installer, 'atomic_write', side_effect=fail_license):
            with self.assertRaises(OSError):
                self.apply(self.plan())
        self.assertFalse(target.parent.exists())
        self.assertTrue(empty.is_dir())
        self.assertEqual(content.read_text(), 'keep')
        self.apply(self.plan())
        self.assertTrue((target.parent / 'SKILL.md').is_file())
        self.assertTrue(target.is_file())

    def test_malformed_markers_fail_before_changes(self):
        (self.codex / 'AGENTS.md').write_text(installer.START)
        before = self.config.read_bytes()
        with self.assertRaises(ValueError):
            self.plan()
        self.assertEqual(self.config.read_bytes(), before)

    def test_override_is_reported_instead_of_installing_ignored_instructions(self):
        (self.codex / 'AGENTS.override.md').write_text('override')
        with self.assertRaisesRegex(ValueError, 'shadows'):
            self.plan()

    def test_symlink_is_not_replaced(self):
        target = self.root / 'target'
        target.write_text('keep')
        link = self.root / 'link'
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.apply({link: b'new'})
        self.assertEqual(target.read_text(), 'keep')

    def test_invalid_hooks_are_rejected(self):
        for value in ([], {'hooks': []}, {'hooks': {'SessionStart': {}}}):
            (self.codex / 'hooks.json').write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                self.plan()

    def test_model_validation_checks_every_profile(self):
        profiles = installer.profiles()
        response = subprocess.CompletedProcess([], 0, json.dumps([
            {'id': 'gpt-6-astra', 'thinkingOptionIds': ['low', 'medium', 'high'],
             'thinkingOptions': 'low, medium, high'},
            {'id': 'gpt-6.1-sol', 'thinkingOptionIds': ['low', 'medium', 'high'],
             'thinkingOptions': 'low, medium, high'}]), '')
        with patch.object(installer.subprocess, 'run', return_value=response):
            installer.validate_models(profiles, self.paseo, installer.merge_paseo(self.original, profiles))
            profiles[-1]['model'] = 'not-available'
            with self.assertRaisesRegex(ValueError, 'not available'):
                installer.validate_models(profiles, self.paseo, installer.merge_paseo(self.original, profiles))

    def test_orchestrator_copies_base_catalog_without_replacing_role_overrides(self):
        base = {'models': [{'id': 'custom', 'thinkingOptions': [{'id': 'high'}]}],
                'additionalModels': [{'id': 'extra', 'thinkingOptions': [{'id': 'low'}]}]}
        self.original['agents']['providers']['codex'] = base
        for override in ({}, {'models': [], 'additionalModels': []},
                         {'models': [{'id': 'role-only'}]}):
            with self.subTest(override=override):
                self.original['agents']['providers']['codex-orchestrator'] = override
                result = installer.merge_paseo(self.original, installer.profiles())
                role = result['agents']['providers']['codex-orchestrator']
                for key in ('models', 'additionalModels'):
                    self.assertEqual(role[key], override.get(key, base[key]))
                self.assertEqual(self.original['agents']['providers']['codex-orchestrator'], override)

    def test_model_validation_uses_planned_role_catalog(self):
        profiles = installer.profiles()
        coordinator = next(p for p in profiles if p['provider'] == 'codex-orchestrator')
        runtime = [{'id': 'gpt-6-astra', 'thinkingOptionIds': ['high']}]
        custom = {'id': 'custom', 'thinkingOptions': [{'id': 'high'}]}
        cases = [
            ({'models': [custom]}, {}, 'custom', None),
            ({}, {'models': [custom]}, 'custom', None),
            ({}, {'models': [custom]}, 'gpt-6-astra', 'not available'),
            ({}, {'models': [custom], 'additionalModels': [{'id': 'custom', 'label': 'Renamed'}]}, 'custom', None),
            ({}, {'models': [custom], 'additionalModels': [{'id': 'custom', 'thinkingOptions': []}]}, 'custom', 'Thinking'),
            ({}, {'additionalModels': [custom]}, 'custom', None),
            ({'models': [custom]}, {'models': []}, 'gpt-6-astra', 'Cannot validate'),
            ({}, {'env': {'OPENAI_BASE_URL': 'https://example.test'}}, 'gpt-6-astra', 'Cannot validate'),
        ]
        for base, role, selected, error in cases:
            with self.subTest(base=base, role=role, selected=selected):
                self.original['agents']['providers'].update(codex=base)
                self.original['agents']['providers']['codex-orchestrator'] = role
                coordinator['model'] = selected
                planned = installer.merge_paseo(self.original, profiles)
                live = ([{'id': 'custom', 'thinkingOptionIds': ['high']}]
                        if base.get('models') else runtime)
                response = subprocess.CompletedProcess([], 0, json.dumps(live), '')
                with patch.object(installer.subprocess, 'run', return_value=response):
                    if error:
                        with self.assertRaisesRegex(ValueError, error):
                            installer.validate_models([coordinator], self.paseo, planned)
                    else:
                        installer.validate_models([coordinator], self.paseo, planned)

    def test_tool_changes_are_revalidated_before_config_apply(self):
        before = (self.codex / 'AGENTS.md').read_bytes()
        catalog = [{'id': 'gpt-6-astra', 'thinkingOptionIds': ['high']},
                   {'id': 'gpt-6.1-sol', 'thinkingOptionIds': ['low', 'medium']}]
        def run(command, **kwargs):
            if command[0] == 'bash':
                config = json.loads(self.config.read_text())
                config['agents']['providers']['codex-orchestrator'] = {
                    'models': [{'id': 'other-model', 'thinkingOptions': [{'id': 'high'}]}]}
                self.config.write_text(json.dumps(config))
                return subprocess.CompletedProcess(command, 0)
            return subprocess.CompletedProcess(command, 0, json.dumps(catalog), '')
        with patch.dict(os.environ, {'CODEX_HOME': str(self.codex),
                                     'PASEO_HOME': str(self.paseo), 'HOME': str(self.root)}), \
                patch.object(sys, 'argv', ['install.py', '--with-tools', '--apply']), \
                patch.object(installer.subprocess, 'run', side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(installer.main(), 1)
        self.assertIn('not available for codex-orchestrator', errors.getvalue())
        self.assertEqual((self.codex / 'AGENTS.md').read_bytes(), before)
        self.assertFalse((self.codex / 'rules').exists())

    def test_configure_tools_preview_and_apply(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.dict(os.environ, {'CODEX_HOME': str(self.codex),
                                     'PASEO_HOME': str(self.paseo), 'HOME': str(self.root)}), \
                patch.object(installer, 'validate_models') as validate, \
                patch.object(installer.subprocess, 'run') as run, \
                contextlib.redirect_stdout(io.StringIO()):
            with patch.object(sys, 'argv', ['install.py', '--configure-tools']):
                self.assertEqual(installer.main(), 0)
            run.assert_not_called()
            self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
            validate.reset_mock()
            with patch.object(sys, 'argv', ['install.py', '--configure-tools', '--apply']):
                self.assertEqual(installer.main(), 0)
            run.assert_called_once_with(['bash', str(ROOT / 'codex/install-tools.sh'),
                                         '--apply', '--configure-only'], check=True)
            self.assertEqual(validate.call_count, 2, 'Revalidate after plugin configuration')
        config = json.loads(self.config.read_text())
        self.assertEqual(len(config['daemon']['agentProfiles']), 13)

    def test_dry_run_never_writes_or_restarts(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(ROOT / 'codex/install.py'),
            '--offline', '--codex-home', str(self.codex), '--skills-dir', str(self.skills),
            '--paseo-home', str(self.paseo)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Preview only', result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_offline_apply_is_not_allowed(self):
        result = subprocess.run([sys.executable, str(ROOT / 'codex/install.py'),
                                 '--offline', '--apply'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('preview-only', result.stderr)


if __name__ == '__main__':
    unittest.main()
