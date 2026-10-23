---
type: system
status: active
version: 1.1.0
research_origin: 2026-07-31
reviewed: 2026-10-23
managed: knowledge-base-conventions
---

# Knowledge Base Research and Decisions

## Provenance and limits

The initial research behind this model was recorded on 2026-07-31. This public document preserves its sources and reasoning while removing personal account, employer and conversation details. Private origin/context belongs in the vault's unmanaged local-conventions note, not in a public skill.

The official PARA article and the primary Obsidian discussions on folders/links/properties were re-read on 2026-10-23. Other links below are retained as original research references unless explicitly described otherwise.

The original synthesis used language such as "strong consensus." That is stronger than these sources warrant: forum threads are opinionated community examples, not a representative study. This version distinguishes the official PARA definition, recurring recommendations, alternatives and this implementation's own decisions.

## Findings by source

### 1. Official PARA: organize by actionability

[Tiago Forte — The PARA Method](https://fortelabs.com/blog/para/)

The official explanation defines four categories:

- Projects: efforts with a goal and an endpoint.
- Areas: ongoing responsibilities requiring attention/standards.
- Resources: topics and interests useful for future reference.
- Archives: inactive material from the previous categories.

Its central argument is to organize around current projects and goals rather than only broad academic subjects. Simplicity is intentional. The article does not define a separate "light" and "full" folder hierarchy.

**Decision here:** retain all four categories. Use clear project outcomes and a sustainable lifecycle instead of adding taxonomy layers to demonstrate completeness.

### 2. Obsidian: folders versus links and tags

[Folders vs. linking vs. tags — the definitive guide](https://forum.obsidian.md/t/folders-vs-linking-vs-tags-the-definitive-guide-extremely-short-read-this/78468)

The author favors project folders for deliverable-oriented work and minimal folders plus links for personal knowledge work. The post also expresses a strong personal preference against tags. It is a useful workflow argument, not a universal rule or a reason to prohibit tags for everybody.

**Decision here:** use folders for primary ownership, links for relationships, and a small intentional tag vocabulary when it solves a real problem. Do not adopt another author's preferences as mandatory law.

### 3. Obsidian: different tools solve different retrieval problems

[An opinionated reflection on folders, links, tags and properties](https://forum.obsidian.md/t/an-opinionated-reflection-on-using-folders-links-tags-and-properties/78548)

The author explicitly calls the post opinionated, explores file types, links, metadata and note forms, and does not prescribe this vault's particular tree. It demonstrates that links, folders, tags and properties are not interchangeable.

**Decision here:** assign each mechanism a purpose. Folders hold one primary filing location; links connect contexts; maps provide reading paths; properties support actual queries. Avoid duplicating the whole hierarchy in tags.

### 4. Shallow and stable folders

[The Strategy of Note Taking: Folders, Tags, Links and Redundancy](https://forum.obsidian.md/t/the-strategy-of-note-taking-folders-tags-links-and-redundancy/99402)

Retained from the initial research as a community discussion of filing, links and redundancy. Depth limits such as two or three levels are practical heuristics, not formal PARA requirements or a scientifically established Obsidian consensus.

**Decision here:** prefer shallow ownership boundaries, but do not flatten a useful company/project boundary merely to satisfy an arbitrary level count. Add a map or link before adding nesting.

### 5. Johnny.Decimal: a different organizing model

[Johnny.Decimal introduction](https://johnnydecimal.com/documentation/introduction)

[Saving files in ID folders](https://johnnydecimal.com/documentation/saving-files)

Johnny.Decimal uses stable numerical Areas, Categories and IDs. Its introduction emphasizes constraints, stable locations and quick retrieval. This differs from PARA's emphasis on current actionability and material becoming inactive.

**Decision here:** do not layer a full ID taxonomy onto the existing PARA tree without a demonstrated need and explicit migration approval. This is a choice for this implementation, not a claim that Johnny.Decimal is inferior or cannot be combined deliberately with other methods.

### 6. Zettelkasten: writing and connecting knowledge

[Building a Zettelkasten with Obsidian, with a side of PARA](https://sonim1.com/en/blog/obsidian-zettelkasten-with-para)

Retained from the initial research as an example of combining action-oriented filing with connected notes. The two approaches address different needs: where information supports current work, and how explanations/ideas connect.

**Decision here:** use focused durable notes, explicit links and separate source from interpretation. Do not impose a pure Zettelkasten taxonomy on every transcript, brief, project tracker or evidence record.

### 7. Obsidian examples are diverse

[2023 Gems of the Year winners](https://obsidian.md/blog/2023-goty-winners/)

[2022 Obsidian October winners](https://obsidian.md/blog/2022-obsidian-october-winners/)

These original references illustrate a diversity of community workflows and resources. They are not evidence that Obsidian prescribes one canonical vault tree.

**Decision here:** judge structure by useful retrieval and continued use, not by resemblance to a fashionable template.

## Adopted decisions

### D1 — PARA is the core filing model

Use Projects, Areas, Resources and Archives. Rejected for this implementation: copying a work-operations tree wholesale, deep subject taxonomies, tags-only filing, or removing execution-oriented categories to impose a pure note-linking system.

### D2 — Support folders are implementation conveniences

Inbox, Meta, People, Maps and Attachments make capture, self-documentation and retrieval practical. A configured Templates folder supports repeatable note creation. Numeric prefixes stabilize sidebar ordering where already used; they do not justify renaming a configured unprefixed folder. These are not additional official PARA categories.

### D3 — Completeness means lifecycle, not more folders

The four PARA categories are already present. Add clearer outcomes, next actions, Area standards, purposeful reviews, lesson extraction and deliberate archiving. The suggested review cadence is a local operational convention, not an official requirement or an automatically created reminder.

### D4 — Self-contained governance, traceable copies

Keep the complete rules, research and maintenance guidance in the vault AND in the installed public skill. GitHub is the common authoring source. Every generated skill snapshot records its source commit and file hashes; the vault status records the upstream revision actually applied.

### D5 — Use a pinned vendor snapshot, not a runtime submodule

The skill lives in the existing public skill collection; the documentation lives in its own public repository. A normal skill installer must receive real support files without having to perform a recursive Git checkout. A submodule would add a separate dependency-resolution step and can appear only as a gitlink to installers that fetch repository files rather than clone recursively.

A deterministic exporter copies the complete declared bundle from one committed source revision. Verification checks the copy against that pinned revision. The installed snapshot is a release/fallback and may lag the current vault mirror; that difference is explicit, not silent drift. Update the skill from its public repository, not by hand-patching the installed copy.

### D6 — Pull Markdown, never upload private notes

The scheduled sync resolves one upstream commit, validates an allowlisted/hash-checked Markdown payload, then writes through the explicitly named native Obsidian CLI. It never runs freshly downloaded code, pushes vault changes, deletes notes or expands scope from a remote manifest.

Local edits to managed notes are conflicts requiring review. Private local conventions remain unmanaged and never become public implicitly.

### D7 — An explicit augmentation layer

Document each adopted support folder's purpose, working loop and boundary rather than merely naming it in a tree. This is an implementation decision informed by the existing capture, study, relationship and navigation workflows, not a claim that external PARA research prescribes these roots.

- Inbox is intake and continuity; processing is traceable and does not imply source deletion.
- Meta contains the operating manual and private scope, not domain/project content.
- People records persist across projects; a company/event still owns its own evidence and status.
- Maps curate reading paths; owner-specific indexes remain with their owners and trackers remain authoritative.
- Attachments hold assets/frozen exports; preserve existing originals and classify by purpose, not extension alone.
- `Templates/` stays at its configured path; a reusable skeleton and a completed note have different homes.
- An existing `Tags/` tree is not automatically a routing category or evidence of a particular plugin. Labels belong in meaningful tags/properties; investigate consumers before any cleanup.

Use the lifecycle's capture-to-consolidation examples to explain how these choices work together. Adopting documentation does not authorize a content migration, index relocation, source purge, plugin reconfiguration or new schedule.

## Review triggers

Revisit the structure when recurring retrieval failures, ambiguous ownership or a real workflow change justify it. Revisit the publishing/sync design if compatibility, threat model or maintenance requirements change. Do not reorganize merely because a different productivity system becomes fashionable.

See [[00_meta/Knowledge Base Conventions]], [[00_meta/Knowledge Base Lifecycle]] and [[00_meta/Knowledge Base Sync]].
