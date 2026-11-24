---
name: omp-harness-api-gotchas
description: "Use when an OMP task subagent dispatch fails with 'Unknown eval tool(s)', or eval commit.draft errors 'Not inside a git repository' for a repo other than cwd, or bash reports 'UID: readonly variable'."
---

# OMP harness API gotchas

Discrete, verified OMP/bash API semantics that cause failed tool calls (2026-11-23).
These are correct calls with wrong API usage — not model emission or parser regressions
(for those, see `omp-tool-call-failure-triage`).

## `task` subagent `tools` field
- The per-task `tools` array expects **EVAL-defined tools** (created via `@tool`/`tool()` in an
  eval cell), **NOT harness tool names**.
- Passing `tools: ["bash","read","web_search","glob","grep"]` fails:
  `Unknown eval tool(s): ... Available: none`.
- **Fix:** omit the `tools` field entirely → the subagent gets its default toolset.
- For read-only research, prefer `agent: "scout"` (faster model) where available.

## eval `commit` namespace is cwd-bound
- `commit.draft()` / `d.commit()` operate on the **session cwd** repo.
- If cwd is not a git repo (or is a different repo than your target), it errors
  `Not inside a git repository: <cwd>`. It cannot target an arbitrary other repo.
- **Fix:** for a repo other than cwd (e.g. `~/src/agent-skills` while cwd is elsewhere),
  use plain `git -C <repo> add/commit` there.

## bash `UID` is readonly
- `UID=...` fails: `UID: readonly variable`. Use another name (e.g. `UPID`).

## `manage_skill` refuses symlink write-through
- A `managed-skills/<name>` entry that is a **symlink** into another dir (e.g. the skills repo)
  is readable live, but `manage_skill` update refuses:
  `resolves through a symlink; refusing to write outside the managed directory`.
- **Repo-backed managed skills:** symlink `managed-skills/<name>` → repo `skills/<name>` for live
  read/visibility, then **edit the repo file directly with `edit`/`write` + git commit/push**
  (not `manage_skill`). Repo stays the single source of truth; other agents install snapshots.