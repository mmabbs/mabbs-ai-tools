# mabbs-ai-tools
A small collection of skills and plugins I use in my own Claude workflows, cleaned up so anyone can install them. Each tool is a self-contained folder. Most are skills you copy into a skills directory; `check-cc-health` installs as a plugin. No build step.

New to Claude skills? Check out [Anthropic's docs on Claude Skills](https://code.claude.com/docs/en/skills)

## Tools

### Design

| Tool | What it does | Notes |
| ---- | ------------ | ----- |
| [map-build](tools/map-build/) | Walks you through a build as a graph (nodes, edges, shared state, checkers, failure paths) before any spec exists, starting from one loop and making every extra part earn its place. A skeptic agent reviews the design; you get a note plus an interactive HTML page. | manual-only · bundles an agent · Python 3 |

### Skill development

| Tool                                 | What it does                                                                                                                                              | Notes                        |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| [sanitize-release](tools/sanitize-release/) | Turns a personal skill into a public copy: scans for secrets, private names, and portability problems, strips personal data, writes the README, runs an independent review, and gates the repo move. | manual-only · Opus · Python 3 |

### Claude Code setup

| Tool                                     | What it does                                                                                                                                                          | Notes                          |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| [check-cc-health](tools/check-cc-health/)           | Plugin that audits Claude Code infrastructure across 7 domains (chats, config, assets, memory, version compat, debris, temp files) with Python scanners and a SessionStart hook. Companion to the built-in `/doctor`. | Plugin install |
| [audit-config](tools/audit-config/)     | Audits every Claude Code config layer (rules, skills, hooks, plugins, MCP, memory, CLAUDE.md, agents) across all your projects and recommends what to relocate, consolidate, or create. Picks up where `/doctor` stops. | Spawns subagents · Opus recommended |

### Local scene & monitoring

| Tool                       | What it does                                                                                       | Notes                                            |
| -------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [fetch-ai-news](tools/fetch-ai-news/) | Generates a Canadian AI-industry news digest covering funding, jobs, regulation, and market moves. | Region-configurable · writes files               |
| [find-events](tools/find-events/) | Scrapes local tech and AI events from several sources into one date-stamped, categorized note.     | Region-configurable · manual-only · writes files |

**Notes legend:** _manual-only_ — runs only when you invoke it, won't auto-trigger; _region-configurable_ — ships with Canadian defaults you can repoint.

## Install

Each tool is one folder. For a skill, clone the repo and copy the folder you want into your skills directory (`check-cc-health` is a plugin and installs differently; see below):

```bash
git clone --depth 1 https://github.com/<user>/<repo>.git
cp -r <repo>/tools/audit-config ~/.claude/skills/
```

- `~/.claude/skills/` installs a skill for every project. A project's own `.claude/skills/` scopes it to that repo.
- Claude Code detects newly added skills without a restart.
- Want one skill without cloning the whole repo? Use GitHub's "download folder" option, or [`degit`](https://github.com/Rich-Harris/degit) (requires Node 20+):

  ```bash
  degit <user>/<repo>/tools/audit-config ~/.claude/skills/audit-config
  ```

Replace `<user>/<repo>` with this repository's path.

## Before you run them

Some tools assume a particular environment. Each tool's own `README.md` documents its requirements, configuration, and how it behaves without them — the short version:

- **Obsidian-coupled** — `find-events` and `fetch-ai-news` write notes into an Obsidian vault. The per-tool READMEs list what to change for your own vault, or how to run them standalone.
- **Region-configurable** — `fetch-ai-news` and `find-events` default to Canadian and Toronto sources. Both document how to point them elsewhere.
- **Bundled scripts** — `find-events` includes a cron wrapper shell script that expects `claude` on your PATH.
- **Plugin install** — `check-cc-health` is a plugin, not a standalone skill. It requires the local plugin install flow (`claude plugin marketplace add` + `claude plugin install`). See its README for the full steps.
- **Bundled agent** — `map-build` ships a `skeptic` agent in its `agents/` folder. Copy it to `~/.claude/agents/` too, or the review step can't run. Its README has the steps.
- **Subagent-heavy** — `audit-config` spawns eight parallel scanner agents plus one reasoning agent per run. It targets Sonnet for scanning and Opus for the cross-layer reasoning; without those models it falls back to your session model.

## Maintenance and contributions

These are tools I build and maintain for my own use. I make a genuine effort to review issues and pull requests, but I can't promise a response time or that I'll merge. Treat it as best-effort. Fork freely.
