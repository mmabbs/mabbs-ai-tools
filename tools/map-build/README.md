# Map Build

Design a build as a graph before anyone writes a spec. You describe what you want to build. Claude walks you through it one piece at a time, explaining its reasoning out loud. It starts from the smallest design that could work: one agent or process in a loop. Each extra part has to earn its place. A separate skeptic agent then reviews the design, you confirm it, and you get a markdown note plus an interactive HTML page you can come back to later.

It's built for two goals at once: a sound design, and you understanding that design well enough to explain it yourself. It works for any kind of build, like a SaaS product, a game system, an industry workflow tool, or an agent pipeline.

1. **Orient.** Claude reads the inputs you name and says what it learned and what's still open.
2. **Name the job.** It covers what the build does, what "done" looks like, and what starts it.
3. **Start as one loop.** The whole build is described as one loop with a checker and a stop condition, plus where that strains.
4. **Test the five reasons.** A part splits off only for one of five reasons: a distinct specialty, a parallel fan-out, a different model or tools, auditable routing, or an overloaded checker.
5. **Build the graph one piece at a time.** Each part is a node. Claude covers what each node is, what starts it, its job, and who may write each piece of shared data.
6. **Checks and failures.** Every output gets a checker, every loop gets a stop condition, and every node gets a failure path.
7. **Show the whole map.**
8. **Skeptic review.** A fresh agent stress-tests the design. Findings are shown word for word. Rejected findings get one rebuttal round.
9. **Check understanding.** Claude asks you two "what happens if…" questions before asking for approval.
10. **The gate.** You confirm, or say whether your "no" means "I don't follow" or "I disagree."
11. **Write the outputs.** You get a versioned note (`graph-<name>-v<N>.md`) and an interactive page (`graph-<name>-v<N>.html`).

## Sample output

Open [`references/demo-market-brief.html`](references/demo-market-brief.html) in a browser to see a finished page. It maps a "Morning Market Brief" build, with five parallel researchers, a merge step, a writer, a checker on a different model, a score router, and a person who approves. You can step through it in the order it runs or in the order the design grew. Click any node or lettered edge for its explanation.

The note gets tables generated from the same data:

```markdown
| # | Node | What it is | Job | Why it exists |
| --- | --- | --- | --- | --- |
| 1 | Morning schedule | Schedule · daily 6:00 am | Trigger | Required by the job |
| 2 | Planner | Agent · Opus 5.5 | Coordinator | Reason 1 |
| 3 | Researcher | Agent · Sonnet 4.6 | Worker | Reason 2 |
| 6 | Synthesizer | Agent · Sonnet 4.6 | Merge | Reason 2 |
| 7 | Writer | Agent · Opus 5.5 | Worker | Starting loop |
| 8 | Checker | Agent · Opus 4.6 · read-only | Checker | Reason 5, also 3 |
| 9 | Score router | Script · plain rules | Coordinator | Reason 4 |

### If a node fails

3. Researcher: If its source is down, it retries once, then writes a gap note instead (edge B). The other four carry on.
8. Checker: If it errors out, the draft goes to you marked "unchecked." It never ships as if it had passed.
```

It also gets an edge table, a who-writes-what table for shared state, a list of cut nodes, and a mermaid flow diagram.

## Requirements

| Component | Required? | Without it |
| --- | --- | --- |
| Claude Code | Required | — |
| `skeptic` agent (bundled in `agents/`) | Required | Step 8 can't run. The skill has no review step without it. |
| Opus access | Recommended | The bundled skeptic is pinned to `claude-opus-5-5`. Edit its `model:` line to a model you can use, or step 8 may not run. |
| Python 3 | Required | The page and the tables can't be built or checked. |
| Node.js | Optional | `extract` can't read the hand-written demo page. Pages the script builds are plain JSON and don't need Node. |
| Internet access when viewing the page | Required | The page loads its layout library (dagre) from cdnjs. Offline, the graph doesn't draw. |

## Installation

```bash
git clone https://github.com/mmabbs/mabbs-ai-tools.git
mkdir -p ~/.claude/skills ~/.claude/agents
cp -r mabbs-ai-tools/tools/map-build ~/.claude/skills/map-build
cp mabbs-ai-tools/tools/map-build/agents/skeptic.md ~/.claude/agents/skeptic.md
```

If Claude Code is already running, restart it so it picks up the agent.

If you already have an agent named `skeptic`, rename the bundled one (its file and its `name:` line). Then change "the `skeptic` agent" in `SKILL.md` step 8 to the new name.

## Usage

The skill runs only when you call it. It never triggers on its own.

```
/map-build a nightly job that pulls support tickets, tags them by urgency, and drafts replies for a person to approve
```

Name any docs Claude should read first, like a brief, notes, or an existing design. Claude asks which project the graph belongs to and where to save the outputs. Plan for a back-and-forth conversation: Claude stops after each design step so you can react.

To change a confirmed graph later, run `/map-build` again and point it at the old HTML page. The script pulls the data back out of the page, and the walkthrough produces the next version. Old versions are never overwritten.

## Bundled files

| File | What it's for |
| --- | --- |
| `SKILL.md` | The walkthrough Claude follows, including the five reasons a node can exist. |
| `agents/skeptic.md` | The read-only design reviewer used in step 8. It also works as a general design skeptic. |
| `references/node-names.md` | How to name and describe nodes in plain words, with a worked example. |
| `references/graph-data.md` | The format of the graph data and its content rules. |
| `references/demo-market-brief.html` | A finished example page. It's also the template that `build` fills. |
| `scripts/graph_page.py` | `check` enforces the content rules, `build` writes the page, `tables` prints the note's tables and mermaid diagram, and `extract` pulls the data back out of a page. |

## Changelog

### 2026-11-16

- Initial public release.
