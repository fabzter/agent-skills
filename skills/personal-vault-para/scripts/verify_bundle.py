#!/usr/bin/env python3
"""Build/check canonical manifests and export a commit-pinned public skill."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "fabzter/knowledge-base-conventions"
DOCS = {
    "README.md": "references/governance-index.md",
    "Knowledge Base Conventions.md": "references/conventions.md",
    "Knowledge Base Research and Decisions.md": "references/para-research.md",
    "Knowledge Base Lifecycle.md": "references/lifecycle.md",
    "Knowledge Base Sync.md": "references/sync-protocol.md",
}
BUNDLE_SOURCES = {
    "SKILL.md": "skill/SKILL.md",
    "scripts/sync_vault.py": "sync_engine.py",
    "scripts/cron_entry.py": "cron_entry.py",
    "scripts/verify_bundle.py": "tools/bundle.py",
    **{dest: "vault/00_meta/" + name for name, dest in DOCS.items()},
}
LOCK = "references/upstream-lock.json"
MAX_FILE_BYTES = 128 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def manifest(root: Path) -> dict:
    expected = set(DOCS)
    actual = {p.name for p in (root / "vault/00_meta").glob("*.md")}
    if actual != expected:
        raise ValueError(f"Unexpected/missing canonical notes: {actual ^ expected}")
    return {
        "schema_version": 1,
        "files": [
            {
                "source": "vault/00_meta/" + name,
                "target": "00_meta/" + name,
                "sha256": digest((root / "vault/00_meta" / name).read_bytes()),
            }
            for name in sorted(DOCS)
        ],
    }


def safe_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(c) < 32 for c in value)):
        raise ValueError("Invalid bundle path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError("Unsafe bundle path")
    return value


def validate_lock(lock: dict) -> None:
    if (lock.get("schema_version") != 1 or lock.get("repo") != REPOSITORY
            or not re.fullmatch(r"[0-9a-f]{40}", lock.get("commit", ""))):
        raise ValueError("Invalid upstream lock provenance")
    files = lock.get("files")
    if not isinstance(files, dict) or set(files) != set(BUNDLE_SOURCES):
        raise ValueError("Unexpected/missing bundle files")
    for dest, source in BUNDLE_SOURCES.items():
        safe_relative(dest)
        item = files[dest]
        if (item.get("source") != source
                or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", ""))):
            raise ValueError(f"Invalid locked file: {dest}")


def fetch_blob(commit: str, source: str) -> bytes:
    url = (f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/"
           + quote(safe_relative(source), safe="/"))
    request = Request(url, headers={"User-Agent": "knowledge-base-bundle-verifier/1"})
    with urlopen(request, timeout=15) as response:
        result = response.read(MAX_FILE_BYTES + 1)
    if len(result) > MAX_FILE_BYTES:
        raise ValueError("Upstream bundle file exceeds size limit")
    return result


def verify_bundle(bundle: Path, remote: bool = False) -> dict:
    if (bundle / LOCK).is_symlink():
        raise ValueError("Symlinked lock file is not an installed copy")
    lock = json.loads((bundle / LOCK).read_text())
    validate_lock(lock)
    for dest, item in lock["files"].items():
        path = bundle / safe_relative(dest)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing/symlinked bundle file: {dest}")
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES or digest(data) != item["sha256"]:
            raise ValueError(f"Bundle hash mismatch: {dest}")
        if remote and data != fetch_blob(lock["commit"], item["source"]):
            raise ValueError(f"Bundle differs from pinned public source: {dest}")
    # Every explicitly referenced support path must be shipped, not merely named.
    text = (bundle / "SKILL.md").read_text()
    references = re.findall(r"\]\(((?:references|scripts)/[^)\s]+)\)", text)
    declared = set(lock["files"]) | {LOCK}
    if set(references) - declared:
        raise ValueError(f"Unshipped SKILL.md references: {set(references) - declared}")
    return lock


def export_bundle(root: Path, output: Path) -> dict:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root, text=True
    )
    if status:
        raise ValueError("Export requires a clean committed source checkout")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    lock = {"schema_version": 1, "repo": REPOSITORY, "commit": commit, "files": {}}
    output = output.expanduser().absolute()
    if output.is_symlink():
        raise ValueError("Refusing symlinked export destination")
    # Stage data in memory from Git objects; never snapshot uncommitted working files.
    payload = {}
    for dest, source in BUNDLE_SOURCES.items():
        payload[dest] = subprocess.check_output(["git", "show", f"{commit}:{source}"], cwd=root)
        if len(payload[dest]) > MAX_FILE_BYTES:
            raise ValueError(f"Source exceeds size limit: {source}")
        lock["files"][dest] = {"source": source, "sha256": digest(payload[dest])}
    for dest, data in {**payload, LOCK: json_bytes(lock)}.items():
        path = output / safe_relative(dest)
        for parent in (path, *path.parents):
            if parent == output.parent:
                break
            if parent.is_symlink():
                raise ValueError(f"Refusing symlink in export path: {parent}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    verify_bundle(output)
    return lock


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("manifest")
    make.add_argument("--check", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--remote", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            expected = json_bytes(manifest(ROOT))
            path = ROOT / "manifest.json"
            if args.check:
                if not path.is_file() or path.read_bytes() != expected:
                    raise ValueError("Manifest is missing/stale; regenerate before committing")
                print("Canonical manifest verified")
            else:
                path.write_bytes(expected)
                print("Canonical manifest generated")
        elif args.command == "export":
            lock = export_bundle(ROOT, args.output)
            print(f"Exported complete skill from {REPOSITORY}@{lock['commit']}")
        else:
            lock = verify_bundle(args.bundle.expanduser(), args.remote)
            print(f"Verified {len(lock['files'])} files from {REPOSITORY}@{lock['commit']}")
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Bundle error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
