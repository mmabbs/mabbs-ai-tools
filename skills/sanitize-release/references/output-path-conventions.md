# Output Path Conventions for Published Skills

Published skills must not embed the author's folder structure, vault layout, or project organization into defaults, examples, or instructions. A stranger running the skill should never encounter a path that only made sense on the author's machine.

## Decision Matrix

How a skill should handle output paths depends on what it produces:

| Output type | Convention | Rationale | Examples |
|---|---|---|---|
| **Ephemeral** — reports, dashboards, previews, one-off analysis | Write to CWD, no subdirectory | User runs the skill where they want the file. No structure to assume. | `session-report`, `playground` |
| **Infrastructure** — Claude Code state, caches, plugin data | `~/.claude/` or `${CLAUDE_PLUGIN_DATA}` | Belongs to Claude Code, not the user's project tree. | `project-artifact`; a usage-stats dashboard that caches data |
| **Persistent notes** — vault notes, structured documents the user organizes | Parameterized path, no default folder | The user's organizational scheme is their own. Skill asks or accepts a path; never assumes one. | a note-taking skill that asks where to save |
| **Project artifacts** — generated configs, code, project-scoped output | Project root or CWD | Output lives with the code. No assumed subfolder hierarchy. | `skill-creator` |

## What Counts as Author-Specific

Not just absolute paths. Any of these in a skill's defaults, examples, or instructions are portability failures:

1. **Relative paths that encode folder structure** — `notes/events/`, `scrapers/output/`, `Research/AI/`. These assume the user's project has the same directory tree as the author's.
2. **City/locale-specific defaults** — `chicago-events-YYYY-MM-DD.md`, timezone assumptions, locale-specific date formats in filenames.
3. **Domain/tag defaults** — `book-club`, `ai-news`, or any tag that reflects the author's use case rather than the skill's function.
4. **Vault-specific conventions** — frontmatter schemas, folder naming patterns, or organizational rules that belong to the author's vault, not the skill.
5. **Output masquerading as input** — frontmatter properties the skill *writes* listed as things the skill *expects*. This misleads users into thinking they need to set up something that's actually generated.

## Placeholder Format

When a value must be supplied by the user, use angle-bracket placeholders:

| Category | Placeholder | NOT this |
|---|---|---|
| Output folder | `<output-folder>` | `notes/events/` |
| Vault name | `<vault-name>` | `my-notes-vault` |
| City/locale | `<city>` | `chicago` |
| Domain tag | `<your-domain>` | `book-club` |
| File path | `<path-to-file>` | `~/Documents/notes/...` |

Placeholders go in README examples, default configurations, and any instructional text. The skill's own SKILL.md `argument-hint` should also use this format.

## The Test

For every literal value in a skill's output paths, defaults, and examples, ask: **"Would a stranger pick this same value?"**

- `YYYY-MM-DD` in a date-stamped filename → yes, that's a universal format convention. Keep it.
- `notes/events/` as the output folder → no, that's the author's vault structure. Replace with `<output-folder>`.
- `scraped-date` as a frontmatter key the skill writes → yes, that's the skill's own schema. Keep it.
- `book-club` as a default tag → no, that's the author's domain. Replace with `<your-domain>` or remove.
