# cc-health

A Claude Code plugin that audits your Claude Code infrastructure across 7 domains — conversations, config, assets (skills/agents/plugins), memory, version compatibility, debris, and temp files. Report-first: scanners are read-only, fixes happen only after you confirm.

To decide which layer a piece of config belongs in (rule, skill, hook, memory), use [config-audit](../config-audit/). This plugin checks health, not placement.

## What it does

1. You invoke `/cc-health <domain>` (or `/cc-health full` to run everything).
2. A Python scanner reads the relevant slice of `~/.claude/` and outputs structured JSON findings.
3. Claude formats the findings as a severity-grouped report (errors → warnings → info).
4. You review the report and optionally ask Claude to fix actionable items.

The `version` domain works differently — it slices the CC changelog between your last-seen version and the current one, classifies entries for breaking changes using a dedicated agent, and checks whether any affect your config.

A SessionStart hook nudges you when Claude Code updates, so you know to run `/cc-health version` before a breaking change surprises you. On installs where Claude Code's executable path doesn't include the version number, the hook can't see updates and stays silent; run `/cc-health version` yourself after updating.

## Sample output

```
## cc-health Report — config

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
| `chats`  | `cc-health-chats.py`  | Conversations — scan, usage, clean, orphans               |
| `config` | `cc-health-config.py` | Config files, scoping, permissions, MCP                   |
| `assets` | `cc-health-assets.py` | Skills, agents, plugins, trigger clashes (TF-IDF)         |
| `memory` | `cc-health-memory.py` | MEMORY.md entries, stale paths, dated entries              |
| `version`| (orchestrated inline) | Changelog classification, breaking-change detection       |
| `debris` | `cc-health-debris.py` | Orphaned agents, TODO/FIXME markers                       |
| `temp`   | `cc-health-temp.py`   | Scratch files, artifact droppings, stale context files    |
| `full`   | (all of the above)    | Run every domain sequentially                             |

## Requirements

| Component               | Required? | Without it                                                        |
|--------------------------|-----------|-------------------------------------------------------------------|
| Claude Code              | Required  | Plugin won't load                                                 |
| Python 3.10+             | Required  | Scanners won't run (stdlib only — no pip dependencies)            |
| Plugin support (v2.1+)   | Required  | Plugin system must be available for hook registration             |
| `~/.claude/cache/changelog.md` | For `version` | Claude Code keeps this file up to date. Without it, the version check stops with "Changelog cache is unavailable" |

## Installation

1. Copy this folder into your local plugins directory:

   ```bash
   mkdir -p ~/.claude/plugins/local
   cp -r cc-health ~/.claude/plugins/local/cc-health
   ```

2. Create the local marketplace file at `~/.claude/plugins/local/.claude-plugin/marketplace.json`. Claude Code needs it to discover plugins in that folder:

   ```json
   {
     "name": "local",
     "owner": { "name": "Your Name" },
     "plugins": [
       { "name": "cc-health", "source": "./cc-health" }
     ]
   }
   ```

   If you already have this file, add the `cc-health` entry to its `plugins` list instead.

3. Register the local plugins folder and install:

   ```bash
   claude plugin marketplace add ~/.claude/plugins/local
   claude plugin install cc-health@local
   ```

4. Restart Claude Code. The SessionStart hook will initialize on first run.

## Usage

```
/cc-health config                          # Run config domain
/cc-health assets                          # Check skills, agents, plugins
/cc-health assets --deep                   # Include description-drift check (spawns agents)
/cc-health assets --clash-threshold 0.25   # Lower trigger-clash sensitivity
/cc-health chats scan --empty-only         # Find empty sessions
/cc-health chats clean                     # Preview what would be deleted (dry run)
/cc-health chats clean --confirm           # Permanently delete the previewed sessions
/cc-health chats usage                     # Disk usage by project
/cc-health chats orphans                   # Find conversations for deleted projects
/cc-health chats global                    # Full ~/.claude disk breakdown
/cc-health version                         # Check for breaking changes since last run
/cc-health full                            # Run all domains
```

With no filter, `clean` targets short-lived sessions: no assistant reply, fewer than 3 user messages, under 60 seconds, or under 2 KB. Deletion is permanent, so run the preview first.

## Bundled files

| Path                                    | What it is                                                |
|-----------------------------------------|-----------------------------------------------------------|
| `skills/cc-health/SKILL.md`             | Main skill instructions — Claude's orchestration guide    |
| `skills/cc-health/references/`          | Reference docs for path encoding and config load semantics|
| `agents/changelog-classifier.md`        | Agent definition for version-domain changelog analysis    |
| `scripts/cc-health-*.py`               | Domain scanner scripts (one per domain)                   |
| `scripts/lib/`                          | Shared Python modules (schema, frontmatter, TF-IDF)      |
| `scripts/version-detect.sh`            | SessionStart hook script — detects CC version changes     |
| `hooks/hooks.json`                      | Hook registration for the SessionStart nudge              |
| `tests/`                                | pytest test suite for all scanners                        |

Persistent state (last-seen version, trigger-clash baseline) is written to `~/.claude/cc-health-state.json` at runtime — outside the plugin directory, so reinstalling or upgrading the plugin never wipes it.
| `.claude-plugin/plugin.json`            | Plugin manifest                                           |

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

- Fixed the version check. The changelog classifier is now a flat agent file (`agents/changelog-classifier.md`) called as `cc-health:changelog-classifier`; the old name did not resolve.
- The classifier runs on Sonnet. Its `effort: high` setting is gone.
- Install steps corrected: create the local marketplace file, then register `~/.claude/plugins/local` (not the plugin folder) and install `cc-health@local`.
- The assets scanner no longer warns about bare model aliases such as `opus` or `sonnet`. It recognizes flat agent files in plugins and plugin-scoped agent names.
- The description says when to use the skill. The archive folder is described as optional.
- Removed skill-routing awareness. Trigger clashes are now one warning, `trigger-clash`.
- The effort check and the orphan check read both agent layouts (`agents/<name>.md` and `agents/<name>/AGENT.md`). An unreferenced agent that has a description is reported as info, not a warning.
- Fixed the `chats clean` example and the Domains table in the skill. The usage block now shows the dry run before `--confirm`.
- Listed the changelog cache as a requirement. The `cache` folder is marked "with caution" in the disk breakdown. The SessionStart hook falls back to `python3` on your PATH.

### 2026-07-19 — v2.0.1

- State relocated to `~/.claude/cc-health-state.json` (outside the plugin tree; survives upgrades). Legacy in-plugin state migrates automatically on first read.
- All plugin paths now use `${CLAUDE_PLUGIN_ROOT}` — install location no longer hardcoded.
- Removed hardcoded Opus model pins (classifier and `--deep` drift check inherit the session model).
- Version domain: first-run baseline handling, missing/stale changelog guards, classifier failure contract.
- Scanner failure handling and `full`-mode aggregation rules documented in the skill.
- Documented the chats `global` subcommand; wired reference docs into the report flow.

### 2026-07-18

- Initial public release as cc-health v2.0.0 (successor to cc-audit).
- 7 audit domains: chats, config, assets, memory, version, debris, temp.
- TF-IDF trigger-clash detection with delta reporting and routing-override awareness.
- DFS path resolver for lossy hyphen-encoded project paths.
- Changelog classifier agent for breaking-change detection.
- SessionStart hook for version-change nudges.
- Full pytest suite covering all scanner domains.
