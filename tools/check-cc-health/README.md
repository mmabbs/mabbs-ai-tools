# check-cc-health

A Claude Code plugin that audits your Claude Code infrastructure across 7 domains — conversations, config, assets (skills/agents/plugins), memory, version compatibility, debris, and temp files. Report-first: scanners are read-only, fixes happen only after you confirm.

To decide which layer a piece of config belongs in (rule, skill, hook, memory), use [audit-config](../audit-config/). This plugin checks health, not placement.

## What it does

1. You invoke `/check-cc-health <domain>` (or `/check-cc-health full` to run everything).
2. A Python scanner reads the relevant slice of `~/.claude/` and outputs structured JSON findings.
3. Claude formats the findings as a severity-grouped report (errors → warnings → info).
4. You review the report and optionally ask Claude to fix actionable items.

The `version` domain works differently — it slices the CC changelog between your last-seen version and the current one, classifies entries for breaking changes using a dedicated agent, and checks whether any affect your config.

A SessionStart hook nudges you when Claude Code updates, so you know to run `/check-cc-health version` before a breaking change surprises you. On installs where Claude Code's executable path doesn't include the version number, the hook can't see updates and stays silent; run `/check-cc-health version` yourself after updating.

## How it fits with `/doctor`

Claude Code's built-in `/doctor` (and `/skill-doctor`) cover different ground. Run both:

| Built-in `/doctor` covers                                          | check-cc-health covers                                                        |
|--------------------------------------------------------------------|-------------------------------------------------------------------------|
| Your install, PATH, and update channel                             | Changelog entries since your last run that touch your config           |
| Settings and `.mcp.json` files that fail to parse                  | Project entries and MCP servers tied to folders that no longer exist   |
| Agent and skill frontmatter that won't load                        | Broken skill/agent references and dead `@`-imports across every project |
| Unused skills, plugins, and MCP servers (with `/skill-doctor` stats) | Skills whose trigger descriptions compete with each other              |
| CLAUDE.md trimming and dedup in the current project                | Stale and dated auto-memory entries                                    |
| Slow hooks, permission defaults                                    | Old conversations, orphaned project folders, leftover scratch files    |

Where the two overlapped, check-cc-health dropped its check: malformed `.mcp.json` files are left to `/doctor`.

## Sample output

```
## check-cc-health Report — config

**Summary:** 0 errors, 2 warnings, 1 info

### Warnings
| Check                  | Message                                                      | Suggested Action                     |
|------------------------|--------------------------------------------------------------|--------------------------------------|
| orphaned-project-entry | Project entry points to non-existent directory: -Users-jdoe… | Remove the entry from .claude.json   |
| mcp-scope-mismatch     | MCP server 'obsidian' local-scoped to non-existent dir       | Remove or re-scope to 'user'         |

### Info
| Check                | Message                                              | Suggested Action                         |
|----------------------|------------------------------------------------------|------------------------------------------|
| duplicate-permission | Permission 'Bash(git:*)' in both settings files      | Remove from one (settings.local wins)    |
```

## Domains

| Domain   | Scanner script        | What it checks                                            |
|----------|-----------------------|-----------------------------------------------------------|
| `chats`  | `check-cc-health-chats.py`  | Conversations — scan, usage, clean, orphans               |
| `config` | `check-cc-health-config.py` | Config files, scoping, permissions, MCP                   |
| `assets` | `check-cc-health-assets.py` | Skills, agents, plugins, trigger clashes (TF-IDF)         |
| `memory` | `check-cc-health-memory.py` | MEMORY.md entries, stale paths, dated entries              |
| `version`| (orchestrated inline) | Changelog classification, breaking-change detection       |
| `debris` | `check-cc-health-debris.py` | Orphaned agents, TODO/FIXME markers                       |
| `temp`   | `check-cc-health-temp.py`   | Scratch files, artifact droppings, stale context files    |
| `full`   | (all of the above)    | Run every domain sequentially                             |

## Requirements

| Component               | Required? | Without it                                                        |
|--------------------------|-----------|-------------------------------------------------------------------|
| Claude Code              | Required  | Plugin won't load                                                 |
| Python 3.10+             | Required  | Scanners won't run (stdlib only — no pip dependencies)            |
| Plugin support (v2.1+)   | Required  | Plugin system must be available for hook registration             |
| `~/.claude/cache/changelog.md` | For `version` | Claude Code keeps this file up to date. Without it, the version check stops with "Changelog cache is unavailable" |

## Installation

1. Clone the repo and copy this folder into your local plugins directory:

   ```bash
   git clone --depth 1 https://github.com/mmabbs/mabbs-ai-tools.git
   mkdir -p ~/.claude/plugins/local
   cp -r mabbs-ai-tools/tools/check-cc-health ~/.claude/plugins/local/check-cc-health
   ```

2. Create the local marketplace file at `~/.claude/plugins/local/.claude-plugin/marketplace.json`. Claude Code needs it to discover plugins in that folder:

   ```json
   {
     "name": "local",
     "owner": { "name": "Your Name" },
     "plugins": [
       { "name": "check-cc-health", "source": "./check-cc-health" }
     ]
   }
   ```

   If you already have this file, add the `check-cc-health` entry to its `plugins` list instead.

3. Register the local plugins folder and install:

   ```bash
   claude plugin marketplace add ~/.claude/plugins/local
   claude plugin install check-cc-health@local
   ```

4. Restart Claude Code. The SessionStart hook will initialize on first run.

## Usage

```
/check-cc-health config                          # Run config domain
/check-cc-health assets                          # Check skills, agents, plugins
/check-cc-health assets --deep                   # Include description-drift check (spawns agents)
/check-cc-health assets --clash-threshold 0.25   # Lower trigger-clash sensitivity
/check-cc-health chats scan --empty-only         # Find empty sessions
/check-cc-health chats clean                     # Preview what would be deleted (dry run)
/check-cc-health chats clean --confirm           # Permanently delete the previewed sessions
/check-cc-health chats usage                     # Disk usage by project
/check-cc-health chats orphans                   # Find conversations for deleted projects
/check-cc-health chats global                    # Full ~/.claude disk breakdown
/check-cc-health version                         # Check for breaking changes since last run
/check-cc-health full                            # Run all domains
```

With no filter, `clean` targets short-lived sessions: no assistant reply, fewer than 3 user messages, under 60 seconds, or under 2 KB. Deletion is permanent, so run the preview first.

## Bundled files

| Path                                    | What it is                                                |
|-----------------------------------------|-----------------------------------------------------------|
| `skills/check-cc-health/SKILL.md`             | Main skill instructions — Claude's orchestration guide    |
| `skills/check-cc-health/references/`          | Reference docs for path encoding and config load semantics|
| `agents/changelog-classifier.md`        | Agent definition for version-domain changelog analysis    |
| `scripts/check-cc-health-*.py`               | Domain scanner scripts (one per domain)                   |
| `scripts/lib/`                          | Shared Python modules (schema, frontmatter, TF-IDF, path decoding) |
| `scripts/version-detect.sh`            | SessionStart hook script — detects CC version changes     |
| `hooks/hooks.json`                      | Hook registration for the SessionStart nudge              |
| `tests/`                                | pytest test suite for all scanners                        |
| `.claude-plugin/plugin.json`            | Plugin manifest                                           |

Persistent state (last-seen version, trigger-clash baseline) is written to `~/.claude/check-cc-health-state.json` at runtime — outside the plugin directory, so reinstalling or upgrading the plugin never wipes it.

## Not implemented (ideas)

Checks that were scoped but never built. Listed here so nobody assumes the scanners cover them:

- Config: settings.json launch-root placement detection
- Config: MCP subdirectory-loss detection (flagging when subdir launches would lose a server)
- Memory: dead flag/setting references (setting keys named in memory not in active config)
- Memory: fuzzy-match moved path suggestions
- Debris: dead @-imports across all CLAUDE.md files (currently in assets domain only)
- Debris: half-renamed identifier detection
- Temp: abandoned git worktree detection

## Changelog

### 2026-11-16

- Renamed from `cc-health`. The plugin, skill, and command are now `check-cc-health`. If you installed the old plugin, uninstall it and install `check-cc-health@local`.
- Fixed the version check. The changelog classifier is now a flat agent file (`agents/changelog-classifier.md`) called as `check-cc-health:changelog-classifier`; the old name did not resolve.
- The classifier runs on Sonnet. Its `effort: high` setting is gone.
- Install steps corrected: create the local marketplace file, then register `~/.claude/plugins/local` (not the plugin folder) and install `check-cc-health@local`.
- The assets scanner no longer warns about bare model aliases such as `opus` or `sonnet`. It recognizes flat agent files in plugins and plugin-scoped agent names.
- The description says when to use the skill. The archive folder is described as optional.
- Removed skill-routing awareness. Trigger clashes are now one warning, `trigger-clash`.
- The effort check and the orphan check read both agent layouts (`agents/<name>.md` and `agents/<name>/AGENT.md`). An unreferenced agent that has a description is reported as info, not a warning.
- Fixed the `chats clean` example and the Domains table in the skill. The usage block now shows the dry run before `--confirm`.
- Listed the changelog cache as a requirement. The `cache` folder is marked "with caution" in the disk breakdown. The SessionStart hook falls back to `python3` on your PATH.

### 2026-10-05 — v2.1.0

- Repositioned alongside Claude Code's built-in `/doctor`; see "How it fits with `/doctor`".
- Config: removed the `malformed-mcp-json` check (`/doctor` parse-checks `.mcp.json`).
- Assets: `invalid-model-id` (flagged bare aliases) replaced by `pinned-model-id`, an info-level notice that a full model ID won't follow newer releases. Bare aliases (`opus`, `sonnet`, `haiku`) are no longer flagged.
- Assets: the model/effort check now reads flat `agents/<name>.md` files, the standard layout, as well as `agents/<name>/AGENT.md`. Previously it skipped flat files.
- Assets: plugin agents are recognized in both layouts and under their `<plugin>:<name>` form, so references like `check-cc-health:changelog-classifier` no longer read as broken.
- Fixed the bundled classifier agent: it is now `agents/changelog-classifier.md` with `name` and `description` frontmatter. It previously had no `name` or `description`, so it registered under a path-derived name the version domain didn't call.
- Fixed `/check-cc-health assets --deep` failing: `--deep` is handled by the skill and no longer passed to the scanner, which rejects it.
- Corrected the skill's description of the chats output (an object with a `summary`, not a list) and named the field behind each reported count.
- `references/path-encoding.md` now matches the code: `.` and `_` also collapse to `-`.
- Changelog classifier: `irrelevant` now means "nothing a user's config, scripts, or workflow could depend on", so it no longer guesses what the user uses.
- Moved the "When to Use" triggers into the skill description, where they affect routing.
- Chats and config now share one path decoder (`scripts/lib/pathcodec.py`). It matches encoded project names against real folder names, so names with any punctuation (`my_app`, `site.v2`, `{Project}`) resolve. Previously `chats orphans` could report those projects as deleted.
- `references/path-encoding.md` rewritten: Claude Code turns every non-letter, non-digit character into `-`, not just a handful.
- `references/load-semantics.md` checked against Claude Code 2.1.289 and stamped; the `/compact` note corrected (nested CLAUDE.md files reload on demand).

### 2026-07-19 — v2.0.1

- State relocated to `~/.claude/check-cc-health-state.json` (outside the plugin tree; survives upgrades). Legacy in-plugin state migrates automatically on first read.
- All plugin paths now use `${CLAUDE_PLUGIN_ROOT}` — install location no longer hardcoded.
- Removed hardcoded Opus model pins (classifier and `--deep` drift check inherit the session model).
- Version domain: first-run baseline handling, missing/stale changelog guards, classifier failure contract.
- Scanner failure handling and `full`-mode aggregation rules documented in the skill.
- Documented the chats `global` subcommand; wired reference docs into the report flow.

### 2026-07-18

- Initial public release as check-cc-health v2.0.0 (successor to cc-audit).
- 7 audit domains: chats, config, assets, memory, version, debris, temp.
- TF-IDF trigger-clash detection with delta reporting and routing-override awareness.
- DFS path resolver for lossy hyphen-encoded project paths.
- Changelog classifier agent for breaking-change detection.
- SessionStart hook for version-change nudges.
- Full pytest suite covering all scanner domains.
