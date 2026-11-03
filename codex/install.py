#!/usr/bin/env python3
"""Install only the Codex adapter and merge its Paseo launch profiles."""
import argparse
import copy
import datetime
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
START = '<!-- PASEO_CODEX_STACK_START -->'
END = '<!-- PASEO_CODEX_STACK_END -->'
MODES = ('auto', 'auto-review', 'full-access')
ORCHESTRATOR_PROVIDER = 'codex-orchestrator'
ORCHESTRATOR_INSTRUCTIONS = (
    'You are the Paseo development orchestrator. For development tasks, use the installed '
    'codex-orchestrate and codex-pocock-paseo skills automatically. Read them before planning '
    'or delegating. Follow the user-approved scope and project instructions. '
    'For questions or simple checks, answer directly without unnecessary delegation.'
)


def merge_instructions(text, block):
    if START not in text and END not in text:
        return text.rstrip() + ('\n\n' if text.strip() else '') + block.strip() + '\n'
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('Ambiguous AGENTS.md markers; no files were changed')
    first, last = text.index(START), text.index(END)
    if last < first:
        raise ValueError('Reversed AGENTS.md markers; no files were changed')
    return text[:first] + block.strip() + text[last + len(END):]


def profiles(model=None, mode=None, thinking=None, source=None):
    result = json.loads((source or SOURCE / 'agent-profiles.json').read_text())
    if not isinstance(result, list) or not result:
        raise ValueError('Profiles must be a non-empty list')
    ids = set()
    for profile in result:
        if not isinstance(profile, dict):
            raise ValueError('Every profile must be an object')
        identity = profile.get('id', '')
        if not isinstance(identity, str) or not re.fullmatch(r'codex-[a-z0-9-]+', identity) or identity in ids:
            raise ValueError('Profile IDs must be unique and start with codex-')
        ids.add(identity)
        if profile.get('provider') not in ('codex', identity):
            raise ValueError(f'{identity}: provider must be codex or its own role ID')
        # Migrate older profiles that only carried notes on the generic provider.
        profile['provider'] = identity
        for key, override in [('model', model), ('modeId', mode), ('thinkingOptionId', thinking)]:
            if override is not None:
                profile[key] = override
        for key in ('name', 'model', 'thinkingOptionId', 'notes'):
            if not isinstance(profile.get(key), str) or not profile[key].strip():
                raise ValueError(f'{identity}: missing {key}')
        if profile.get('modeId') not in MODES:
            raise ValueError(f'{identity}: unsupported Codex mode')
    expected = {p['id'] for p in json.loads((SOURCE / 'agent-profiles.json').read_text())}
    if not expected.issubset(ids):
        raise ValueError('Custom profiles must include every role in codex/agent-profiles.json')
    return result


def merge_paseo(original, new_profiles, mode=None):
    result = copy.deepcopy(original)
    daemon = result.setdefault('daemon', {})
    if not isinstance(daemon, dict):
        raise ValueError('Paseo daemon must be an object')
    existing = daemon.get('agentProfiles', [])
    if not isinstance(existing, list) or any(not isinstance(p, dict) for p in existing):
        raise ValueError('Paseo agentProfiles must be a list of objects')
    new_profiles = copy.deepcopy(new_profiles)
    for profile in new_profiles:
        previous = next((p for p in existing if p.get('id') == profile['id']), {})
        profile['modeId'] = mode if mode is not None else previous.get('modeId', profile['modeId'])
        if profile['modeId'] not in MODES:
            raise ValueError(f"{profile['id']}: unsupported saved mode; choose --mode explicitly")
    ids = {p['id'] for p in new_profiles}
    daemon['agentProfiles'] = [p for p in existing if p.get('id') not in ids] + new_profiles
    mcp = daemon.setdefault('mcp', {})
    if not isinstance(mcp, dict):
        raise ValueError('Paseo daemon.mcp must be an object')
    mcp['injectIntoAgents'] = True
    agents = result.setdefault('agents', {})
    if not isinstance(agents, dict):
        raise ValueError('Paseo agents must be an object')
    providers = agents.setdefault('providers', {})
    if not isinstance(providers, dict):
        raise ValueError('Paseo providers must be an object')
    base = providers.get('codex', {})
    if not isinstance(base, dict):
        raise ValueError('Codex provider settings must be objects')
    command = base.get('command', ['codex'])
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError('Codex command must be a non-empty list of non-empty strings')
    for profile in new_profiles:
        role = providers.setdefault(profile['provider'], {})
        if not isinstance(role, dict):
            raise ValueError('Codex provider settings must be objects')
        # Paseo inherits runtime settings, but not configured model catalogs.
        for key in ('models', 'additionalModels'):
            if key not in role and key in base:
                role[key] = copy.deepcopy(base[key])
        instructions = (f"You are {profile['name']}. {profile['notes']} "
                        'Follow the user-approved scope and project instructions. ')
        if profile['provider'] == ORCHESTRATOR_PROVIDER:
            instructions += ORCHESTRATOR_INSTRUCTIONS
        else:
            instructions += ('Do not delegate to other agents. For a delegated ticket, '
                             'only the coordinator updates tracker state. Report results, '
                             'checks and limitations without claiming unperformed actions.')
        role.update(extends='codex', label=profile['name'], command=[
            *command, '-c', 'developer_instructions=' + json.dumps(instructions, ensure_ascii=False)])
    return result


def role_catalog(catalog, providers, provider):
    base = providers.get('codex', {})
    role = providers[provider]
    models, additions = role.get('models', []), role.get('additionalModels', [])
    for items in (models, additions):
        if not isinstance(items, list) or any(not isinstance(m, dict) or not isinstance(m.get('id'), str) for m in items):
            raise ValueError('Configured models must be a list of objects with string IDs')
        for model in items:
            if 'thinkingOptions' in model and (not isinstance(model['thinkingOptions'], list) or
                    any(not isinstance(option, dict) or not isinstance(option.get('id'), str)
                        for option in model['thinkingOptions'])):
                raise ValueError('Configured thinkingOptions must be a list of objects with string IDs')
    if models:
        result = copy.deepcopy(models)
    else:
        base_env, role_env = base.get('env', {}), role.get('env', {})
        if not isinstance(base_env, dict) or not isinstance(role_env, dict):
            raise ValueError('Provider env must be an object')
        same_env = all(base_env.get(key) == value for key, value in role_env.items())
        if same_env and all(role.get(key, []) == base.get(key, []) for key in ('models', 'additionalModels')):
            return catalog
        if not same_env or base.get('models') or base.get('additionalModels'):
            raise ValueError(f'Cannot validate the planned {provider} dynamic catalog; '
                             'set its explicit non-empty models list with thinkingOptions')
        result = copy.deepcopy(catalog)
    for addition in additions:
        existing = next((model for model in result if model['id'] == addition['id']), None)
        if existing is None:
            result.append(copy.deepcopy(addition))
        else:
            existing.update(addition)
    return result


def validate_models(new_profiles, paseo_home, planned_config):
    # The derived provider may not exist yet; validate its planned catalog.
    command = ['paseo', 'provider', 'models', 'codex', '--json', '--home', str(paseo_home)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=45)
    catalog = json.loads(result.stdout)
    if not isinstance(catalog, list) or any(not isinstance(m, dict) or not isinstance(m.get('id'), str)
                                         for m in catalog):
        raise ValueError('Unexpected Paseo model catalog format')
    # CLI thinkingOptions is display text; configured thinkingOptions is structured.
    catalog = [{'id': m['id'], 'thinkingOptions': [{'id': option} for option in m.get('thinkingOptionIds', [])]}
               for m in catalog]
    catalogs = {'codex': catalog}
    for provider in {p['provider'] for p in new_profiles} - {'codex'}:
        catalogs[provider] = role_catalog(catalog, planned_config['agents']['providers'], provider)
    for profile in new_profiles:
        model, thinking = profile['model'], profile['thinkingOptionId']
        match = next((m for m in catalogs[profile['provider']] if m.get('id') == model), None)
        if not match:
            raise ValueError(f"Model {model!r} is not available for {profile['provider']}")
        options = [option['id'] for option in match.get('thinkingOptions', [])]
        if thinking not in options:
            raise ValueError(f'Thinking {thinking!r} is not supported by {model!r}')


def merge_hooks(original, hook_path):
    if not isinstance(original, dict):
        raise ValueError('hooks.json must be an object')
    result = copy.deepcopy(original)
    events = result.setdefault('hooks', {})
    if not isinstance(events, dict):
        raise ValueError('hooks must be an object')
    groups = events.setdefault('SessionStart', [])
    if not isinstance(groups, list):
        raise ValueError('SessionStart hooks must be a list')
    command = 'python3 ' + shlex.quote(str(hook_path))
    entry = {'matcher': 'startup|resume', 'hooks': [
        {'type': 'command', 'command': command, 'async': True, 'timeout': 300}
    ]}
    if entry not in groups:
        groups.append(entry)
    return result


def build_plan(codex_home, skills_dir, paseo_home, new_profiles, mode=None):
    config_path = paseo_home / 'config.json'
    if not config_path.is_file():
        raise ValueError(f'Existing Paseo config required: {config_path}')
    config = json.loads(config_path.read_text())
    if not isinstance(config, dict):
        raise ValueError('Paseo config must be an object')
    override = codex_home / 'AGENTS.override.md'
    if override.exists() and override.read_text().strip():
        raise ValueError(f'{override} shadows AGENTS.md; integrate the stack block there explicitly first')
    agent_path = codex_home / 'AGENTS.md'
    current = agent_path.read_text() if agent_path.exists() else ''
    hook_path = codex_home / 'hooks' / 'paseo-codegraph-autoindex.py'
    hooks_json = codex_home / 'hooks.json'
    hooks = json.loads(hooks_json.read_text()) if hooks_json.exists() else {}
    plan = {
        agent_path: merge_instructions(current, (SOURCE / 'AGENTS.dev-stack.md').read_text()).encode(),
        config_path: (json.dumps(merge_paseo(config, new_profiles, mode), ensure_ascii=False, indent=2) + '\n').encode(),
        hooks_json: (json.dumps(merge_hooks(hooks, hook_path), indent=2) + '\n').encode(),
        hook_path: (SOURCE / 'hooks' / 'codegraph-autoindex.py').read_bytes(),
        codex_home / 'rules' / 'paseo-aio.rules': (SOURCE / 'paseo-aio.rules').read_bytes(),
    }
    for source in sorted((SOURCE / 'skills').rglob('*')):
        if source.is_file():
            plan[skills_dir / source.relative_to(SOURCE / 'skills')] = source.read_bytes()
    # Preserve existing built-in Paseo skills; ship their upstream license too.
    upstream = SOURCE.parent / 'paseo' / 'skills'
    for directory in sorted(upstream.iterdir()):
        if not directory.is_dir() or (skills_dir / directory.name).exists():
            continue
        for source in directory.rglob('*'):
            if source.is_file():
                plan[skills_dir / directory.name / source.relative_to(directory)] = source.read_bytes()
        plan[skills_dir / directory.name / 'LICENSE'] = (upstream / 'LICENSE').read_bytes()
    return plan


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply_plan(plan, backup_root):
    changes = {p: data for p, data in plan.items() if not p.exists() or p.read_bytes() != data}
    for path in changes:
        if path.is_symlink():
            raise ValueError(f'Refusing to replace symlink: {path}')
    if not changes:
        print('Already up to date; no files changed.')
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = backup_root / stamp
    backup.mkdir(parents=True, mode=0o700)
    manifest = []
    for index, path in enumerate(changes):
        saved = backup / str(index) if path.exists() else None
        if saved:
            shutil.copyfile(path, saved)
            saved.chmod(0o600)
        manifest.append({'path': str(path), 'backup': str(saved) if saved else None,
                         'mode': path.stat().st_mode & 0o777 if path.exists() else 0o600})
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    written = []
    try:
        for entry in manifest:
            path = Path(entry['path'])
            atomic_write(path, changes[path], entry['mode'])
            written.append(entry)
    except BaseException:
        for entry in reversed(written):
            path = Path(entry['path'])
            if entry['backup']:
                atomic_write(path, Path(entry['backup']).read_bytes(), entry['mode'])
            else:
                path.unlink(missing_ok=True)
        raise
    print(f'Applied {len(changes)} files. Backup: {backup}')
    print('Reload Paseo with paseo reload. Review new hooks in Codex /hooks, then start a new session.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write files; default is a read-only preview')
    parser.add_argument('--with-tools', action='store_true', help='install pinned RTK, CodeGraph, Playwright CLI and Codex plugins')
    parser.add_argument('--configure-tools', action='store_true', help='configure installed tools and install Codex plugins without downloading binaries')
    parser.add_argument('--with-browser', action='store_true', help='also download Chromium (requires --with-tools)')
    parser.add_argument('--profiles', type=Path, default=SOURCE / 'agent-profiles.json')
    parser.add_argument('--model', help='override the model in all Codex profiles')
    parser.add_argument('--thinking', help='override reasoning effort in all Codex profiles')
    parser.add_argument('--mode', choices=MODES, help='override permission mode in all Codex profiles; default: preserve saved modes')
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))))
    parser.add_argument('--skills-dir', type=Path, default=Path.home() / '.agents' / 'skills')
    parser.add_argument('--paseo-home', type=Path, default=Path(os.environ.get('PASEO_HOME', str(Path.home() / '.paseo'))))
    parser.add_argument('--offline', action='store_true', help='skip live model validation, for staging/tests only')
    args = parser.parse_args()
    if args.configure_tools and args.with_tools:
        parser.error('--configure-tools cannot be combined with --with-tools')
    if args.with_browser and not args.with_tools:
        parser.error('--with-browser requires --with-tools')
    if (args.with_tools or args.configure_tools) and (args.codex_home != parser.get_default('codex_home') or args.skills_dir != parser.get_default('skills_dir')):
        parser.error('Tool setup uses the current Codex user; custom staging paths support configs only')
    try:
        if args.apply and args.offline:
            parser.error('--offline is preview-only; apply requires live model validation')
        new_profiles = profiles(args.model, args.mode, args.thinking, args.profiles)
        plan = build_plan(args.codex_home.expanduser().absolute(), args.skills_dir.expanduser().absolute(),
                          args.paseo_home.expanduser().absolute(), new_profiles, args.mode)
        config_path = args.paseo_home.expanduser().absolute() / 'config.json'
        if not args.offline:
            validate_models(new_profiles, config_path.parent, json.loads(plan[config_path]))
        else:
            print('OFFLINE: model availability was not verified.')
        owned_ids = {p['id'] for p in new_profiles}
        planned_profiles = [p for p in json.loads(plan[config_path])['daemon']['agentProfiles']
                            if p.get('id') in owned_ids]
        for profile in planned_profiles:
            print(f"{profile['id']}: {profile['model']} / {profile['thinkingOptionId']} / {profile['modeId']}")
        if any(p['modeId'] == 'full-access' for p in planned_profiles):
            print('Full Access: these new agents will run without the Codex filesystem sandbox.')
        if args.with_tools:
            print('Tools: pinned RTK, CodeGraph, Playwright CLI, Matt Pocock and Ponytail; Chromium=' + str(args.with_browser))
        if args.configure_tools:
            print('Tools: configure existing binaries and install Matt Pocock/Ponytail plugins; no binary/browser downloads')
        for path, data in plan.items():
            state = 'unchanged' if path.exists() and path.read_bytes() == data else 'write'
            print(f'{state}: {path}')
        if args.apply:
            sys.stdout.flush()
            if args.with_tools or args.configure_tools:
                command = ['bash', str(SOURCE / 'install-tools.sh'), '--apply']
                if args.configure_tools:
                    command.append('--configure-only')
                if args.with_browser:
                    command.append('--browser')
                subprocess.run(command, check=True)
                # Tool installers may add instructions/hooks. Merge against their
                # fresh output rather than overwriting it with the preview.
                plan = build_plan(args.codex_home.expanduser().absolute(), args.skills_dir.expanduser().absolute(),
                                  args.paseo_home.expanduser().absolute(), new_profiles, args.mode)
                validate_models(new_profiles, config_path.parent, json.loads(plan[config_path]))
            apply_plan(plan, args.codex_home.expanduser().absolute() / 'backups' / 'paseo-aio')
        else:
            print('Preview only. Add --apply to write this plan. No packages installed or daemon restarted.')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
