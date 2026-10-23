#!/usr/bin/env python3
"""Mirror validated public governance Markdown through the official Obsidian CLI.

No LLM, third-party libraries, vault-data uploads, deletion or downloaded code.
Configuration is private. The executable itself is updated only by an explicit
reviewed skill release; its public Markdown source may advance independently.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

STATUS_PATH = '00_meta/Knowledge Base Sync Status.md'
MAX_FILE = 128 * 1024
MAX_TOTAL = 512 * 1024
MAX_FILES = 20


class SyncError(RuntimeError):
    pass


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Deadline:
    def __init__(self, seconds=100):
        self.end = time.monotonic() + seconds

    def timeout(self, limit=15):
        remaining = self.end - time.monotonic()
        if remaining <= 0:
            raise SyncError('Sync exceeded its bounded execution budget')
        return min(float(limit), remaining)


def safe_target(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise SyncError('Invalid managed destination')
    path = PurePosixPath(value)
    if (any(ord(c) < 32 or ord(c) == 127 for c in value)
            or path.is_absolute() or '..' in path.parts or str(path) != value
            or len(path.parts) != 2 or path.parts[0] != '00_meta'
            or not value.endswith('.md')):
        raise SyncError('Unsafe managed destination: ' + repr(value))
    return value


def entries(manifest, allowed=None):
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise SyncError('Unsupported manifest schema')
    rows = manifest.get('files')
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FILES:
        raise SyncError('Manifest has an invalid number of documents')
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            raise SyncError('Malformed manifest entry')
        target = safe_target(row.get('target'))
        if target == STATUS_PATH or target in found:
            raise SyncError('Duplicate/reserved manifest destination: ' + target)
        if row.get('source') != 'vault/' + target:
            raise SyncError('Manifest source mapping is not canonical: ' + target)
        if not isinstance(row.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
            raise SyncError('Invalid content hash: ' + target)
        found[target] = row
    if allowed is not None and set(found) != set(allowed):
        raise SyncError('Manifest destinations differ from the local fixed allowlist')
    return found


def validate_payload(commit, manifest, files, allowed):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise SyncError('Upstream did not resolve to an immutable commit')
    rows = entries(manifest, allowed)
    if not isinstance(files, dict) or set(files) != {r['source'] for r in rows.values()}:
        raise SyncError('Incomplete or expanded document payload')
    result = {}
    total = 0
    for target, row in rows.items():
        data = files[row['source']]
        if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_FILE:
            raise SyncError('Empty/oversized document: ' + target)
        total += len(data)
        if total > MAX_TOTAL or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise SyncError('Payload size/hash validation failed: ' + target)
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as error:
            raise SyncError('Document is not UTF-8: ' + target) from error
        if '\x00' in text:
            raise SyncError('Binary/NUL content is not a Markdown document')
        result[target] = text
    return result


def validate_config(config):
    if not isinstance(config, dict):
        raise SyncError('Configuration must be a JSON object')
    cfg = dict(config)
    for key in ('repo', 'ref', 'vault', 'expected_vault_path', 'obsidian_cli', 'state_dir'):
        if not isinstance(cfg.get(key), str) or not cfg[key].strip():
            raise SyncError('Missing explicit configuration: ' + key)
        if any(ord(c) < 32 for c in cfg[key]):
            raise SyncError('Control characters in configuration: ' + key)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', cfg['repo']):
        raise SyncError('Repository must be an explicit owner/name')
    if len(cfg['ref']) > 200:
        raise SyncError('Invalid upstream ref')
    for key in ('expected_vault_path', 'obsidian_cli', 'state_dir'):
        cfg[key] = str(Path(cfg[key]).expanduser())
        if not Path(cfg[key]).is_absolute():
            raise SyncError('Configuration path must be absolute: ' + key)
    if Path(cfg['state_dir']).resolve().is_relative_to(Path(cfg['expected_vault_path']).resolve()):
        raise SyncError('Private state must stay outside the vault')
    allowed = cfg.get('allowed_paths')
    if (not isinstance(allowed, list) or not 1 <= len(allowed) <= MAX_FILES
            or len(allowed) != len(set(allowed))):
        raise SyncError('A nonempty unique local destination allowlist is required')
    cfg['allowed_paths'] = [safe_target(path) for path in allowed]
    if STATUS_PATH in allowed:
        raise SyncError('Generated status is not an upstream manifest destination')
    for key, default in [('request_timeout', 8), ('command_timeout', 15)]:
        value = cfg.get(key, default)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value <= 30:
            raise SyncError('Invalid bounded timeout: ' + key)
        cfg[key] = value
    return cfg


class GitHubSource:
    def __init__(self, config, deadline):
        self.config, self.deadline = config, deadline

    def _get(self, url):
        for attempt in range(2):
            try:
                request = Request(url, headers={'User-Agent': 'knowledge-base-conventions-sync/1'})
                with urlopen(request, timeout=self.deadline.timeout(self.config.get('request_timeout', 8))) as response:
                    data = response.read(MAX_FILE + 1)
                if len(data) > MAX_FILE:
                    raise SyncError('Upstream file exceeds the download limit')
                return data
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                transient = not isinstance(error, HTTPError) or error.code in (429, 500, 502, 503, 504)
                if attempt or not transient:
                    raise SyncError('Public upstream unavailable: ' + str(error)) from error
                time.sleep(min(0.2, self.deadline.timeout()))
        raise SyncError('Public upstream request failed')

    def pull(self):
        repo, ref = self.config['repo'], quote(self.config['ref'], safe='')
        try:
            commit = json.loads(self._get(f'https://api.github.com/repos/{repo}/commits/{ref}'))['sha']
            if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
                raise SyncError('Invalid resolved GitHub commit')
            base = f'https://raw.githubusercontent.com/{repo}/{commit}/'
            manifest = json.loads(self._get(base + 'manifest.json'))
            rows = entries(manifest, self.config.get('allowed_paths'))
            files = {row['source']: self._get(base + quote(row['source'], safe='/'))
                     for row in rows.values()}
            return commit, manifest, files
        except (ValueError, KeyError, TypeError) as error:
            raise SyncError('Malformed upstream metadata or manifest') from error


class ObsidianBackend:
    def __init__(self, config, deadline):
        self.config, self.deadline = config, deadline
        self.root = Path(config['expected_vault_path'])
        self.seen = {}

    def _call(self, *args):
        try:
            result = subprocess.run(
                [self.config['obsidian_cli'], 'vault=' + self.config['vault'], *args],
                capture_output=True, text=True, check=False,
                timeout=self.deadline.timeout(self.config['command_timeout']),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SyncError('Native Obsidian CLI unavailable or timed out') from error
        if result.returncode or result.stdout.lstrip().lower().startswith(('error:', 'cannot find')):
            raise SyncError('Native Obsidian command failed: ' + (result.stderr or result.stdout).strip())
        return result.stdout

    def verify(self):
        actual = self._call('vault', 'info=path').strip()
        if not actual or os.path.realpath(actual) != os.path.realpath(self.root):
            raise SyncError('Explicit vault/path mismatch; refusing all writes')

    def _guard(self, path):
        safe_target(path)
        candidate = self.root / path
        try:
            if (self.root / '00_meta').is_symlink() or candidate.is_symlink():
                raise SyncError('Refusing symlinked managed note/directory: ' + path)
        except PermissionError:
            # Native access can work while independent filesystem access is denied.
            # New native creates omit overwrite; unreadable indexed originals fail below.
            pass
        return candidate

    def read(self, path):
        candidate = self._guard(path)
        output = self._call('files', 'folder=00_meta')
        indexed = set(output.splitlines())
        if any(line and not line.startswith('00_meta/') for line in indexed):
            raise SyncError('Unexpected native vault file-list response')
        if path not in indexed:
            try:
                if candidate.exists():
                    raise SyncError('Managed note exists but is not indexed; refusing blind write: ' + path)
            except PermissionError:
                pass
            self.seen[path] = False
            return None
        text = self._call('read', 'path=' + path)
        info = self._call('file', 'path=' + path)
        fields = dict(line.split('\t', 1) for line in info.splitlines() if '\t' in line)
        try:
            if fields['path'] != path or int(fields['size']) != len(text.encode('utf-8')):
                raise SyncError('Native readback path/size mismatch: ' + path)
        except (KeyError, ValueError) as error:
            raise SyncError('Malformed native file metadata: ' + path) from error
        self.seen[path] = True
        return text

    def write(self, path, text):
        self._guard(path)
        args = ['create', 'path=' + path, 'content=' + text]
        if self.seen.get(path):
            args.append('overwrite')
        self._call(*args)

    def verify_disk(self, path, text):
        # File Provider reads can hang. Bound the independent check in a subprocess,
        # not a non-cancellable thread. The helper only returns a hash, never content.
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), '--disk-hash', str(self.root / path)],
                capture_output=True, text=True, timeout=self.deadline.timeout(4), check=False,
            )
            report = json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return 'unavailable: independent disk read timed out'
        except (OSError, ValueError) as error:
            raise SyncError('Independent disk verification failed: ' + path) from error
        if report.get('status') == 'unavailable':
            return 'unavailable: macOS permission denial'
        if result.returncode or report.get('sha256') != digest(text):
            raise SyncError('Independent disk bytes differ: ' + path)
        return 'verified'


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SyncError('Refusing symlinked private state file: ' + str(path))
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


@contextmanager
def exclusive_lock(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(directory / 'sync.lock', flags, 0o600)
    except OSError as error:
        raise SyncError('Cannot open private sync lock') from error
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SyncError('Another governance sync is already running') from error
        yield
    finally:
        os.close(descriptor)


def read_state(path, identity, allowed):
    if path.is_symlink():
        raise SyncError('Refusing symlinked state')
    if not path.exists():
        return {'schema_version': 1, 'identity': identity, 'files': {}, 'inflight': {}}
    try:
        state = json.loads(path.read_text())
        if (state.get('schema_version') != 1 or state.get('identity') != identity
                or not isinstance(state.get('files'), dict) or not isinstance(state.get('inflight'), dict)):
            raise ValueError('identity/schema mismatch')
        if (set(state['files']) | set(state['inflight'])) - (set(allowed) | {STATUS_PATH}):
            raise ValueError('unmanaged paths in state')
        for item in state['files'].values():
            if not isinstance(item, dict) or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', '')):
                raise ValueError('invalid verified state hash')
        for item in state['inflight'].values():
            if not isinstance(item, dict) or not re.fullmatch('[0-9a-f]{64}', item.get('desired_sha256', '')):
                raise ValueError('invalid write journal')
        return state
    except (OSError, ValueError, TypeError, AttributeError) as error:
        raise SyncError('Private sync state is unreadable/corrupt or belongs to another scope') from error


def installed_revision():
    lock = Path(__file__).resolve().parents[1] / 'references/upstream-lock.json'
    if not lock.exists():
        return 'unavailable (standalone checkout)'
    try:
        value = json.loads(lock.read_text())
        revision = value['commit']
        if not re.fullmatch('[0-9a-f]{40}', revision):
            raise ValueError('invalid commit')
        return revision
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SyncError('Installed skill has an invalid upstream lock') from error


def status_text(config, commit, snapshot, applied, documents):
    lines = [
        '---', 'type: system', 'status: verified', 'managed: knowledge-base-sync', '---', '',
        '# Knowledge Base Sync Status', '',
        f'- Source: https://github.com/{config["repo"]}/tree/{commit}',
        f'- Applied upstream commit: `{commit}`',
        f'- Installed skill reference snapshot: `{snapshot}`',
        f'- Last completed mirror generation (UTC): `{applied}`',
        '- This describes the last completed mirror, not the health of every later check.',
        '- Private health and scheduler run records are authoritative for failed checks.', '',
        '## Verified managed documents', '', '| Note | SHA-256 |', '| --- | --- |',
    ]
    lines += [f'| [[{path[:-3]}]] | `{digest(text)}` |' for path, text in sorted(documents.items())]
    lines += ['', '## Scope', '',
              'Only the explicitly configured governance notes and this generated status are managed.',
              '[[00_meta/Local Vault Conventions]] and other private notes are never uploaded or overwritten.',
              'A newer vault revision than the skill snapshot is explicit version skew; read current vault governance first.', '']
    return '\n'.join(lines)


def run_sync(config, source=None, backend=None, dry_run=False):
    cfg = validate_config(config)
    directory = Path(cfg['state_dir'])
    deadline = Deadline()
    with exclusive_lock(directory):
        try:
            identity = {key: cfg[key] for key in ('repo', 'vault', 'expected_vault_path')}
            state = read_state(directory / 'state.json', identity, cfg['allowed_paths'])
            source = source or GitHubSource(cfg, deadline)
            backend = backend or ObsidianBackend(cfg, deadline)
            commit, manifest, files = source.pull()
            documents = validate_payload(commit, manifest, files, cfg['allowed_paths'])
            backend.verify()
            snapshot = installed_revision()
            same_generation = (state.get('last_complete_commit') == commit
                               and state.get('installed_snapshot') == snapshot)
            applied = state.get('applied_at') if same_generation else now()
            desired = {**documents, STATUS_PATH: status_text(cfg, commit, snapshot, applied, documents)}
            originals = {}
            # Preflight the complete batch before any note writes or adoption checkpoints.
            for target, text in desired.items():
                current = backend.read(target)
                originals[target] = current
                current_hash = digest(current) if current is not None else None
                record = state['files'].get(target)
                pending = state['inflight'].get(target)
                if pending and current_hash == pending['desired_sha256']:
                    record = {'sha256': current_hash, 'commit': pending.get('commit')}
                    state['files'][target] = record
                    del state['inflight'][target]
                if record and current is None:
                    raise SyncError('Local deletion conflict: ' + target)
                expected = record.get('sha256') if record else None
                if current is not None and current != text and current_hash != expected:
                    raise SyncError('Local edit/adoption conflict: ' + target)
            changed = [target for target, text in desired.items() if originals[target] != text]
            if dry_run:
                return {'commit': commit, 'changed': changed, 'dry_run': True}
            checks = {}
            for target, text in desired.items():
                deadline.timeout()
                current = originals[target]
                if backend.read(target) != current:
                    raise SyncError('Concurrent modification conflict: ' + target)
                if target in changed:
                    if current is not None:
                        folder = directory / 'backups' / hashlib.sha256(target.encode()).hexdigest()
                        backup = folder / (digest(current) + '.md')
                        if not backup.exists():
                            atomic_write(backup, current.encode())
                        elif backup.read_bytes() != current.encode():
                            raise SyncError('Private prior-version backup mismatch')
                    state['inflight'][target] = {
                        'old_sha256': digest(current) if current is not None else None,
                        'desired_sha256': digest(text), 'commit': commit,
                    }
                    save_json(directory / 'state.json', state)
                    backend.write(target, text)
                    if backend.read(target) != text:
                        raise SyncError('Native readback mismatch after write: ' + target)
                checks[target] = backend.verify_disk(target, text)
                state['files'][target] = {'sha256': digest(text), 'commit': commit}
                state['inflight'].pop(target, None)
                save_json(directory / 'state.json', state)
            state.update(last_complete_commit=commit, installed_snapshot=snapshot, applied_at=applied)
            save_json(directory / 'state.json', state)
            save_json(directory / 'health.json', {
                'ok': True, 'checked_at': now(), 'commit': commit, 'changed': changed,
                'independent_disk_verification': checks,
            })
            return {'commit': commit, 'changed': changed, 'dry_run': False}
        except Exception as error:
            if not dry_run:
                try:
                    save_json(directory / 'health.json', {'ok': False, 'checked_at': now(), 'error': str(error)})
                except OSError:
                    pass
            if isinstance(error, SyncError):
                raise
            raise SyncError(str(error)) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
                        default=Path(os.environ.get('KB_SYNC_CONFIG', '~/.config/knowledge-base-sync/config.json')).expanduser())
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--disk-hash', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.disk_hash is not None:
        try:
            data = args.disk_hash.read_bytes()
            print(json.dumps({'status': 'ok', 'sha256': hashlib.sha256(data).hexdigest()}))
            return 0
        except PermissionError:
            print(json.dumps({'status': 'unavailable'}))
            return 0
        except OSError as error:
            print(json.dumps({'status': 'error', 'error': str(error)}))
            return 1
    try:
        config = json.loads(args.config.expanduser().read_text())
        result = run_sync(config, dry_run=args.dry_run)
        if result['changed'] or args.dry_run:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (SyncError, OSError, ValueError) as error:
        print('Knowledge-base sync failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
