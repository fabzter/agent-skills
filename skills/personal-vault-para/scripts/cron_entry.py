#!/usr/bin/env python3
"""Place a regular copy in HERMES_HOME/scripts; invoke the reviewed installed skill.

This wrapper never fetches executable code. Its child runs in a new process group
so an execution-budget failure can stop this sync's own descendants safely.
"""
from pathlib import Path
import os
import signal
import subprocess
import sys


def main(argv=None, profile_root=None, timeout=110):
    root = Path(profile_root) if profile_root is not None else Path(__file__).resolve().parents[1]
    script = root / 'skills/personal-vault-para/scripts/sync_vault.py'
    if not script.is_file() or script.is_symlink():
        print('Knowledge-base sync skill is not installed as a regular GitHub bundle: ' + str(script),
              file=sys.stderr)
        return 1
    arguments = sys.argv[1:] if argv is None else argv
    try:
        child = subprocess.Popen([sys.executable, str(script), *arguments], start_new_session=True)
    except OSError as error:
        print('Cannot start installed knowledge-base sync: ' + str(error), file=sys.stderr)
        return 1
    try:
        return child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=5)
        print('Knowledge-base sync exceeded its execution budget; inspect journal and cron run status.',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
