---
name: personal-vault-para
description: "Use when organizing a personal Obsidian vault with PARA."
version: 2.1.0
author: fabzter
license: MIT
metadata:
  hermes:
    tags: [obsidian, personal-vault, para, knowledge-management]
    homepage: https://github.com/fabzter/knowledge-base-conventions
---

# Personal Vault PARA

## When to use

Read, create, classify, maintain or migrate notes in an explicitly authorized personal Obsidian vault. Use the reference copies for questions about the system's research, conventions or PARA lifecycle. This is not permission to operate on an organization's vault, publish private content or reorganize existing notes.

## Authority and complete reference copies

The shared rules are authored in [knowledge-base-conventions](https://github.com/fabzter/knowledge-base-conventions). This GitHub-installed skill carries a complete, pinned snapshot, not just a pointer:

- [Governance index](references/governance-index.md)
- [Conventions](references/conventions.md)
- [Research and decisions](references/para-research.md)
- [Lifecycle](references/lifecycle.md)
- [Sync protocol and maintenance](references/sync-protocol.md)
- [Pinned upstream revision and hashes](references/upstream-lock.json)
- [Offline/pinned-source bundle verifier](scripts/verify_bundle.py)

The vault contains the same shared documentation under `00_meta`, plus optional private local conventions. Its current mirror may be newer than this release snapshot. Never assume copies are current simply because they exist.

## Procedure

1. Identify the exact personal vault/account from the user's task or trusted local configuration. Verify the explicit vault's actual path with the native Obsidian CLI. Do not silently use another account, a similarly named vault or a path from historical memory.
2. Read `00_meta/README.md`, `00_meta/Knowledge Base Conventions.md`, `00_meta/Local Vault Conventions.md` when present, and `00_meta/Knowledge Base Sync Status.md`. Local conventions contain private scope/domain details and are never part of the public bundle.
3. Compare the applied upstream revision with this skill's lock file. Prefer the verified current vault rules; this bundled copy is the offline/released fallback. If live rules are unavailable or version differences matter, say which snapshot is being used. Do not invent updates or silently discard a conflicting local rule.
4. Start at the actual active project and its authoritative tracker, then read the relevant Area and only the supporting Resources/People needed. A historical prep brief is preserved context, not current process-status authority.
5. Classify by actionability: a concrete active outcome -> Projects; an ongoing responsibility/standard -> Areas; general reference/interest -> Resources; inactive material -> Archive. System documentation -> Meta. Capture unclassified material in Inbox. Link related contexts rather than copying the note.
6. Keep company/project ownership intact. For multi-company work, use a neutral staging parent and separate company children; durable company notes belong in their own project home. Shared reusable context belongs in its Area/Resource, not beneath another company.
7. Use the official Obsidian CLI for supported note operations with an explicit vault and exact `.md` path. Read before modifying. Preserve content, frontmatter, source evidence, hand edits, stable IDs and existing naming conventions. Verify complete readback; independently verify disk bytes when accessible. Report verification limitations rather than claiming an unperformed check.
8. Treat migrations, bulk renames, archiving, publication, messages and schedules as separately scoped side effects. A new convention is not blanket permission to move old notes.

## Augmented practice

Use the conventions reference's **Our augmentation layer** for each support folder's purpose, workflow and boundary. Inspect the current folder README, relevant templates and private local conventions before changing an established lane. Do not infer a routing policy or a plugin owner merely from an existing root name.

- **Inbox:** capture and traceable routing, including established handover/study lanes. For the study workflow, consolidate and verify durable knowledge before changing the processed source from `raw` to `filed`; preserve its source/destination trail.
- **Meta:** the system's operating manual, managed mirror boundaries and private local scope; not general domain content.
- **People:** shared relationship entities across projects; event evidence and live process state stay with their actual owners.
- **Maps:** curated reading paths, not duplicated content/status. Keep project/course indexes in their owner folders and link them from broader maps.
- **Attachments:** linked assets and frozen exports; preserve originals and classify by purpose, not extension alone.
- **Templates:** reusable skeletons at the configured `Templates/` path; completed notes go to their owner/capture lane. Template changes never rewrite existing notes implicitly.
- **Tags:** ordinary labels use tags/properties. An existing `Tags/` tree is not a new filing category; identify its consumers before any authorized cleanup.

Creating a convention or updating the governance mirror is not permission to drain Inbox, migrate notes, archive people, regenerate originals, change plugin configuration or delete empty-looking folders. The lifecycle reference gives the end-to-end study and event examples.

## PARA completeness

All four PARA categories are already part of this model. "Lightweight" is about keeping maintenance small, not omitting a category. Use the lifecycle reference to improve project outcomes, Area standards, reviews, lesson extraction and deliberate archiving before adding folder complexity. Suggested reviews do not authorize reminders or automatic archiving.

## Deterministic governance sync

[Reviewed sync script](scripts/sync_vault.py) runs without an LLM, third-party Python packages or model credentials. Its default private configuration is `~/.config/knowledge-base-sync/config.json`; use `--config` for another explicit path.

[Reviewed cron entry point](scripts/cron_entry.py) belongs as a regular file in the Hermes profile's `scripts` directory; the scheduler refuses entry points outside that sandbox. It invokes the installed skill with a bounded process lifetime. The sync uses POSIX locking and is supported on macOS/Linux.

The script pulls public Markdown from a single resolved upstream commit into locally allowlisted `00_meta` destinations only. It verifies hashes, detects local edits/deletions, journals verified progress, excludes concurrent runs and never deletes notes, uploads private data, executes downloaded code or falls back to filesystem vault writes.

Run a dry-run before the first application; follow the sync reference for configuration, installation, recovery and scheduling. Use the actual installed script path discovered by the skill tool. Do not assume a clone exists or copy a command from another agent's installation path. Schedule only on explicit request; local TUI jobs do not provide live chat notifications.

## Updating this skill

Edit the canonical source repository, regenerate its manifest, commit, export the complete pinned bundle into `fabzter/agent-skills`, commit/push that bundle, then reinstall from GitHub. Never hand-edit installed reference copies and call that an upstream update. The lock file and public verifier expose drift.

## Pitfalls

- A Git submodule is not an installed reference bundle. These references are real vendored files, hash-checked against an immutable commit.
- A stale bundled copy is a declared fallback, not automatically the current vault policy.
- Global public examples do not override private account boundaries or explicit user instructions.
- Success exit codes alone do not prove native note persistence or skill replacement. Verify exact content and source provenance.
- Never overwrite unreadable originals. A failed native CLI prerequisite is not permission to change permissions or switch accounts.
- Public repositories must contain only generic documentation, code and examples; private settings, source conversations and vault data stay local.

## Verification

- Load this installed skill and its linked references; confirm the GitHub source and lock revision.
- Verify the explicit named vault/path, governance index and private local scope.
- For note changes, verify the full intended path/content and relevant links.
- For a sync, inspect its exit status, private health state and generated revision status, then confirm a repeated healthy run is a silent no-op.
