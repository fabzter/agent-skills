# agent-skills

Agent-neutral skills shared across every coding agent on a machine: omp (oh-my-pi), Claude Code, Codex CLI, Devin, Hermes, OpenClaw, Qwen Code, Qoder, OpenCode.

## Layout

- `skills/<name>/SKILL.md` — canonical skill source (uniform format: YAML frontmatter `name` + `description`).
- `SKILL.md` (root, symlink) — for installers that require a repo-root `SKILL.md` (OpenClaw `skills install git:`).
- `plugins/<name>/` — Claude/omp plugin wrapper (`.claude-plugin/plugin.json` + `skills/` symlink) for marketplace installs.
- `.claude-plugin/marketplace.json` and `.omp-plugin/marketplace.json` — plugin catalogs for `claude plugin marketplace add` / omp `/marketplace add`.
- `.devin-plugin/plugin.json` — Devin plugin manifest (`skills: ["skills"]`).

## Install per agent

| agent | command |
|---|---|
| omp | `/marketplace add fabzter/agent-skills` then `/marketplace install token-plan-multimodal-gen@fabzter-agent-skills` |
| Claude Code | `claude plugin marketplace add fabzter/agent-skills` then `claude plugin install token-plan-multimodal-gen@fabzter-agent-skills --scope user --yes` |
| Codex | `python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo fabzter/agent-skills --path skills/token-plan-multimodal-gen` |
| Devin | `devin plugins install fabzter/agent-skills -y` |
| Hermes | `hermes skills tap add fabzter/agent-skills` then `hermes skills install fabzter/agent-skills/token-plan-multimodal-gen --yes` |
| OpenClaw | `openclaw skills install git:fabzter/agent-skills --global` |
| Qwen / Qoder / others | `npx skills add fabzter/agent-skills -a qwen-code -a qoder -g` |
| Any (universal) | symlink or copy `skills/<name>` into the agent's user skills dir (e.g. `~/.agents/skills/`, read natively by Codex, OpenCode, omp, Devin) |

## Skills

- `token-plan-multimodal-gen` — image/TTS/video generation via Alibaba Model Studio Token Plan (DashScope-native endpoints; verified live on the Singapore subscription).
- `chrome-relay-live-tab` — drive the user's live, logged-in Chrome tabs (read/navigate/click/type/scratch tabs) via the omp browser relay's raw CDP endpoint; verified operation catalog inside.
- `ats-form-filling` — fill job-application forms (Workday, Greenhouse) in the live logged-in Chrome tab via the CDP relay, sourced from the CV; React-input patterns, spinbutton date fields, and the Skills-dictionary/stale-state pitfalls.
- `ladybug-memory-runbook` — diagnose and repair Ladybug graph-memory failures ("database is not initialised", corrupt WAL, SIGBUS, FTS-index inconsistency, multi-process single-writer corruption).
- `gog-oauth-refresh-token-expiry` — diagnose and fix gog CLI logins that die every ~7 days (Google External+Testing 7-day refresh tokens); detect via `refresh_token_expires_in` on the token endpoint, fix by completing OAuth branding + publishing the app to In production + a `--force-consent` re-auth.

OpenClaw's `skills install git:` takes the repo-root `SKILL.md` (single skill). For additional skills, symlink them: `ln -s <clone>/skills/<name> ~/.openclaw/skills/<name>`.

## omp via CLI (non-interactive, reproducible)

The table above uses omp's in-session slash commands. The same installs work from a shell, which is easier to script and verify:

```bash
omp plugin marketplace update fabzter-agent-skills          # refresh the cached catalog after a push
omp plugin install <skill>@fabzter-agent-skills --scope user # install
omp plugin list                                              # confirm it shows (user) + enabled
```

**Refresh the marketplace before installing a newly-added skill** — omp caches the catalog
(`~/.omp/plugins/cache/marketplaces/<mp>/marketplace.json`); a skill pushed after the last
`marketplace add`/`update` will not appear until you update. The install materializes under
`~/.omp/plugins/cache/plugins/<mp>___<skill>___<ver>/`, with `skills/<name>` symlinked into the
cached marketplace clone — verify with `find -L` (the symlink, not the raw dir).
