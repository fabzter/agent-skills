# Upstream LadybugDB issues + where the flock guard actually lives

Captured 2026-09-28. Both halves answer the same question a diagnosing agent asks too late:
*"is this my process hygiene, or a known engine bug?"* — it is usually the engine.

## Part 1 — The crash signatures are already filed, by Fabz himself

Fabz is a **contributor** to `LadybugDB/ladybug`, not merely a user. He filed and personally
symbolicated several of the exact signatures this skill treats as local mysteries. Cite the issue
number in any diagnosis that matches; do not write a fresh theory.

| Issue | Signature | Relevance to Hermes |
| --- | --- | --- |
| **#840** | SIGSEGV/SIGBUS, null-pointer `memmove` under `NodeTableScanState::scanNext` → `ColumnChunk::scan` → `StringVector::reserveString` (0.19.1, Python, darwin-arm64) | **The teardown-SIGBUS shape.** His symbolication: a writer committing/checkpointing while a background scan copies an out-of-line string (>13 chars); visibility/version state is released *before* the copy loop, so nothing pins the buffer and the destination is NULL. **Corollary he proved: read-only repro attempts always come back negative** — the missing ingredient is a concurrent writer. A negative repro is NOT evidence against the bug |
| **#843** | Durable on-disk corruption: one 8-byte page-list header overwritten with a float32, DB unopenable (0.19.1, macOS arm64) | Explains a DB that will not reopen at all, with no `.wal` involved |
| **#940** | Heap corruption / SIGSEGV on insert + `CHECKPOINT` into a node table with an HNSW index (0.20.2 and main; **0.19.1 clean**) | **Directly implicates the WAL-salvage `CHECKPOINT` step.** If the engine is newer than 0.19.1, the salvage itself can be the corruption source — check the version before blaming your own repair |
| **#948** | Bad page index reaches the write path; file left at 892 GiB *apparent* size (sparse), silently exhausting disk on any copy/backup | Why `cp -p` of a "12 MB" DB can fill a disk. Check apparent vs. real size before backing up |
| **#957 / #958** | IceDisk relation-table data race; ALP `fix(alp): bound the encodable range and the sentinel by ENCODED_TYPE` | The ALP encoding issue was handed to Fabz by the maintainer (see below) |
| **#879** | "Fix ASAN bugs" — **closed as completed 2026-09-28**, "Passes now" | Sanitizer fixes landed upstream. Check whether the installed `ladybug` predates them before treating a crash as environmental |

Maintainers: **`adsharma`** (Arun Sharma, Ladybug Memory Inc) and **`Saiteja64`**. In #879
Saiteja64 wrote: *"@fabzter Thanks for digging into this… Feel free to take the ALP encoding issue
you found — that one wasn't on my radar before your report."* He is collaborating with them.

**Fastest route to this context:** `gog gmail search "ladybug" --account=faboster@gmail.com` —
the GitHub notification mail carries the full symbolicated analysis inline. Related repos of his:
`fabzter/ladybug` (fork) and `fabzter/ladybug-948-repro` (content-scrubbed reproducer DB for #948).

## Part 2 — Where the flock single-writer guard actually lives

`~/.hermes/plugins/ladybug` is a git clone with **two remotes**, and they disagree:

| Remote | Repo | HEAD | Guard present? |
| --- | --- | --- | --- |
| `origin` | `Ladybug-Memory/hermes-memory-plugin` | `087d793` "Restructure repo layout to match templates" | ❌ **no** |
| `fork` | `fabzter/hermes-memory-plugin` | `1d5b73b` "Restore fcntl.flock single-writer guard" | ✅ **yes** (pushed 2026-09-28) |

**Upstream never took it.** `Ladybug-Memory/hermes-memory-plugin` **PR #3 — "Add cross-process
single-writer flock guard around Ladybug DB open" — is CLOSED, not merged.** Read the closure
thread before re-pitching the same change; Arun Sharma closed it deliberately.

Consequence that bites silently:

```bash
hermes plugins update ladybug      # pulls origin -> the guard VANISHES, no warning
grep -c flock ~/.hermes/plugins/ladybug/__init__.py   # 0 == guard gone
```

Restore:

```bash
git -C ~/.hermes/plugins/ladybug pull fork main
grep -c flock ~/.hermes/plugins/ladybug/__init__.py   # expect > 0
git -C ~/.hermes/plugins/ladybug log --oneline -2      # expect 1d5b73b on top
```

## Part 3 — This skill is local-only (provenance gap)

`hermes-ladybug-memory` exists in **no repo**. Verified 2026-09-28 by checking:
all 15 `Ladybug-Memory` org repos · `adsharma/hermes-agent` branch `feature/ladybug-memory-plugin`
(carries the *plugin* at `plugins/memory/ladybug/`, not the skill) · `NousResearch/hermes-agent`
upstream · GitHub code search for distinctive phrases (`hermes-ladybug-memory`, `hermes-writer.lock`,
"Ladybug is Hermes's graph-memory store") — all empty. `hermes skills list` reports source `local`.

So an upgrade that rewrites `~/.hermes/skills/` loses this file with no trace, exactly as upgrades
have already eaten the flock guard twice. Candidate for adoption into `fabzter/agent-skills`
(see the `hermes-skill-repos` skill for the repo-first workflow).
