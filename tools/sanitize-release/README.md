# Sanitize Release

Takes a personal Claude Code skill and produces a copy ready for public release. The live skill is never touched — all changes happen on a staging copy. A scan script checks for secrets, your private names, and anything that only works on your machine. A fresh reviewer agent then reads the result as a stranger would, and nothing reaches your repo until both are accounted for.

- **Stage 0 — Private terms check.** The scan reads your own names and identifiers from a local file. If the file is missing, the skill stops and offers to create it.
- **Stage 1 — Canonicalize.** Finds every copy of the skill (live, staging, exports), diffs them, and merges into one canonical version.
- **Stage 2 — Scan and assess.** Runs the scan, reads every file, and presents findings in three buckets: sanitization issues, polish items, and what needs writing. Images and PDFs the scan can't read are listed for you to open. No edits happen until you've seen the full picture.
- **Stage 3 — Blockers and advisories.** Reports objective defects (broken references, missing scripts) separately from observations. Blockers gate the repo move; advisories are stated once and dropped.
- **Stage 4 — Copy to staging.** Creates the working copy in your staging directory.
- **Stage 5 — Mechanical pass.** Applies uniform changes (strip vault metadata, replace personal names and paths, neutralize secrets, bundle referenced agents) without confirmation.
- **Stage 6 — Judgment pass.** Presents keep/remove decisions that need your input: regional identity vs. personal interest, coupling strategy, positioning claims, and leaks no scan can catch (people named in prose, unreleased plans).
- **Stage 7 — Docs, review, and gate.** Writes the public README, scans the staging copy, runs a fresh reviewer agent that didn't make the edits, and moves the skill to the repo only when everything is accounted for and no blockers remain.
- **Stage 8 — Handoff.** Offers an optional prompt audit, checks that your next commit uses your public email, and offers a commit.

## Sample output

The scan groups findings by type, masks secrets, and lists files it can't read:

```
Scanned: /path/to/staging/daily-brief
Files read: 6
Private terms: 12 rule(s) from /home/you/.config/leak-scan/private-terms
Errors: 4   Warnings: 2

== secret
[error] references/source-config.md:8  google_api_key: AIza****
    api_key: AIza****
[error] references/source-config.md:8  credential_assignment: api_key: AIza****
    api_key: AIza****

== private_term
[error] SKILL.md:41  private_term: Acme Notes
    Save the brief into the AcmeNotesVault inbox.

== portability
[error] SKILL.md:12  named_agent_ref: subagent_type: "daily-brief--summarizer"
    subagent_type: "daily-brief--summarizer"
[warning] SKILL.md:30  mcp_tool_ref: mcp__notes__write_note
    Write the brief with mcp__notes__write_note.
[warning] SKILL.md:52  model_pin: claude-sonnet-5-5
    Summaries run on claude-sonnet-5-5.

== binaries (a scan cannot read these; open each one)
  assets/example-output.png
```

After a run, the staging directory holds the sanitized skill:

```
staging/daily-brief/
├── SKILL.md              # Clean frontmatter, no personal paths
├── README.md             # Public README with requirements table
├── references/
│   └── source-config.md  # API keys replaced with placeholders
├── scripts/
│   └── fetch_news.py     # Uses ${CLAUDE_SKILL_DIR}, not absolute paths
└── agents/
    └── daily-brief--summarizer.md  # Bundled agent definition
```

## Requirements

| Component | Required? | Without it |
|-----------|-----------|------------|
| Claude Code | Required | The skill runs inside Claude Code sessions |
| macOS or Linux | Required | The skill uses `diff`, `python3`, and `open`/`xdg-open`. On Windows, run Claude Code in WSL |
| Python 3 | Required | The scan can't run. It uses only the standard library — nothing to install |
| A private-terms file | Required | The scan stops. The skill offers to create one on first run — see Configuration |
| Access to Opus | Required | The Stage 7 reviewer can't run. It's pinned to Opus because it's the last check before something goes public |
| Git | Required | No commit email check or commit offer |
| A staging directory and a local git repo | Required | Nowhere to write the sanitized copy or publish it — configure in `repo-conventions.md` |
| Claude Code's bundled `claude-api` skill | Optional | The Stage 8 prompt audit falls back to `/doctor prompt-audit`; sanitization itself is unaffected |

## Installation

```bash
git clone https://github.com/mmabbs/mabbs-ai-tools.git
mkdir -p ~/.claude/skills
cp -r mabbs-ai-tools/tools/sanitize-release ~/.claude/skills/sanitize-release
```

## Usage

The skill is manual-only: it runs when you type the command, never on its own.

```
/sanitize-release ~/.claude/skills/<skill-name>
```

Add any context after the path, such as known issues or where the skill was published before.

## Configuration

Edit the installed copy: `~/.claude/skills/sanitize-release/references/repo-conventions.md`.

**1. Paths.** Replace the placeholders in the Paths table:

| Placeholder | Replace with |
|-------------|-------------|
| `/path/to/your/staging/directory/` | Your staging directory for sanitized copies |
| `/path/to/your/local/skills-repo/` | Your local git repo for published skills |
| `https://github.com/your-username/your-skills-repo/` | Your GitHub repo URL |

The skill stops while these placeholders remain. The public commit email in the same file can stay unset — the skill asks for it once and records it.

**2. Repo facts.** The same file describes how the repo is run: license location, `.gitignore`, versioning, and commit message format. Edit each to match your repo. The license line matters most: it decides whether the skill deletes per-skill license files.

**3. Private terms.** The scan can't guess your name, your vault names, or your client names. It reads them from `~/.config/leak-scan/private-terms` (or the path in `$LEAK_SCAN_PRIVATE`). One rule per line, a severity then a regular expression:

```
# high and medium are errors; low is a warning
high (?i)jane[\s_\-.]*doe
medium (?i)acme[\s_\-.]*notes
medium (?i)\bproject[\s_\-.]*falcon\b
```

Write each term so it matches every spelling: `[\s_\-.]*` between words catches `AcmeNotes`, `acme_notes`, `acme-notes`, and `Acme Notes`. The scan also splits joined-up names before matching. The file never ships — keep it out of any repo you publish. If it's missing on first run, the skill offers to create it from names it has already seen in the session.

## Bundled files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill instructions Claude follows during a run |
| `scripts/release_scan.py` | The scan: secrets, private terms, portability, leftover build files, binaries |
| `references/repo-conventions.md` | Your staging/repo paths, repo facts, triage criteria, public commit email — configure before first use |
| `references/mechanical-pass.md` | The uniform changes applied without confirmation |
| `references/judgment-pass.md` | Keep/remove decisions that need your input, including leaks a scan can't see |
| `references/output-path-conventions.md` | Where a published skill should write its files, by output type |
| `references/reviewer-prompt.md` | The prompt for the Stage 7 reviewer agent |
| `references/readme-template.md` | Structure and writing rules for the public README the skill generates |

## Related

The secret patterns and the private-terms file format follow [sanitize-public](https://github.com/imisic/claude-marketplace/tree/main/plugins/sanitize-public), so one private-terms file serves both. Use sanitize-public for a general leak gate on any repo, including its git history. Use this skill to turn a personal skill into a public one.

## Changelog

### 2026-11-16

- Removed `effort: high` from the skill. It runs at your session's effort level.
- The README's sample scanner output uses a current model ID.

### 2026-11-15

- Renamed from `skill-sanitizer`.
- New scan script (`scripts/release_scan.py`) replaces the final grep sweep. It catches secrets (API keys, tokens, private keys, credential assignments), your private terms, home paths, custom agents, MCP tools, hooks, sibling skills, model pins, and leftover `__pycache__`/`.DS_Store` files, and lists binaries to open by hand. Secrets are masked in its output.
- Private terms now live in a local file outside the skill, so the published skill never contains them. The scan refuses to run without it.
- Stage 7 adds a fresh reviewer agent that checks what the scan can't: trigger collisions, hidden dependencies, setup a stranger couldn't follow.
- Judgment pass adds a checklist for leaks no scan can catch.
- Stage 8 checks that your next commit uses your public email.
- Output paths follow a decision table by output type instead of always defaulting to the current folder.
- Repo facts (license, versioning, commit format) are now marked as settings to configure, and the license rule never deletes a license file without asking.
- Manual-only: the skill now sets `disable-model-invocation`, so it runs only when you type the command.
- Stage 8: the optional validation run now uses `/claude-api prompt-audit` (or `/doctor prompt-audit`) in place of skill-critic, which has been retired from this repo.
- Mechanical pass: strips only vault frontmatter fields and keeps every Claude Code field (`model`, `allowed-tools`, `hooks`, `when_to_use`, and others). It previously kept just five fields and would remove working configuration.
- Non-interactive runs: when copies of a skill differ, the copy at the given path wins and every difference is listed in the report.
- Rules now state their reason instead of citing past runs.
- Judgment-pass examples no longer name specific cities.

### 2026-07-17

- Initial public release.
