---
type: system
status: active
version: 1.1.0
managed: knowledge-base-conventions
---

# Knowledge Base Sync

## One source, several usable copies

- **Authoring source:** [fabzter/knowledge-base-conventions](https://github.com/fabzter/knowledge-base-conventions), specifically the managed files under `vault/00_meta`.
- **Vault mirror:** complete Markdown notes at the same vault-relative `00_meta` paths.
- **Skill source:** [personal-vault-para in fabzter/agent-skills](https://github.com/fabzter/agent-skills/tree/main/skills/personal-vault-para), containing an exported reference snapshot and reviewed sync script.
- **Skill provenance:** `references/upstream-lock.json` records the source repository, commit and expected hash of every exported file.
- **Private additions:** the vault owner's `00_meta/Local Vault Conventions.md`, plus a private JSON sync configuration outside both public repos.

The vault mirror can follow the configured upstream branch while the skill remains on an older declared release. Agents must read current vault governance and inspect revision status before treating their bundled fallback as current. Automatic skill reinstallation is intentionally separate from automatic Markdown mirroring: a documentation update must not silently replace executable code.

## What the scheduled job does

1. Acquire an exclusive local lock.
2. Resolve the configured public GitHub ref to a single immutable commit.
3. Fetch the manifest and documents from that commit, never from a moving ref during the download.
4. Validate schema, sizes, paths and content hashes before any vault mutation.
5. Verify the explicit vault name resolves to the expected configured directory.
6. Preflight every managed note for collisions, local edits, missing tracked files and concurrent modifications.
7. Write only allowed notes through the official Obsidian CLI, verifying exact readback and durable per-note state after each write.
8. Record revision/health status locally and in the generated vault status note.

A successful no-op prints nothing. A failure exits nonzero with a useful diagnostic; previous verified content remains available. Network failures do not justify fabricating content or falling back to unverified writes.

## What it cannot do

- No LLM calls or model credentials.
- No execution of newly downloaded repository code.
- No automatic upload or commit of vault data.
- No deletion, renaming, archiving or classification of existing notes.
- No account switching, background permission changes or alternate vault selection.
- No filesystem fallback writes into the vault.
- No new write authority just because the upstream manifest adds a path.

Only private configuration can approve an additional managed destination. Unrelated notes in `00_meta`, including private local conventions, remain untouched.

## Local configuration

The installed script uses `~/.config/knowledge-base-sync/config.json` by default. `--config` or `KB_SYNC_CONFIG` can select another explicit configuration. See the repository's generic `config.example.json`; do not commit the real config.

Important fields are the source repository/ref, explicit vault name, expected absolute vault directory, absolute official CLI executable, private state directory and the fixed allowed note paths. A mismatch between the requested vault and the path returned by the native CLI is a hard failure.

The native CLI requires the application to be running and responsive. An unavailable app or denied account/path is a blocked sync, not permission to bypass the CLI or write elsewhere. Retry after restoring the actual prerequisite.

## Commands

From a checkout of the canonical documentation repository:

```bash
python3 -m unittest discover -s tests -v
python3 tools/bundle.py manifest --check
python3 sync_engine.py --config /path/to/private-config.json --dry-run
python3 sync_engine.py --config /path/to/private-config.json
```

The installed skill ships the same reviewed executable as `scripts/sync_vault.py`. It needs Python 3.10+ and the official Obsidian CLI; no additional Python packages or API keys are required.

The sync uses POSIX file locking (macOS/Linux). Hermes restricts scheduled entry points to its profile's `scripts` directory: install the small reviewed `scripts/cron_entry.py` wrapper there as a regular file. The wrapper runs the installed skill's executable with a bounded process lifetime; do not schedule an absolute path outside Hermes's allowed scripts directory or use a symlink to bypass that check.

## Changing shared conventions

1. Edit canonical documents in the documentation repository, not the managed vault mirror.
2. Run tests and regenerate the manifest with `python3 tools/bundle.py manifest`.
3. Review the diff for privacy, scope and compatibility, then commit and push.
4. The next configured deterministic sync updates matching allowed vault notes. Run it manually when the update is needed immediately.
5. To release the same material to the public skill, export from a clean committed checkout:

```bash
python3 tools/bundle.py export --output /path/to/agent-skills/skills/personal-vault-para
python3 tools/bundle.py verify --bundle /path/to/agent-skills/skills/personal-vault-para
```

6. Commit/push the generated skill bundle in `agent-skills`, then reinstall from that repository:

```bash
hermes skills install fabzter/agent-skills/skills/personal-vault-para --yes --force
```

7. Verify installed content and provenance, not only the install command's return code. Re-run the sync to refresh the status's installed-snapshot revision when appropriate.

No submodule initialization, implicit network cloning or editing of the installed references is required. The repository CI and pinned bundle checks make accidental divergence visible.

## Handling a conflict

A managed note that no longer matches its last verified version is treated as a local edit. A tracked note that disappears is treated as a local deletion. An unknown pre-existing note with different content is an adoption conflict. Synchronization stops instead of erasing it.

1. Read the diagnostic and compare the local note with the upstream version and private prior-version backup/journal.
2. Decide whether the change belongs in shared conventions, in the private local-conventions note, or should be discarded.
3. Preserve any desired local content first. Changes to shared rules go through the source repository; private additions stay private.
4. Restore the managed note to its last verified form, or to the exact reviewed incoming version, only with the owner's approval.
5. Re-run dry-run and sync, then verify the conflict is gone.

There is intentionally no blanket overwrite/force switch. Deleting state is not a normal conflict-resolution procedure: it loses evidence of ownership and prior versions.

## Interrupted and failed runs

A durable per-note journal allows a subsequent run to distinguish a verified prior write from arbitrary changed content. A partial run is not claimed to be an all-files atomic transaction. The next run revalidates inputs and resumes safe progress; it never reports a new global successful revision until all required notes verify.

The native CLI does not offer a cross-process compare-and-swap or a multi-note transaction. Immediate rechecks detect intervening edits but cannot provide database-level isolation against an edit in the tiny interval before the app applies a write. Keep managed mirrors read-only during sync; put local additions in the unmanaged note. The design deliberately avoids pretending this residual race does not exist.

Failed network or native CLI operations retain existing mirrors. Check the private health record and scheduler's durable run record. The generated vault status describes the last completed mirror, not a promise that the latest check succeeded; a failed check may be unable to update the vault at all.

To roll back deliberately, configure the source ref to a reviewed immutable earlier commit and run the same preflight/verification path. Do not use an unreviewed branch reset or destructive checkout of vault files.

## Scheduling and visibility

The deployment can use Hermes `no_agent=true` with the reviewed entry-point wrapper every six hours. Schedule only when explicitly requested. Healthy no-ops are silent. Errors are nonzero; scheduler output and local health provide diagnostics.

A local TUI job does not deliver live messages back into its conversation. Gateway notifications need an explicitly selected delivery channel; local logs and a status note are not a substitute for push alerts. The app and scheduler must be running for their respective parts to execute.
