---
name: ladybug-memory-runbook
description: Diagnose and repair Ladybug graph-memory failures — "Ladybug database is not initialised", corrupt WAL, SIGBUS crashes, and multi-process single-writer corruption. Agent-neutral runbook (written on a Hermes host; procedures apply to any agent embedding LadybugMemory/lbug).
tags: [ladybug, ladybugdb, memory, crash, sigbus, wal, corruption, not-initialised, single-writer, flock, troubleshooting, runbook]
---

# Ladybug Memory Runbook

Ladybug is Hermes's graph-memory store behind the `ladybug_search` / `ladybug_recall` / `ladybug_store` / `ladybug_update` tools. This skill covers its failure modes and repair. **Do not confuse Ladybug with the plaintext memory stores** (`MEMORY.md` / `USER.md`, injected every turn, managed by the `memory` tool) — they are completely separate; Ladybug corruption does not touch MEMORY.md.

> **Before diagnosing any crash or corruption, read `references/upstream-issues-and-guard-provenance.md`.** It establishes that these signatures are **known upstream engine bugs that Fabz himself filed** (`LadybugDB/ladybug` #840 / #843 / #940 / #948 / #879), and it records **where the flock guard actually lives** (`fork` remote, not `origin`) so an update does not silently delete it. Citing the issue number beats inventing a new root-cause theory every time.

## What Ladybug is (durable facts)

- Engine: **LadybugDB**, a Kùzu fork (`_lbug.cpython-311-darwin.so`). Not SQLite, not DuckDB — a custom graph DB.
- **Package names moved in the Aug 2026 upgrade.** Engine `real_ladybug 0.15.3` → import **`ladybug`** (dist `ladybug 0.19.1`); memory layer `ladybug-memory 0.1.7` → 0.1.8, imported as **`lbmemory`** (`from lbmemory import LadybugMemory`). Older notes saying `import real_ladybug` are stale — that name no longer resolves.
- **The plugin opens with `enable_entity_extraction=True`, which requires the `[extract]` extra** (`gliner2` + `transformers`). Without it, `LadybugMemory.__init__` raises `ImportError: Entity extraction requires the 'extract' extra` — `initialize()` swallows that into `_db = None`, so **every tool returns "not initialised"** while the file on disk is perfectly healthy. A distinct root cause from WAL corruption and from lock contention; check it first because it is a one-liner. Fix (the venv has **no `pip`** — use `uv`, and run it via `execute_code`+`subprocess` because a raw `uv pip install` line can trip the terminal lifecycle-guard null-byte crash):
  ```bash
  uv pip install --python ~/.hermes/hermes-agent/venv/bin/python "ladybug-memory[extract]"
  ```
  Expect a `gliner2` downgrade and a `transformers` major-version move — re-verify with a strict open afterwards. First store with extraction enabled downloads `microsoft/deberta-v3-base` from HF (unauthenticated = slow but works). Probe with `enable_entity_extraction=False` when you only need to read/write text and want to skip that download.
- DB file: `~/.hermes/ladybug.lbdb` (single file). Backup convention: `ladybug.lbdb.bak`.
- **Single-writer by design.** The `Database` docstring states it plainly: *"there cannot be multiple Database objects created with the same database path."* This is the #1 thing to remember.
- Plugin: `~/.hermes/plugins/ladybug/` (the Hermes-side integration that opens the DB). `~/.hermes/hermes-agent/plugins/memory/ladybug` is a **symlink to it** — same file, not a second copy; the runtime logger name is `plugins.memory.ladybug`.
- **0.19.1 also enforces single-writer in the engine itself**: a second opener gets `IO exception: Could not set lock on file` (see docs.ladybugdb.com/concurrency). That is a hard exception, not graceful degradation — the flock guard below still matters, and it is what turns that error into a clean MEMORY.md-only fallback.

## Failure signature: SIGBUS crash on large messages

Symptom: Hermes crashes with `Bus error: 10` / `EXC_BAD_ACCESS (SIGBUS)` when a large (~2KB+ multiline) message arrives. Short messages are fine. Crash reports land in `~/Library/Logs/DiagnosticReports/Python-*.ips`.

Recognize the signature in a `.ips` file: `"signal":"SIGBUS"`, `esr` = "Data Abort byte read Translation fault", faulting frame in `lbug::storage::NodeTableScanState::scanNext` ← `lbug::fts_extension::tableFunc` ← `lbug::common::TaskScheduler::runWorkerThread`, all in `_lbug.cpython-311-darwin.so` / `libfts.lbug_extension`.

**This is upstream issue #840 — filed and symbolicated by Fabz.** See the reference file for the full frame-by-frame analysis and the reason a read-only repro can never reproduce it (a concurrent writer is the missing ingredient). Quote the issue number rather than re-deriving it.

## Root cause: multi-process single-writer violation

Ladybug is single-writer, but every live Hermes process (gateway + CLI sessions + cron workers + any tmux bridge session) opens `ladybug.lbdb`. When one process rewrites/grows the file, the others' mmap regions go stale and the next FTS scan faults → SIGBUS.

Confirm in ~5 seconds:
```bash
lsof ~/.hermes/ladybug.lbdb   # >1 Python process holding it = the smoking gun
ls -la ~/.hermes/ladybug.lbdb*   # check for .wal; .bak is the older fallback
```

A `ladybug_store` returning nonsense like `duplicated primary key value <token>` (non-integer "keys") is the same corruption surfacing in the write path — stop writing to Ladybug until repaired.

## Failure signature: every tool returns "Ladybug database is not initialised."

Symptom (observed 2026-09-16): all `ladybug_*` tools return `{"error": "Ladybug database is not initialised."}` — yet `~/.hermes/ladybug.lbdb` exists (11.8 MB) with a stale `.wal` beside it, and `lsof` shows **no process holding the file at all**.

**Resolved 2026-09-16 — root cause was a corrupt `.wal`, and the DB itself was fine.** Full write-up in "Case study" below. Since the fix, this error string **carries its reason** (`... is not initialised. (open failed: ...)` / `(another Hermes process (pid N) already holds ...)`), so a bare reasonless string means you are on a Hermes process running pre-`1d5b73b` plugin code in memory — restart it before diagnosing anything else.

What the error actually means: the plugin's `initialize()` failed to open the DB and set `self._db = None`; `handle_tool_call` returns that exact string whenever `_db` is falsy (see `~/.hermes/plugins/ladybug/__init__.py`, `_db = None` assignments around L506–533, error string around L654). So the DB is not "missing" — the **open** raised an exception that got swallowed into the None fallback. Diagnosis path:

0. **Cheapest check first — is the `[extract]` extra installed?** The plugin's `initialize()` opens with `enable_entity_extraction=True`; a missing extra raises `ImportError` that lands in the same `_db = None` fallback as a corrupt WAL. One command settles it:
   ```python
   # execute_code + subprocess, hermes venv python
   from lbmemory import LadybugMemory
   LadybugMemory(path, enable_entity_extraction=True)   # ImportError => install ladybug-memory[extract]
   ```
   If a strict `enable_entity_extraction=False` open succeeds while the `True` open raises `ImportError`, that is the whole diagnosis — no WAL work, no process killing.
1. Find the real exception: plugin logger output / gateway logs from session start (`initialize()` logs "Ladybug opened at ..."; its absence plus any traceback above it is the smoking gun).
2. Check `lsof ~/.hermes/ladybug.lbdb` — empty means nobody holds it, so a fresh open attempt from a probe script is safe-ish (single open, from ONE process, never concurrent with the gateway retrying).
3. Check the flock guard is still present (`grep -n "flock" ~/.hermes/plugins/ladybug/__init__.py`) — a Hermes upgrade can rewrite the plugin; a missing guard correlates with repeat corruption (this host has 4+ dated `.corrupt-*`/`.badpage-*` backups). **Note the guard lives on the `fork` remote, not `origin` — `hermes plugins update` deletes it silently.** Restore steps in the reference file.
4. A stale `.wal` (mtime newer than the `.lbdb`) after an unclean shutdown is the **prime suspect, and was the actual cause on 2026-09-16** — WAL replay failure on open. Go straight to the WAL salvage in repair step 3; it is cheap and non-destructive. **Size is no guide:** the same error recurred on 2026-09-23 from a **5.8 KB** WAL sitting beside the 11.8 MB `.lbdb` (the 09-15 case had a 17 KB one). Any `.wal` newer than the DB is a suspect no matter how small.
5. Compare the live `.lbdb`/`.wal` against the dated `.corrupt-*` copies with `md5`. **Byte-identical means an earlier repair copied aside and then stopped** — the file has been frozen since that timestamp, so the outage is older than the newest backup suggests.

Host quirk while diagnosing: probe scripts that `import ladybug_memory` can trip the terminal lifecycle-guard "embedded null byte" crash — run probes via `execute_code` + `subprocess.run` (see `hermes-write-redaction-quirks` §2).

Escalation that worked on this host: hand the repair to a dedicated Claude Code bridge session (`claude-bridge open ladybugfix --cwd ~/.hermes`) with a brief containing symptoms + constraints (copy-aside before any destructive step, warn before booting out `ai.hermes.gateway`, don't touch MEMORY.md). It can iterate on the plugin/DB without occupying the Hermes session, and it knows the Kùzu/LadybugDB engine internals.

## The fix — a guard that upgrades keep deleting

A **cross-process `fcntl.flock(LOCK_EX|LOCK_NB)` single-writer guard**: the first process to acquire the lock opens the graph DB; all other processes degrade to MEMORY.md-only with a warning. It takes the lock on a sidecar `~/.hermes/ladybug.lbdb.hermes-writer.lock` (holding the pid), **not** on the DB file itself, so it cannot contend with the engine's own file lock. It also releases the lock on open failure, so a process that cannot open the DB does not block a healthy one.

**This guard has now been dropped twice by upgrades. Always verify it rather than assuming it shipped:**
```bash
grep -n "flock" ~/.hermes/plugins/ladybug/__init__.py
git -C ~/.hermes/plugins/ladybug log --oneline    # expect 1d5b73b
```

**But grep can FALSE-NEGATIVE (observed 2026-09-23):** `grep flock` returned 0 matches and git log showed only `087d793`, yet the guard was demonstrably ACTIVE — a degraded session's tool error read *"another Hermes process (pid 7051) already holds ~/.hermes/ladybug.lbdb; this session is MEMORY.md-only"*. Treat that error string as the authoritative behavioral proof the guard works; only conclude the guard is missing when BOTH the grep is empty AND a second process opens the DB without degrading (or you get the raw `IO exception: Could not set lock on file`).

**Degraded mode is NOT an outage.** If the error names another live pid as holder, the DB is healthy and the holder session has full access; your session is MEMORY.md-only by design. Do not attempt repair from a degraded session (you cannot take the writer lock anyway) and do not loop-retry `ladybug_store`. Park the fact in MEMORY.md/vault and tell the user it will land from the holder or a fresh session.

**Killing the holder does NOT heal the already-degraded session (confirmed 2026-09-28).** `handle_tool_call` has no lazy re-init — it is literally `if not self._db: return json.dumps({"error": ...})`. So after you kill the holder and `lsof` shows both the DB and the lock free, `ladybug_store` in *this* session **still fails and still prints the stale reason naming the now-dead pid.** Read that as "this process cached `_db = None` at startup", never as "the kill failed" and never as "the DB is corrupt". Only a session/gateway restart re-runs `initialize()`. Practical consequence: do not start the WAL-salvage procedure on a file that `lsof` + a strict out-of-process open have just proven healthy.

**Identifying a zombie holder:** `lsof ~/.hermes/ladybug.lbdb` gives the pid; `ps -p <pid> -o pid,ppid,lstart,etime,command` says what it is. On this host the holder was a **5-day-old `hermes --resume <session_id>`** parked in a herdr pane (`ppid` → `-zsh` → `herdr server`), not the live session — so a long `ELAPSED` plus a `--resume` cmdline is the zombie signature. It also owned a `tools/mcp_stdio_watchdog.py` child; **plain SIGTERM was ignored**, so `kill -9` the child and the holder, then confirm `lsof` is blank for **both** the `.lbdb` and the `.hermes-writer.lock`. Note that other `mcp_stdio_watchdog.py` processes belong to unrelated live sessions — kill only the one whose `--ppid` is your zombie.

**Writing from a degraded session anyway (works — do this instead of making the user wait):** with `lsof` empty, a single out-of-process `lbmemory` open is safe and can both verify and *write*. Run it via `execute_code` + `subprocess` with the hermes venv python:
```python
from lbmemory import LadybugMemory
m = LadybugMemory(os.path.expanduser("~/.hermes/ladybug.lbdb"), enable_entity_extraction=False)
entry = m.store(content="...", memory_type="project", importance=7)   # returns MemoryEntry with .id
m.close()   # ALWAYS close — a dangling opener blocks the next session's writer lock
```
Verify the write landed by **re-opening and searching**, and mind the result shape: `m.search(q)` returns `MemorySearchResult` objects whose text lives on **`.entry`** (a `MemoryEntry`), *not* on `.content` — reading `.content` yields empty strings and looks exactly like "readback 0 hits / the store failed" when the memory is in fact present. `m.get(<id>)` is the direct by-id check.
History: first shipped as `821217b`; the Aug 2026 upgrade **replaced the plugin repo wholesale** (leaving a single commit, `087d793 "Restructure repo layout to match templates"`, and no trace of 821217b) and the unguarded weeks that followed produced the 2026-09-10 WAL corruption. Re-shipped 2026-09-16 as **`1d5b73b`**.

If the repo history is short and `flock` greps empty, the guard is gone again and the multi-process corruption risk is live — treat that as a real finding, not cosmetic, and restore it from `1d5b73b` or from `~/.hermes/ladybug-plugin-__init__.py.pre-flock-*` diffs.

## Repair procedure (if the DB is corrupt)

Escalate in order, backing up first and never `rm` before a copy:

1. Back up: `cp -p ~/.hermes/ladybug.lbdb ~/.hermes/ladybug.lbdb.corrupt-$(date +%Y%m%d-%H%M%S)` (and copy `.bak` aside too). **Check apparent vs. real size first** — upstream #948 leaves a sparse file with a giant apparent size, and a naive `cp` can fill the disk.
2. Stop ALL hermes processes (not just the gateway — every holder must release the file):
   - `launchctl bootout gui/$(id -u)/ai.hermes.gateway`
   - `for pid in $(lsof -t ~/.hermes/ladybug.lbdb); do kill "$pid"; done`
   - Re-run `lsof` to confirm empty.
3. **WAL salvage — try this first; it fixed the 2026-09-16 outage with zero data loss.** Rehearse it on a copy in a scratch dir before touching the live file. Opening tolerantly replays the valid WAL prefix, and `CHECKPOINT` folds it into the DB and clears the corrupt WAL:
   ```python
   import ladybug
   db = ladybug.Database(path, throw_on_wal_replay_failure=False)   # strict default is what refuses to open
   conn = ladybug.Connection(db)
   conn.execute("MATCH (m:Memory) RETURN count(m)")                 # sanity-check the data survived
   conn.execute("CHECKPOINT")
   conn.close(); db.close()
   ```
   Then confirm it reopens **strictly**, the way the plugin does: `LadybugMemory(path, enable_entity_extraction=False)`. If that succeeds, you are done — skip step 4.
   A SIGBUS or a still-failing strict open routes you to step 4. **Caveat from upstream #940:** `CHECKPOINT` into a node table with an HNSW index heap-corrupts on 0.20.2/main (0.19.1 is clean) — if the engine is newer than 0.19.1, the salvage step itself may be the corruption source.
4. Fallback: restore `ladybug.lbdb.bak` (clean but older), or delete to recreate empty and re-seed from MEMORY.md.
5. Restart gateway: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist`.
6. Verify: `lsof ~/.hermes/ladybug.lbdb` shows exactly ONE process; then a `ladybug_search`/`ladybug_store` round-trip returns clean results (no SIGBUS, no duplicate-key garbage).

### Verifying a repair when your OWN session is still broken (2026-09-23)

The DB can be healthy on disk while the session you are sitting in still refuses writes. Do not
misread that as "the repair failed":

- `ladybug_store` keeps returning the **same** stale reason (`... Corrupted wal file ...`) after a
  successful salvage — because the plugin cached `_db = None` when that session started. What is
  broken now is the in-process flag, not the file.
- `~/.hermes/ladybug.lbdb.hermes-writer.lock` contains `pid NNNN` — the process that took the
  writer lock and then failed to open. Reading it tells you which live session is in the bad state.
- **Prove the file is fine out-of-process** (via `execute_code` + `subprocess`, hermes venv python —
  a bare `terminal` probe can trip the null-byte guard):
  ```python
  from lbmemory import LadybugMemory
  m = LadybugMemory(db_path, enable_entity_extraction=False)   # strict open
  m.search("some term")                                        # hits = data intact
  ```
  A strict open plus a search returning results = repair done; only a session restart remains. Also
  confirm the post-`CHECKPOINT` `.wal` is gone and the `.lbdb` mtime moved.
- Use the WAL salvage **without** stopping other processes when `lsof` is already empty — no need to
  `launchctl bootout` the gateway (and therefore no need to kill the session doing the repair).
- Do NOT restart the user's live session to "finish" the job, and do not retry `ladybug_store` in a
  loop. Park the durable facts in `MEMORY.md` (always injected) and tell the user the DB is repaired
  and will come back on the next session start.

## Case study: the 2026-09-10 → 09-16 outage

Worth reading once; it is the shape this failure takes end to end.

- **Trigger.** The Aug 20 upgrade replaced the plugin repo and dropped the `821217b` flock guard. Gateway + CLI + TUI sessions went back to opening the same single-writer file concurrently.
- **Break.** IO/bad-page faults on Aug 26–27, then on **2026-09-10 08:38** a half-written WAL: every open raised `Runtime exception: Corrupted wal file. Read out invalid WAL record type.` `initialize()` swallowed it into `_db = None` and all tools returned the bare "not initialised" string.
- **Why it looked stranger than it was.** `lsof` was empty — because *every* process's open had failed, nobody held the file. An empty `lsof` here means "nothing can open it", not "nothing is wrong".
- **Why it lasted six days.** A Sep 15 repair attempt copied the DB and WAL aside and stopped. `md5` showed the live files still byte-identical to those `*-20260915-141934` copies, so nothing had actually changed since. Always run that comparison.
- **Fix.** WAL salvage (repair step 3) recovered all 39 memories with no data loss; guard re-committed as `1d5b73b`; gateway restarted.
- **Gotcha on restart.** `launchctl bootstrap` immediately after `bootout` can fail with `Bootstrap failed: 5: Input/output error`. It is a race, not a broken plist (`plutil -lint` passes). Confirm the job is really gone (`launchctl print gui/$(id -u)/ai.hermes.gateway` → "Could not find service") and just retry.
- **Gotcha after restart.** Restarting the gateway does **not** fix already-running CLI/TUI sessions: they hold the pre-patch plugin in memory with `_db = None` and keep emitting the old error. Each needs its own restart. Also, the gateway opens the DB only when a session initializes, so an empty `lsof` right after a restart is expected, not a failure.

## Key separation (reduces panic during outages)

- `MEMORY.md` / `USER.md` (the `memory` tool) = plaintext, injected every turn, **independent of Ladybug**. Park critical facts there during a Ladybug outage; they survive.
- Ladybug (lbug DB) = secondary recall store, largely redundant with MEMORY.md for this user. Its loss is low-cost; MEMORY.md loss is high-cost.
- The gateway runs under launchd label `ai.hermes.gateway` (plist `~/Library/LaunchAgents/ai.hermes.gateway.plist`).

## Pitfalls

- **Do not diagnose in a vacuum — check upstream first.** Fabz filed #840/#843/#940/#948 and contributed to #879 (closed as completed 2026-09-28). Attributing a known engine bug to your own process hygiene produces a confident wrong root cause and wastes a session. See `references/upstream-issues-and-guard-provenance.md`; his Gmail is the fastest index (`gog gmail search "ladybug" --account=faboster@gmail.com`).
- **One-shot probe processes are themselves a WAL-corruption source (2026-09-28, 3x in one session).** `LadybugMemory` has **no `.close()` method** (AttributeError) — so a `python -c` script that stores via `lbmemory` and exits normally SIGBUS-es during interpreter teardown **with the DB still open**, leaving a corrupt `ladybug.lbdb.wal` behind even when the DB was pristine and single-held. Symptoms: store returns a valid id and reads back fine in-process, but the NEXT strict open anywhere raises `Corrupted wal file. Read out invalid WAL record type.` **Safe one-shot write pattern:** do the work, `sys.stdout.flush()`, then `os._exit(0)` (skips teardown entirely). If corruption already happened: engine-level `ladybug.Database(path, throw_on_wal_replay_failure=False)` → `CHECKPOINT` → verify strict open → confirm no live `.wal` remains. NOTE: writes inside a rolled-back corrupt WAL are LOST by the salvage (observed: a stored id 43 vanished); re-store after the DB is clean, and prefer parking the fact in MEMORY.md/vault first so it survives either outcome.
- **Stop after one failed write attempt — do not retry into a corrupting DB.** Observed 2026-09-28: three successive `lbmemory.store()` one-shots each SIGBUS-ed and re-corrupted the WAL, and the salvage rolled back the writes anyway (net zero data, three repair cycles). If the first store attempt faults, the correct move is: park the fact in the vault, salvage once, and hand the write to a session that owns the lock. A retry loop on a corrupting engine is a losing fight that risks the healthy state.
- **Never open a second `Database` handle while one is live in the same process** — that is the single-writer violation in miniature and produces an immediate SIGBUS. Salvage/verify in *separate* processes, one handle each.
- Do NOT run the repair from inside a tmux bridge / agent session that itself holds the DB — it must be run from a clean terminal, because stopping all holders kills the session doing the repair.
- Multi-process corruption surfaces in **two** shapes: stale-mmap SIGBUS (no `.wal` involved) **and** a corrupt `.wal` that blocks every subsequent open (2026-09-16). Do not rule out the single-writer root cause just because a `.wal` is present, or vice versa.
- Never `rm` the `.wal` blind. Copy it aside, then let `CHECKPOINT` (step 3) consume it — deleting it discards whatever committed writes its valid prefix still holds.
- If `import real_ladybug` or opening the corrupt DB from a shell hangs/gets blocked, do not retry it repeatedly — each open is a fresh corruption risk on a live multi-process file.
- **Always `close()` an out-of-process probe handle.** A forgotten `LadybugMemory(...)` in a scratch script keeps the engine's file lock until the interpreter exits; if that process lingers it silently blocks the *next* session's writer lock and reproduces the "another process holds it" degradation with no obvious holder. Wrap probes in `try/finally: m.close()`. (Note the tension with the pitfall above: `close()` exists on the engine-level handle, not reliably on `LadybugMemory` — when in doubt, `os._exit(0)` after flushing.)
- **`m.search()` results carry their text on `.entry`, not `.content`.** Verifying a write by reading `hit.content` gives empty strings and looks identical to "the store failed" — a false negative that can send you chasing a non-existent write bug. Confirm with `hit.entry` (a `MemoryEntry`) or `m.get(id)`.
- **A degraded session cannot be healed in place, only restarted.** Do not promise the user that killing the holder "makes this session work"; the accurate statement is that the lock is free and Ladybug comes back on the next session/gateway start, while their fact can be written out-of-process right now.
- **`hermes plugins update` deletes the flock guard.** It pulls `origin` (`Ladybug-Memory/hermes-memory-plugin`, HEAD `087d793`), which has no guard; the guard lives on the `fork` remote (`1d5b73b`). Upstream **PR #3 was closed unmerged** — do not re-pitch it without reading the closure thread. Restore with `git -C ~/.hermes/plugins/ladybug pull fork main`. Full table in the reference file.
- **This skill is local-only.** It exists in no repo (verified across all 15 `Ladybug-Memory` repos, `adsharma/hermes-agent`, NousResearch upstream, and GitHub code search), so a `~/.hermes/skills/` rewrite loses it silently — the same failure mode as the guard. Candidate for adoption into `fabzter/agent-skills`.
