# Repo Conventions

The paths, triage criteria, and gate checklist for this publishing pipeline. This file is user-specific — replace the placeholder paths below with your own before first use.

## Paths

<!-- Configure: replace each path with your actual directories -->

| Location    | Path                                                                    |
| ----------- | ----------------------------------------------------------------------- |
| Staging     | `/path/to/your/staging/directory/`                                      |
| Local repo  | `/path/to/your/local/skills-repo/`                                      |
| Repo skills | `skills/<skill-name>/` inside the local repo                            |
| GitHub      | `https://github.com/your-username/your-skills-repo/`                    |

## Repo facts

<!-- Configure: these describe one example repo. Edit each to match yours. -->

- **License is `<your-license>`, held at `<license-location>`.** If your repo holds one license at its root, delete per-skill license files during sanitization. Otherwise keep each skill's license file. Never delete a license file that carries a third-party notice — ask the user first. If `<your-license>` or `<license-location>` is still a placeholder, keep every license file and ask.
- **If your root `.gitignore` covers `.DS_Store` and `__pycache__/`, don't add per-skill gitignore files.** The mechanical pass deletes these artifacts anyway — the gitignore is backstop, not cleanup.
- **The repo README lists every published skill.** Adding a skill means adding its row: name, one-line description, link to its folder — e.g., `| [skill-name](skills/skill-name/) | One-line description of what it does |`. If the table doesn't exist yet, create it with those two columns.

## Blockers and advisories

The publish decision is the user's alone — sanitizable issues are never rejection reasons, and there is no Ship/Don't-ship verdict to give.

**Blockers** — objective defects; the repo move waits until they're resolved:

- Broken file references, or scripts the SKILL.md depends on that don't exist
- Referenced agents with no definition anywhere (never fabricate one — see mechanical pass item 10)
- Half-built features the instructions rely on

Name what needs building. Finish all sanitization work anyway so it's ready the moment the blocker clears.

**Advisories** — say once, prominently, then proceed. The user weighs them; the skill never acts on them:

- **Placeholder-shell observation.** If after sanitization every step carries a "replace with your own" placeholder or `# Configure:` comment, say so plainly: nothing but the user's configuration remains, and generic verbs (count, read, list, rebuild — things Claude does unprompted) don't count as kept mechanism. The user decides whether that's worth publishing.
- **Built-in overlap.** Heavy overlap with a built-in or shipping feature — name the feature and the remaining gap.
- **Unverifiable claims.** Core claims that verification can't support — flag them; the positioning rewrite in the judgment pass handles the wording.

## Final scan (the gate)

Run `scripts/release_scan.py` over the staging copy before anything moves to the repo (SKILL.md, Stage 7).

- **The private terms live outside the skill.** They are in `~/.config/leak-scan/private-terms`, never in this file or any file that ships. Add a term there the first time it turns up in public content.
- **Every error gets resolved or justified out loud.** The scan finds candidates, not verdicts — "obsidian" in a genuinely Obsidian-coupled skill is fine; a real home path never is.
- **Nothing moves to the repo until the scan output is accounted for.** Git history is permanent — a secret fixed in a later commit is still leaked.

## Public commit identity

| Field | Value |
| --- | --- |
| Public commit email | _unset — ask the user once, then record it here_ |

- **Compare against this before every commit offer** (SKILL.md, Stage 8). If the field is unset, ask the user which email they publish under and record the answer here.

## Versioning and changelog

- **Each published skill's README ends with a `Changelog` section** using dated `### YYYY-MM-DD` entries. Add an entry on first publish and on every update that reaches the repo.
- **Default: no semver, no git tags.** Dated entries carry the history. Change this if your repo uses version numbers or tags.
- **Default commit message format:** `Add skill: <name>` or `Update <name>: <what changed>`. Change it to match your repo's style.
