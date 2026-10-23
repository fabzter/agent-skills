---
type: system
status: active
version: 1.1.0
managed: knowledge-base-conventions
---

# Knowledge Base Governance

This folder explains how this knowledge base works. You should not need an agent's private memory or a particular note-taking plugin to understand the system.

## Start here

1. [[00_meta/Knowledge Base Conventions|Conventions]] — filing decisions plus our augmentation layer: Inbox, Meta, People, Maps, Attachments, Templates and existing Tags boundaries; each has a purpose, workflow and limits.
2. [[00_meta/Knowledge Base Research and Decisions|Research and decisions]] — source material, rationale and the distinction between evidence and local choices.
3. [[00_meta/Knowledge Base Lifecycle|Lifecycle]] — capture, active work, reviews, knowledge extraction and archiving, including the study-session and event-to-project working loops.
4. [[00_meta/Knowledge Base Sync|Sync and maintenance]] — canonical source, snapshots, update procedure and conflict recovery.
5. [[00_meta/Knowledge Base Sync Status|Installed revision and sync status]] — generated locally; not part of the public source repository.
6. [[00_meta/Local Vault Conventions|Local vault conventions]] — private account/scope settings and additional project-specific rules, if the vault owner creates this note. Never synchronized to the public repository.

## Authority and copies

The public, version-controlled source is [fabzter/knowledge-base-conventions](https://github.com/fabzter/knowledge-base-conventions). These managed Markdown notes are a complete local mirror, not merely links to an external website. The public `personal-vault-para` skill also ships a complete, commit-pinned reference snapshot.

One authoring source, several readable copies. Copies are useful; untraceable independent authoring is not.

- Change shared rules in the source repository, review them and merge them there.
- The deterministic sync updates only explicitly approved managed notes under `00_meta`.
- Local changes to a managed note stop synchronization rather than being overwritten.
- Private/local conventions live in the separate unmanaged note and never get pushed upstream automatically.
- The installed skill's snapshot can legitimately be older than this vault mirror. Its revision is recorded; agents read current vault governance before relying on an older offline snapshot.
- A user request or a local rule that conflicts with a shared convention needs an explicit resolution. A public example is never permission to expand account access or perform a migration.

## What this system is

PARA supplies the four filing categories: Projects, Areas, Resources and Archives. Inbox, Meta, People, Maps, Attachments and the configured Templates folder form our support layer. An existing Tags tree does not introduce another content category. These are implementation choices; there is no separate official "full PARA" folder tier to unlock.

The lifecycle makes the folders useful. It does not authorize an automatic reorganization of existing content.
