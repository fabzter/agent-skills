---
type: system
status: active
version: 1.1.0
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
| `00_meta/` | Infrastructure for this vault | Conventions, research behind the system, maintenance, template guidance and private local settings |
| `01_projects/` | An active effort with an observable outcome or endpoint | A job search, a specific application process, a renovation, a research deliverable |
| `02_areas/` | An ongoing responsibility with a standard to maintain | Career development, health, home, finances, relationships |
| `03_resources/` | General reference or an interest not currently owned by an active outcome | Technical concepts, methods, reading notes, course knowledge |
| `04_archive/` | Inactive material from Projects, Areas or Resources | Finished or paused projects, retired responsibilities, inactive reference collections |
| `05_people/` | Optional people-centered retrieval | Contact context and relationship notes linked to projects/areas |
| `06_maps/` | Optional navigation | Maps of Content, indexes, dashboards and cross-domain reading paths |
| `99_attachments/` | Assets and preserved source exports | Images, PDFs, recordings and frozen exports linked from owning notes |
| `Templates/` | Configured reusable note skeletons | Capture and course-index templates, not completed notes |
| `Tags/` when already present | Existing compatibility surface, not a filing category | Preserve until its origin and consumers are understood; do not route new content here |

The four PARA categories are Projects, Areas, Resources and Archives. The other folders and their numeric prefixes are local implementation choices, not additional PARA requirements. Do not create empty subfolder trees in anticipation of hypothetical work.

### Decision order

1. Is the note about the knowledge system itself? Use `00_meta`.
2. Is it a reusable note skeleton? Use the configured template folder, here `Templates/`.
3. Is it primarily navigation? Keep an owner-specific index with that owner; use `06_maps/` for a cross-context entry point.
4. Is it a person/relationship record or an imported asset? Use the relevant retrieval/attachment home and link it to the actual project or area. Merely mentioning a person does not make a project note a people record.
5. Does an active outcome own this information? Use that project.
6. Does maintaining an ongoing responsibility own it? Use that area.
7. Is it general knowledge or reference? Use Resources.
8. Has it become inactive? Archive it, subject to the owner's migration approval.
9. Is its purpose still unclear? Capture it temporarily in Inbox.

When both a Project and an Area are relevant, file with the active outcome and link from the Area. Reusable does not automatically mean Resources: personal career narratives and observed interview lessons can belong to the ongoing Career Area; a general interviewing method belongs in Resources.

## Our augmentation layer

PARA provides the actionability model. The folders below add capture, governance, entity retrieval, navigation and assets. These are this implementation's explicit working conventions, not additional official PARA categories. Inspect an existing folder's README and local conventions before changing its workflow. Do not create all of these roots in a different vault merely to match this example.

### `00_inbox/` — Capture and routing

- **Purpose:** Hold unprocessed captures and imports without requiring a filing decision during capture.
- **Workflow:** Record enough source/date/context to recover meaning. During an explicitly requested debrief or review, identify the owning Project, Area, Resource or person record; consolidate useful knowledge there, verify it, and leave a traceable destination on the source. Use the owner directly when it is already clear. Keep established lanes such as study or document intake distinct.
- **Boundary:** A raw source is not a finished lesson or a second task tracker. Processing a capture does not authorize deleting it. A handover may remain here as a continuity pointer under local convention; it points to authoritative notes rather than becoming another status authority. A useful queue matters more than a cosmetically empty folder.

### `00_meta/` — The system's operating manual

- **Purpose:** Explain the knowledge system itself: conventions, research/decisions, maintenance, automation health and local operating scope.
- **Workflow:** Start at its README. Author shared rules in the canonical repository and mirror the approved files; keep private scope and domain exceptions in the unmanaged local-conventions note. Document where templates and automation live instead of silently relocating them.
- **Boundary:** This is not a catch-all for domain knowledge, project delivery or exported credentials. Generated status describes its stated verification scope, not every automation's present health. Do not hand-edit managed mirrors or assume all files in Meta are sync-managed.

### `05_people/` — Durable relationship context

- **Purpose:** Give a person one discoverable entity home across projects, employers and events.
- **Workflow:** Check identity and existing aliases before creating another record. Use a stable human-readable name, adding context only to distinguish collisions. Record relevant relationship/role context with dates and sources, and link the person from the projects, meetings and Areas where the relationship matters.
- **Boundary:** Event evidence and company-process status remain with their Project/Area; link them rather than copying a whole dossier into the person note. A project closing does not end the relationship or authorize archiving the person. Store only necessary private details; never infer identity or personal facts from similar names.

### `06_maps/` — Curated reading paths

- **Purpose:** Provide Maps of Content (MOCs): human-readable entry points across several owners or topics.
- **Workflow:** Link important starting notes with short descriptions and a useful reading order. Keep an individual project's or course's own index in its owner folder; link that index from a broader map when it improves discovery. Update the relevant path when adding durable knowledge, not every map in the vault.
- **Boundary:** A map is navigation, not another copy of its linked material or another operational tracker. It need not list every file. Do not move all README/index/MOC notes into Maps or duplicate live status that already has an authoritative owner.

### `99_attachments/` — Assets and frozen source material

- **Purpose:** Keep reusable media, binary documents and preserved exports discoverable from their owning notes.
- **Workflow:** Link each useful asset from its Project, Area or Resource and record origin/date where material. A shallow project grouping is reasonable when it prevents filename collisions. Keep the original distinguishable from an edited derivative; preserve the relevant revision and source link.
- **Boundary:** Classify by purpose, not extension alone: a frozen export may be Markdown, while a new authored explanation belongs with its knowledge owner. Do not move existing binaries, working originals or externally authoritative documents just for uniformity. Do not delete an asset based only on a missing backlink; retention, privacy and link checks need their own approved scope.

### `Templates/` — Reusable note shapes

- **Purpose:** Supply the starting structure for a repeatable note type without storing the resulting work.
- **Workflow:** Keep the actual folder path configured for the user's template tooling. Choose a template, instantiate a new note in its real owner/capture lane, and fill in the source and routing fields. Maintain common headings/metadata when a repeated workflow genuinely needs them; keep optional sections optional.
- **Boundary:** Completed session notes and course indexes do not live here. Updating a template does not retroactively rewrite existing notes. Unprefixed naming is not a reason to rename this configured folder, move templates into Meta, change a plugin, or make the knowledge base depend on that plugin to be readable.

### `Tags/` — An existing root is not a new category

- **Purpose:** Preserve an already-existing Tags tree without treating its presence as a new knowledge-filing policy. Its origin or consumers may need separate investigation.
- **Workflow:** For ordinary semantic labels, use a small frontmatter/inline tag vocabulary or meaningful properties, independent of folder location. If the existing Tags tree needs maintenance, first identify its actual files, references and any tooling dependency.
- **Boundary:** Do not create one folder/note per tag, move content here because it has a label, or infer a plugin owner from the directory name. No indexed notes is not proof that deleting the tree is safe. Cleanup or migration requires an explicit preservation decision.

App settings, caches and hidden tooling directories are configuration surfaces, not extra knowledge categories. Leave them alone unless changing that specific integration is part of the authorized task.

The working loop is **capture -> consolidate under one PARA owner -> connect people/assets -> expose a useful reading path -> review or archive deliberately**. Templates shape capture; Meta explains the rules. See [[00_meta/Knowledge Base Lifecycle]] for the end-to-end examples.

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
