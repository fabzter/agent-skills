---
type: system
status: active
version: 1.0.0
managed: knowledge-base-conventions
---

# Knowledge Base Conventions

## Scope and intent

This is a PARA-centered personal knowledge base for execution, ongoing responsibilities and reusable knowledge. It is intentionally readable as plain Markdown. Folder names are an implementation, not a claim that one taxonomy suits every person.

Operate only on the vault and accounts explicitly authorized for the task. Never switch to another account because a read failed. Do not apply personal-vault conventions to an organization's vault without authorization.

Read [[00_meta/Local Vault Conventions]] when present. It identifies local scope and additional domain rules; it is private and outside the public sync allowlist. If rules conflict, surface the conflict rather than silently choosing a more permissive rule.

## Filing model

| Home | Meaning | Typical content |
| --- | --- | --- |
| `00_inbox/` | Temporary, unclassified capture | Fleeting notes, raw imports, unprocessed source material |
| `00_meta/` | Infrastructure for this vault | Conventions, research behind the system, maintenance, templates and private local settings |
| `01_projects/` | An active effort with an observable outcome or endpoint | A job search, a specific application process, a renovation, a research deliverable |
| `02_areas/` | An ongoing responsibility with a standard to maintain | Career development, health, home, finances, relationships |
| `03_resources/` | General reference or an interest not currently owned by an active outcome | Technical concepts, methods, reading notes, course knowledge |
| `04_archive/` | Inactive material from Projects, Areas or Resources | Finished or paused projects, retired responsibilities, inactive reference collections |
| `05_people/` | Optional people-centered retrieval | Contact context and relationship notes linked to projects/areas |
| `06_maps/` | Optional navigation | Maps of Content, indexes, dashboards and cross-domain reading paths |
| `99_attachments/` | Binary assets | Images, PDFs, exports and documents linked from notes |

The four PARA categories are Projects, Areas, Resources and Archives. The other folders and their numeric prefixes are local implementation choices, not additional PARA requirements. Do not create empty subfolder trees in anticipation of hypothetical work.

### Decision order

1. Is the note about the knowledge system itself? Use `00_meta`.
2. Is it a people record or a binary asset? Use the relevant optional retrieval/attachment home and link it to the actual project or area.
3. Does an active outcome own this information? Use that project.
4. Does maintaining an ongoing responsibility own it? Use that area.
5. Is it general knowledge or reference? Use Resources.
6. Has it become inactive? Archive it, subject to the owner's migration approval.
7. Is its purpose still unclear? Capture it temporarily in Inbox.

When both a Project and an Area are relevant, file with the active outcome and link from the Area. Reusable does not automatically mean Resources: personal career narratives and observed interview lessons can belong to the ongoing Career Area; a general interviewing method belongs in Resources.

## Project and company ownership

An existing umbrella such as `01_projects/career/` can organize a finite job-search effort. A company-specific process lives beneath its own company home, for example `01_projects/career/<Company>/`. Do not put another company's material beneath that home, either in the vault or in temporary working files.

A multi-company working directory should use a neutral parent with separate company children. The working directory is staging; it is not a second knowledge base. Publish durable results to the correct vault owner and link supporting reusable notes rather than duplicating them.

Keep project artifacts distinct:

- A tracker is the operational process-status authority.
- A preparation brief preserves the context used to prepare for an event. Do not rewrite it into a status tracker after the event.
- A debrief records the event, observations, evidence, learning and next actions, with source limits and dates.
- New information belongs in an explicit update or successor, not a silent rewrite of historical evidence.
- Raw/confidential source and sanitized reusable material have separate audiences and links.

## Folders, links, maps, tags and properties

- Folders answer **where this note is filed**. Choose one primary owner.
- Wikilinks answer **what it relates to**. Prefer exact vault-relative targets when basenames repeat.
- Maps/indexes answer **where to start and what to read next**. They link rather than copy entire notes.
- Tags answer **which cross-cutting type or state applies**. Keep vocabulary small; do not reproduce the folder tree as tags.
- Properties answer **what structured facts can be queried**. Add fields only when they help retrieval or a real workflow.

Prefer shallow folders: normally one or two meaningful levels beneath a PARA category. A company beneath an existing career umbrella is a justified ownership boundary, not a violation to fix. Additional nesting requires a retrieval reason; use links or an index instead of folders for every date, status and note type.

Check link targets against actual files. A similarly named note, a space/underscore difference or a basename-only match is not proof that the link resolves to the intended owner.

## Note shape and naming

Use human-readable stable titles. Follow the neighboring notes' naming convention; do not mass-rename existing content for style consistency. For new dated events, use an unambiguous `YYYY-MM-DD` date in the established prefix or suffix position.

Use frontmatter when it materially helps, such as:

```yaml
---
type: project
status: active
area: career
company: Example Company
---
```

Other useful properties include `date`, `source`, `project`, `role`, `confidential` and stable story IDs. Preserve existing field names and IDs. A new metadata schema is not permission to rewrite the vault.

Aim for one coherent durable idea per reusable note, not an arbitrary word limit. A brief, transcript or evidence record can reasonably be long. Keep source material distinguishable from interpretation; cite source URLs or exact source notes and label inference and uncertainty.

## Attachments, originals and historical evidence

Link binary assets from their owning notes. Do not move legacy assets or rewrite attachment links without a preservation plan. Preserve hand-edited originals and external evidence. Back up before transformations; never regenerate a manually edited source merely to simplify automation.

Archive inactive material rather than deleting it. Preserve provenance and reading paths; do not casually move evidence subject to legal, retention or project-specific constraints. An archive move needs the same authorization and link verification as any other migration.

## Editing discipline

1. Read current notes and the exact local scope before proposing changes.
2. Use the official Obsidian CLI for supported note operations, targeting an explicit vault and exact path.
3. Preserve existing content, metadata, source limits and neighboring conventions.
4. Never overwrite a note whose original content cannot be read.
5. Verify a write through exact native readback. An exit code alone is not persistence evidence.
6. Compare on-disk bytes as an independent check when accessible. If macOS denies direct file access but native readback is complete, report that verification limit; do not change permissions or repeat the write blindly.
7. Prefer link-aware moves. If the CLI cannot safely express an authorized migration, explain the limitation before a filesystem fallback and verify preservation afterwards.
8. Do not commit, publish, message, schedule or migrate content outside the explicit task scope.

The governance sync is narrower than general note editing: it never falls back to filesystem vault writes and never reorganizes content. See [[00_meta/Knowledge Base Sync]].

## Privacy

Only generic conventions, public research sources and generalized examples belong in the public repositories. Never export private vault content, personal account identifiers, home paths, job-search details, conversations, financial/legal information or credentials as part of a skill bundle.

Sync is one-way from the public source to allowlisted governance notes. Local vault changes are never automatically committed or uploaded. The private local-conventions note and private sync configuration are intentionally not source-repository artifacts.
