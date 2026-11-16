---
name: sanitize-release
description: "Ready a personal Claude Code skill for public GitHub release. Use when the user wants to sanitize, publish, stage, release, or audit a skill before it goes public, or asks whether a skill is safe to share. Scans for secrets, private names, and portability problems, copies to staging, strips personal data, writes the public README, runs an independent review, and gates the repo move."
when_to_use: "The user wants to share a skill outside their own setup, or remove personal data from a skill before others see it."
argument-hint: <path-to-skill-folder>
disable-model-invocation: true
effort: high
---

# Sanitize Release

Transform a personal Claude Code skill into a copy ready for the public GitHub repo. All work happens on a staging copy — the live skill is never edited.

Two kinds of problem stop a skill from going public. **Leaks**: secrets, private names, personal paths. **Portability gaps**: things that only work on the author's machine, like custom agents, MCP servers, hooks, or the author's folder layout. A bundled scanner catches both mechanically. A fresh reviewer agent catches what the scanner can't. You handle the judgment calls with the user.

## Inputs

- **Path** (required): the skill folder to sanitize. Usually a live skill under `~/.claude/skills/` or an existing staging copy.
- **Context** (optional): known issues, areas of concern, or publishing history. Include in the message after the path.

## Ground Rules

- **Never edit the live skill.** Every transformation happens on the staging copy. Before any Edit or Write to the skill being sanitized, check the file path starts with the staging directory. If it doesn't, stop.
- **Three writes outside staging are part of the process.** Creating the private-terms file (Stage 0), recording the public commit email in this skill's `references/repo-conventions.md` (Stage 8), and the repo move (Stage 7: copying into the repo and updating its README and changelog). Do these without stopping.
- **Announce each stage as you enter it.** One line: stage name and what's about to happen. No silent gaps between stages.
- **Read `references/repo-conventions.md` before Stage 1.** It holds the staging and repo paths, the triage criteria, the gate checklist, and the public commit identity. If its Paths table still contains placeholder values, stop and ask the user to configure them per the README's Configuration section — with placeholder paths, the staging copy and the repo move have nowhere real to go.
- **If running non-interactively** (no user available to confirm), apply the recommended option for each decision point and mark it `AUTO-APPLIED` in the report. Do not stall waiting for input that cannot come.
- **Never quote a secret back in full.** The scanner already masks secrets to their first 4 characters. Keep it that way in your own reports and edits: name the type and location, never the full value. A report is one more place a secret can leak from.

## The Scanner

`scripts/release_scan.py` reads every file in a folder and reports findings in four groups: secrets, private terms, portability, and workspace artifacts. It also lists binary files (images, PDFs, archives) that no scan can read.

```bash
python3 -B "${CLAUDE_SKILL_DIR}/scripts/release_scan.py" <folder>
python3 -B "${CLAUDE_SKILL_DIR}/scripts/release_scan.py" <folder> --json
```

Exit codes: `0` no errors, `1` errors found, `2` bad invocation, `3` private-terms file missing or empty. Run it with `-B` so Python writes no `__pycache__`. Secrets are printed masked to their first 4 characters.

**Private terms** are the user's own names and identifiers: their name, vault names, private project names, client names. The scanner can't guess these, so it reads them from a local file: `$LEAK_SCAN_PRIVATE` if set, else `~/.config/leak-scan/private-terms`. One rule per line, `<high|medium|low> <regex>`. The file never ships and is never copied into a skill. Joined-up names (`AcmeNotesVault`) are split into words before matching, so a term inside an identifier is still caught.

## Stage 0 — Private Terms Check

Run the scanner once on the target folder. If it exits `3`, stop. A scan without the user's private terms passes everything that matters, and its clean result is false comfort.

1. Tell the user the private-terms file is missing or empty, and where it should be.
2. Offer to create it, seeded with private identifiers already visible in this session: the user's name and username, vault names, private project names. Show the proposed rules before writing.
3. Write each rule to match every spelling: `medium (?i)\bfoo[\s_\-.]*bar\b` catches `FooBar`, `foo_bar`, `foo-bar`, and `Foo Bar`.
4. Continue only once the file has rules. Use `--no-private` only if the user explicitly says to proceed without one, and say in the final report that the private layer was skipped.

In non-interactive runs, do not create the file. Stop and report that it is missing.

## Stage 1 — Canonicalize

Skills drift across copies. A staging copy from last month may be missing content the live skill gained since — or vice versa.

1. Locate every copy of the skill: the given path, `~/.claude/skills/<name>/`, and the staging directory. Ask the user if `.skill` exports or copies elsewhere exist (other Claude surfaces, vaults, backups). In non-interactive runs, skip the question and proceed with the copies found.
2. If more than one copy exists, diff them (`diff -ru`). Report qualitative differences — content one copy has that another lacks, not just whitespace.
3. Merge newer content into a single canonical version before sanitizing. Never silently pick one copy; show the user what differs and confirm the merge direction. In non-interactive runs, the copy at the given path wins: sanitize it, list every difference in the other copies in the report, and mark the decision `AUTO-APPLIED` so the user can re-run with a merged copy. The merge decision determines which content is canonical — Stage 4 writes the merged result to staging; no copy outside staging is ever modified.

## Stage 2 — Scan and Read Everything, Then Assess

1. Run the scanner on the canonical copy (`--json`). This is read-only and changes nothing.
2. Read every file in the skill: SKILL.md, references, scripts, assets. No edits during this stage — findings presented before files change is what keeps the punch list complete.
3. List every binary the scanner reported. Offer to open each one (`open <path>` on macOS, `xdg-open <path>` on Linux) so the user can check it by eye. A screenshot with a real terminal, path, or browser tab in frame leaks more than any string.

Present findings in three buckets, merging scanner hits with what your read found:

1. **Sanitization** — blocks repo entry: secrets, private terms, personal paths, names, vault coupling, proactive triggers, dependencies on agents, MCP servers, hooks, or other skills.
2. **Polish** — professionalism: structure, artifacts, naming, stale content.
3. **What Needs Writing** — missing README, adaptation sections, install docs.

Flag secrets separately and first. They are a higher severity tier than paths or names: a leaked path embarrasses, a leaked key compromises.

## Stage 3 — Blockers and Advisories

The publish decision belongs to the user. By the time this skill is invoked, they have already judged the skill worth sharing — never veto that judgment with a verdict of your own. From your Stage 2 findings and any structural issues the read surfaced, identify items that qualify as either of two kinds (definitions in `references/repo-conventions.md`):

1. **Blockers** — objective defects that make the copy non-functional for adopters: broken file references, missing scripts the SKILL.md depends on, referenced agents with no definition anywhere, half-built features. Blockers don't stop the sanitization work — they block the repo move at Stage 7 until resolved. Carry the list forward: restate any unresolved blockers at the end of each subsequent pass report, so the Stage 7 gate checks a current list rather than a memory from this stage.
2. **Advisories** — observations the user should weigh, stated once and prominently, then dropped: "after sanitization every step is a placeholder — nothing but your configuration remains," "this overlaps heavily with built-in X." Advisories never block and are never re-argued. Present them and proceed.

## Stage 4 — Copy to Staging

Copy the canonical version into the staging directory. If a stale staging copy exists, replace it — Stage 1 already harvested anything newer from it. Work on this copy from here on.

## Stage 5 — Mechanical Pass

Read `references/mechanical-pass.md` and apply every item. These run unconditionally — no confirmation needed. None of them depends on what the skill is for, so none needs the user's input.

After the pass, report what changed as a numbered list grouped by file.

## Stage 6 — Judgment Pass

Read `references/judgment-pass.md` and work through each call. These are keep/remove decisions that turn on what the skill is for and who it's for — context only the user has, so do not apply them silently.

Present all calls in one message: for each, the finding, your recommendation, and the reasoning. Apply only after the user decides.

## Stage 7 — Docs, Review, and Gate

1. **Write the public README** following `references/readme-template.md`.
2. **Scan the staging copy.** Run the scanner on it. Every error gets fixed or justified to the user out loud. Warnings get a one-line reason each if they stay. The scanner finds candidates, not verdicts — "obsidian" in a genuinely Obsidian-coupled skill is fine; a real home path never is.
3. **Run the fresh reviewer.** Spawn one agent (`subagent_type: "general-purpose"`, model `opus`) with the prompt built from `references/reviewer-prompt.md`. It did not make the edits, so it is not grading its own work. It checks what the scanner can't: trigger collisions, hidden dependencies, setup steps a stranger couldn't follow, author-specific defaults. Present its findings in severity order and apply only what the user approves.
4. **Re-check after fixes.** Re-run the scanner after any fix. Re-run the reviewer only if the fixes changed what the skill tells Claude to do, not just README wording.
5. **Move to the repo** only after the scan is accounted for **and no blocker is unresolved**: copy the skill into the publish repo's `skills/` directory, add or update its entry in the repo README, and add a dated changelog entry per the conventions file. An open blocker keeps all completed work in staging and the report says exactly what needs building — nothing enters the repo.

The gate is one-way. Secrets and personal paths that reach git history are permanent even after a fixing commit — nothing moves to the repo until the scan passes.

**The scan is the last operation that touches the staging copy.** If anything executes in staging after it — a validator, a test run, any script — generated artifacts reappear (`__pycache__/` embeds absolute paths in bytecode) and the scan is void. Delete generated artifacts and scan again before the repo move.

## Stage 8 — Handoff

None of these is automatic.

1. **Prompt audit** (optional): offer to run `/claude-api prompt-audit <staged path>` on the staged copy. It uses the `claude-api` skill bundled with Claude Code. If bundled skills are turned off, offer `/doctor prompt-audit` instead, which is built into Claude Code; check its usage first, since it may not accept a folder path. It flags instructions written for older models, hardcoded paths and version pins, and instruction files that contradict each other, and it proposes a diff without applying it. Worth offering because the staged copy stays structurally close to the live skill, so findings usually apply to the user's live version too. If accepted, add this note to the request: "This skill is designed for public distribution. Absent user-specific paths, unset config values, and 'replace with your own' placeholders are intentional — do not flag them." If the audit leads to edits in staging, re-run the Stage 7 scan before anything further moves to the repo.
2. **Commit identity check**: before offering a commit, compare the emails git will publish against the public commit identity in `references/repo-conventions.md`:
   ```bash
   git -C <repo> config user.email
   git -C <repo> log --format='%ae%n%ce' | sort -u
   ```
   `noreply@github.com` as committer comes from GitHub's web interface and is fine. If the next commit's email differs from the public identity, say so and offer a repo-local fix (`git -C <repo> config user.email <public-identity>`). If older commits carry a different email, report it. Do not rewrite history; that is the user's call, and pushed commits may already be cloned.
3. **Commit**: offer to commit the repo changes. Show the diff summary first. Stage only the files this run touched — the repo may hold unrelated uncommitted work.

Close with a one-paragraph report: outcome (published, or held in staging with blockers named), counts per pass, scanner and reviewer results, advisories raised, what was written, what's pending. Say plainly that a clean scan means the text patterns are clean, not that the skill is safe — the judgment pass and review are what make it safe.
