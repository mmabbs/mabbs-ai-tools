---
name: check-cc-health
description: "Audit Claude Code infrastructure health — config, skills/agents/plugins, memory, version compat, conversations, debris, temp files. Report-first, fix on confirmation. Use when the user asks for a health check or cleanup of their Claude Code setup, suspects broken skill or agent references or stale memory paths, wants to know what old conversations and temp files are taking up, or asks what a Claude Code update changed for them."
argument-hint: chats|config|assets|memory|version|debris|temp|full
---

## Domains

| Domain | Scanner | What it checks |
|--------|---------|----------------|
| `chats` | `check-cc-health-chats.py` | Conversations — scan, usage, clean, orphans |
| `config` | `check-cc-health-config.py` | Config files, scoping, permissions, MCP |
| `assets` | `check-cc-health-assets.py` | Skills, agents, plugins, trigger clashes |
| `memory` | `check-cc-health-memory.py` | MEMORY.md entries, stale paths |
| `version` | (orchestrated inline) | Changelog classification, compat checks |
| `debris` | `check-cc-health-debris.py` | Orphaned agents, TODO/FIXME markers |
| `temp` | `check-cc-health-temp.py` | Scratch files, artifact droppings, stale context files |
| `full` | (all of the above) | Run every domain sequentially |

## Workflow

### Step 1: Parse invocation

Extract the domain from the user's message. If no domain is specified, ask which domain to run or suggest `full`.

Accepted forms:
- `/check-cc-health config`
- `/check-cc-health chats clean --empty-only`
- `/check-cc-health assets --deep`
- `/check-cc-health full`

### Step 2: Run scanner

For all domains except `version`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-<domain>.py [flags]
```

The script outputs JSON to stdout. Parse it as the finding report.

`--deep` is not a scanner flag. This skill handles it in Step 4, and the assets scanner exits with an argument error if it receives it. Pass every other flag through.

**Scanner failures:** If a scanner exits non-zero, prints a traceback, or emits anything that isn't parseable JSON, do NOT treat it as "no findings." Report the domain as failed (quote the last few lines of stderr), retry at most once, and in `full` mode continue with the remaining domains. If failures persist, suggest checking `python3 --version` — the scanners require Python 3.10+.

For `chats` domain, pass the subcommand as a positional argument:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-chats.py scan [--project PATH] [--exact] [--filter-command CMD] [--empty-only]
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-chats.py clean [--confirm]
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-chats.py usage
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-chats.py orphans
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-cc-health-chats.py global
```

(`global` reports a full `~/.claude` disk breakdown — useful when the user asks where disk space went, not needed for routine audits.)

For `full` mode, run each domain sequentially and aggregate findings. For the chats domain in `full` mode, run `scan`, `usage`, and `orphans` — never `clean`.

**Chats output translation:** The chats scanner does NOT use the AuditReport schema the other domains use. Each subcommand prints its own JSON object: a `mode` key, a list (`conversations`, `projects`, or `orphans`), and a `summary` object. When aggregating for `full` mode, do NOT treat chats output as Finding objects. Instead, summarize it as: conversation count (`scan` → `summary.total`), short-lived session count (`scan` → `summary.short_lived`), orphan count (`orphans` → `summary.total_orphaned_projects`), custom-named project dirs (`orphans` → `custom_named_dirs`, if any), and total disk usage (`usage` → `summary.total_size_human`). Present this summary in a "Chats" section of the report alongside the other domains' finding tables.

**Assets notes — trigger clash detection:** The assets scanner always checks for overlapping skill trigger descriptions using TF-IDF similarity. Pairs above the threshold (default 0.35, tunable via `--clash-threshold`) are flagged as `trigger-clash` warnings.

Calibration: unrelated skills typically score below 0.2, related-but-distinct skills land between 0.2 and 0.35, and true overlaps score above 0.5 — lower the threshold to catch subtler collisions, raise it if warnings feel noisy. Run with a custom threshold: `/check-cc-health assets --clash-threshold 0.25`

**Delta reporting:** Previously-seen clashes are suppressed on subsequent runs — only new clashes are surfaced. Use `--all-clashes` to bypass delta and show everything (this also resets the baseline for future runs).

### Step 3: Version domain (special handling)

The `version` domain does NOT have a standalone scanner script. Orchestrate it inline:

1. **Read state file:**
   ```bash
   cat ~/.claude/check-cc-health-state.json
   ```
   Extract `lastSeenVersion`. (State lives in `~/.claude/`, outside the plugin directory, so plugin upgrades don't wipe it.)

   **First run:** if the file is missing, or `lastSeenVersion` is null or not a version number (`X.Y.Z`), there is no baseline to diff against. Write the current version to the state file, tell the user the baseline was initialized (comparisons start next run), and skip the rest of the version domain.

2. **Read current version:**
   ```bash
   claude --version
   ```
   Output looks like `2.1.215 (Claude Code)` — take the leading semver. Fast path: if `$CLAUDE_CODE_EXECPATH` is set and its basename is a bare version number, `basename "$CLAUDE_CODE_EXECPATH"` gives the same answer without a subprocess — but on some install methods the basename is a binary name, not a version, so fall back to `claude --version` whenever it doesn't look like `X.Y.Z`.

3. **Check changelog freshness:**
   Read `~/.claude/cache/changelog.md`. If the file doesn't exist, warn: "Changelog cache is unavailable — cannot classify." and stop. Otherwise find the first `## X.Y.Z` heading. If that version is older than the current version, warn: "Changelog cache is stale — cannot classify accurately." and stop.

4. **Slice changelog:**
   Extract all content between `## <lastSeenVersion>` and `## <currentVersion>` (or from `## <lastSeenVersion>` to the top if currentVersion is the latest).

5. **Classify via agent:**
   Spawn the changelog-classifier agent with the changelog slice:
   ```
   Agent({
     subagent_type: "check-cc-health:changelog-classifier",
     prompt: "Classify these changelog entries:\n\n<slice>"
   })
   ```
   The agent returns JSON with classified entries (only breaking/deprecation/schema-change). An empty array `[]` is a valid result — it means nothing since `lastSeenVersion` needs attention. If the response is NOT parseable JSON, report that classification failed and stop — never proceed silently.

6. **Match against config:**
   For each classified entry, extract the concrete identifier the change affects and grep the user's config files for it (e.g., for "Renamed `workflow` keyword to `ultracode`", grep for `workflow`):
   - `settings.json`, `settings.local.json` for setting keys and env vars
   - `~/.claude/skills/*/SKILL.md` for trigger keywords
   - `~/.claude/agents/*.md` and `~/.claude/agents/*/AGENT.md` for model/effort references

7. **Report only relevant hits.**

8. **Update state file:** Set `lastSeenVersion` to current version, update `domainRuns.version` timestamp.

### Step 4: Assets `--deep` (only when the flag was passed)

Skip this step entirely unless `assets` was invoked with `--deep`:

1. Run the regular scanner first, without `--deep` (it runs checks 1–4, 6 and 7; check 5 is this step).
2. For each skill found, spawn an inline agent to check description drift:
   ```
   Agent({
     subagent_type: "general-purpose",
     prompt: "Compare this skill's description frontmatter against what its body actually does. Does the description accurately represent the skill's behavior?\n\nDescription: <desc>\n\nBody:\n<body>\n\nRespond with JSON: {\"drifted\": bool, \"reason\": \"...\"}"
   })
   ```
   If the session reports the general-purpose agent as unavailable, skip the drift check and note the skip in the report instead of failing the step.
3. Add findings for skills where `drifted: true`.

### Step 5: Present report

Format findings as a markdown report:

```markdown
## check-cc-health Report — <domain>

**Summary:** X errors, Y warnings, Z info

### Errors
| Check | Message | File | Suggested Action |
|-------|---------|------|-----------------|
| ... | ... | ... | ... |

### Warnings
| Check | Message | File | Suggested Action |
|-------|---------|------|-----------------|
| ... | ... | ... | ... |

### Info
| Check | Message | File | Suggested Action |
|-------|---------|------|-----------------|
| ... | ... | ... | ... |
```

If no findings: "No issues found in the <domain> domain."

For `full` mode, repeat this template as one section per domain (Chats gets its summary section per the translation note in Step 2), preceded by a single combined summary line across all domains.

When explaining findings to the user, consult the bundled references: `references/load-semantics.md` for config scoping/inheritance findings (mis-scoped settings, MCP scope mismatches), and `references/path-encoding.md` for orphaned-conversation or path-decode findings.

### Step 6: Fix on confirmation (if requested)

After presenting findings, the user may ask to fix issues. For each actionable finding:

- **Deletions** (orphaned entries, stale files): confirm per-batch, then delete.
- **Scope changes** (MCP re-scoping): show the exact change, confirm, then apply.
- **Removals** (stale env vars, dead imports): show what will be removed, confirm, apply.

Never fix without explicit confirmation. Group similar fixes when count > 5.

## Constraints

- Report-first: scanners are read-only. Only fix after user confirmation.
- The scanners skip any folder named `archive` under `~/.claude/`. It's an optional place to park retired config; nothing depends on it existing.
- Skip files modified in the last hour (active session protection) in chats/clean.
- Never delete the current active session.
- The `version` domain updates state AFTER reporting — never before (so re-runs are safe).

## Output Location

- Console: Always output report to conversation
- No file output by default
