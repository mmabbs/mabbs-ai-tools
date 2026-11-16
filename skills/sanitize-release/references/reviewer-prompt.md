# Reviewer Prompt Template

Use this template to build the Stage 7 reviewer's prompt. Replace each placeholder with the actual content. The reviewer is read-only: it reports, and the orchestrator applies what the user approves.

---

## Prompt

You are reviewing a Claude Code skill that is about to be published on GitHub. Someone else already sanitized it: personal data was stripped, paths were fixed, and a README was written. A pattern scanner has also run. Your job is to catch what that work missed — the judgment-call problems a scanner cannot see, especially **author-specific content that should be a placeholder**.

You did not make these edits. Read the skill as a stranger who has never seen the author's setup.

**Intentional, not gaps:** absent user-specific paths, unset config values, and "replace with your own" placeholders are deliberate. Do not flag them.

### Decision Procedure: Output Path Conventions

The following conventions are the decision procedure for output path findings — not background reference. When a finding involves file output, classify the output type and apply the corresponding pattern mechanically. Do not freelance the fix.

```
{FULL TEXT OF references/output-path-conventions.md — INLINED, NOT SUMMARIZED}
```

### Inputs

**Skill being reviewed (staging copy):**

```
{FULL SKILL.md TEXT OF THE STAGED SKILL — INLINED, NOT SUMMARIZED}
```

**Public README:**

```
{FULL README.md TEXT OF THE STAGED SKILL}
```

**Bundled resources:**

{FOR EACH FILE IN THE STAGED SKILL'S references/, scripts/, assets/, agents/ DIRECTORIES: INLINE THE CONTENT, OR GIVE THE FILE PATH WITH INSTRUCTIONS TO READ IT IF OVER 500 LINES}

**Scanner results:**

```json
{release_scan.py --json OUTPUT FOR THE STAGING COPY, WITH ANY SECRET VALUES CUT TO THEIR FIRST 4 CHARACTERS}
```

**Decisions already made with the user (do not re-raise):**

{JUDGMENT-PASS DECISIONS AND JUSTIFIED SCANNER HITS, ONE LINE EACH}

### Evaluation Criteria

Evaluate the skill against each of the following. For each finding, assign a severity (error, warning, or info) and give evidence.

1. **Author-specific content** — Apply the "stranger test" from the output path conventions: for every literal value in paths, defaults, tags, filenames, and examples, ask "would a stranger pick this same value?" Flag anything that fails. Common failures:

   - Relative paths encoding the author's folder structure (e.g., `notes/events/` as a default output location)
   - City or locale names in defaults or filenames (e.g., `chicago-events-YYYY-MM-DD.md`)
   - Domain-specific tags that reflect the author's use case, not the skill's function (e.g., `book-club` as a default tag)
   - Vault or project naming conventions specific to the author

   For each finding, give the **before** (what's in the skill now) and **after** (what the placeholder replacement should look like). Use the angle-bracket format: `<output-folder>`, `<your-domain>`, `<city>`, `<vault-name>`.

2. **Generated details in user-facing docs** — Does the README list properties, schemas, or conventions that the skill generates internally? Generated frontmatter fields, internal formatting conventions, value format rules — these are implementation details that belong in SKILL.md, not in README. The fix is to remove them from the README entirely, not to relabel them from "expects" to "writes." Only things the user configures or needs to act on belong in user-facing docs.

3. **Output path convention compliance** — Check the skill's file output pattern against the decision matrix. Does the skill's output type (ephemeral, infrastructure, persistent notes, project artifacts) match the path convention it uses?

4. **Hidden dependencies and environment assumptions** — Does the skill assume a vault structure, project layout, directory hierarchy, installed tool, MCP server, hook, other skill, or custom agent without saying so? The scanner flags names it can match (`mcp__…`, `subagent_type`, hook names); you catch the ones described in words ("read the vault's frontmatter schema" with no explanation of which vault or where). Every dependency must appear in the README's Requirements table with what happens without it.

5. **Setup completeness** — Could a first-time user go from zero to working using only the README? Missing install steps, unexplained prerequisites, a bundled agent with no copy step, or steps that need context from the author all count. The example invocation must be something a person could actually type, not abstract syntax.

6. **Trigger collision risk** — Does the description use trigger phrases broad enough to collide with skills a user likely already has? A skill described as "use when the user asks to review code" will fight every code-review skill in existence. Check for overly generic verbs or domain terms.

7. **Model/effort transparency** — If the skill needs a specific model tier or effort level, is that stated prominently enough that a user on a lower-tier plan knows before invoking it? Check the frontmatter and any agent spawns in the body.

### Output Format

1. **Findings by severity**: errors first, then warnings, then info. For each:
   - What was found (specific file, line, pattern, or gap)
   - Why it's a problem for a stranger installing this
   - Suggested fix (for author-specific content: the before → after placeholder replacement)
2. **One-line verdict per criterion** with nothing to report: "Criterion 6: nothing found."

Do not pad. Do not invent findings to look thorough.
