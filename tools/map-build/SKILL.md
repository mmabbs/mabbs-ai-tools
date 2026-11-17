---
name: map-build
description: Walk the user through a build as a graph (nodes, edges, shared state, checkers, stop conditions, failure paths) before any spec or plan exists. Reasoning is narrated at every step, a skeptic agent reviews the design, the user confirms it, and the result is saved as a markdown note plus an interactive HTML page. Runs only when the user types /map-build.
argument-hint: "[the build or project to map]"
disable-model-invocation: true
---

# Map Build

The user wants to understand what we're building before anyone writes a spec. This skill walks through the build as a graph, one piece at a time, with the reasoning out loud. Two goals carry equal weight: a sound design, and the user understanding it well enough to explain it themselves.

A graph here is the design of a system: the working parts (nodes), the connections between them (edges), and the data they share (shared state). A single loop is the smallest graph: one node with an edge back to itself. The default is always one loop. Every extra node has to earn its place.

## Ground Rules

- **Don't write specs, plans, or code while this skill runs.** It ends at the user's confirmation. If the user asks to skip ahead, name the steps that are left and ask whether to skip them. Their call.
- **Run the full walkthrough every time.** There's no short version for small builds. Even a single loop is worth seeing, because what it surfaces is the point.
- **Never assume the size or type of the build.** The build might be a SaaS product, a game, a workflow tool for a specific industry, or Claude Code infrastructure. Nodes can be services, databases, web apps, game systems, agents, scripts, hooks, or a person's manual step.
- **Work from the inputs the user names, not from project docs.** The graph comes before any spec, so never go looking for spec, plan, status, or overview files. A project's session-start reading list doesn't count as named inputs.
- **When a named input hands a topic to another doc, read that doc before judging the topic.** Lines like "see guide-question-versus-gap" or "per the anti-noise principle in X" are handoffs. The handed-off doc counts as a named input for that topic, so read it without asking first.
- **Never guess what an unread doc says.** Say "I haven't read it." Don't write "it probably says X."
- **If the user's decision conflicts with an input, flag it the moment you see it.** Quote both sides and ask which one wins. Don't quietly pick one, blend them, or save the conflict for later.
- **If the user names no inputs, ask what to read, or whether to start from their description alone.**
- **Read an earlier `graph-` version of the same build only when this run updates it.**
- **If the user didn't name a project, ask which one it belongs to, or whether it's new.**
- **Name a model only if the user chose it.** Model choices are theirs.

## How to Talk

- **Narrate the reasoning, not just the result.** "I'm making the checker its own node because the writer grading its own facts misses errors" teaches. "Added a checker node" doesn't.
- **Use the technical term every time it applies.** Give it a plain meaning in the same sentence the first time in a session: "a fan-out, where one step splits into copies that run at once." After that, use the term alone. Repeated exposure is how the user learns it. Don't write lecture sections that define terms.
- **If the user has their own terms for the build, use them every time.** They can come from their inputs or their messages. Don't swap in looser words of your own, like "passages" for Idea Units or "raw material" for a Brain Dump doc. If they have no terms of their own, plain words of your choosing are fine.
- **Add one piece at a time.** Show the whole map only at step 7 and at the gate.
- **Ask one question at a time** when you need the user's input.
- **Stop at the end of each step from 3 to 7 so the user can react before you go on.** A step can end early on a question. Steps 1 and 2 can share a message.
- **Refer to people in the graph by their role, and use they/them.** "The paralegal reviews it; they clear or decline."
- **Draw the growing graph as a small text diagram when a new connection changes the shape.** Skip it when a sentence does the job.

## Why a Node Exists

Every node gets exactly one of three labels:

1. **Starting loop.** The one node the graph grew from. It needs no reason. As other jobs split off, it keeps whatever core job is left, and keeps this label. Say which job it kept.
2. **Earned.** It split off because one of the five reasons below forced it. Name the main reason, and a second one only if it truly applies.
3. **Required by the job.** The job can't run without it: triggers, data sources, stores, a person's approval.

The five reasons:

1. **Distinct specialty.** The job needs its own instructions, context, and limits.
2. **Parallel fan-out.** Several copies run at once, then join back up.
3. **Different model or tools.** It needs a different model, or a different set of tools, from its neighbors.
4. **Auditable routing.** You must be able to show why work took one path over another.
5. **Overloaded checker.** One check was judging too many things, so checking split off.

- **If you can't name the reason for a node, fold it back into its neighbor.** Record it as cut, with why.
- **If a reason is present but an existing node already covers it, say so and add no node.** For example, auditable routing can become a rule that a person who's already in the graph logs every decision. Put the change in that node's description.
- **Before adding nodes to fix quality, strengthen the checker.** Half of "we need another node" is a weak checker in disguise.
- **Ask of every model-powered node: "does this need a model at all?"** Fixed, predictable steps are cheaper and safer as code.

## Naming and Describing Nodes

- **Name each node yourself, in plain words, after what it does.** "Status checker," "Ledger keeper," "Run script." The skill never supplies node names.
- **Never use a job type as a name.** The seven jobs (trigger, coordinator, worker, checker, merge, human, store) say what kind of job a node does, not which job. "Coordinator" tells the user nothing. "Run script" does.
- **Start from a common pattern when one fits, then make it specific.** `references/node-names.md` lists the patterns and a worked example of good names and descriptions.
- **Every time you list nodes, describe each one.** Say what it reads, what it decides or does, and what it produces. This covers step 4's results, step 5, the step 7 map, and the gate. A name and a label alone are never enough. A table of labels can sit next to the descriptions, never in place of them.

## The Walkthrough

From step 5 on, save the current graph data to the scratchpad as `graph-<name>.json` after each step, following `references/graph-data.md`. Read that guide before step 5. A long walkthrough can get compacted, and the file survives it.

### 1. Orient

- **Read the inputs the user named, then say in two or three lines what you learned and what's still open.**
- **Skip quizzing the user on concepts.** If a term comes up that they don't know, they'll ask.

### 2. Name the job

- **Pin down three things: what the build does, what "done" looks like, and what starts it.** "Done" becomes the first checker. "What starts it" becomes the first trigger.
- **Confirm whatever the user's opening message already answered, and ask only about the rest.**

### 3. Start as one loop

- **Describe the whole build as one agent or one process in a loop, with its checker and its stop condition.** Say plainly what that single loop would do well and where it would strain.

### 4. Test the five reasons

- **Go through the five reasons one by one and say whether each is present, and why.** Each reason that's really present earns a node. A reason that isn't present is still worth one sentence: "Reason 4 doesn't apply, because nothing here needs an audit trail."
- **Add the required-by-the-job nodes too:** triggers, data sources, stores, and people.

### 5. Build the graph one piece at a time

For each node:

1. **Say what kind of thing it is:** agent, script, service, database, web app, game system, hook, person, or event.
2. **Say whether it needs a model.**
3. **Say what starts it:** a trigger, an upstream node, a schedule, a person.
4. **Name its job:** trigger, coordinator, worker, checker, merge, human, or store.

For each edge, say whether it always happens, only sometimes (and the rule that decides it), or carries data. For shared state, name each piece of data and the one node allowed to write it. Two writers on the same data is a design problem to fix now.

### 6. Checks and failures

- **For every output, name who checks it before the next node uses it.** A node never checks its own work.
- **Give every loop a stop condition and every expensive part a limit.**
- **For every node, say what happens when it fails:** retry how many times, then where the work goes, and who finds out. One failure must not corrupt shared state or poison the nodes downstream.

### 7. Show the whole map

- **Show the node table with a description for each node, the edge list, the who-writes-what table, and a text flow diagram together.** This is the first time the user sees the whole picture.

### 8. Skeptic review

Send the graph to the `skeptic` agent. It reviews the design with fresh eyes, so the brief must not carry this conversation's reasoning.

- **Brief it with exactly five things:** the job in one line, the stakes (low, medium, or high), the user's hard constraints as plain facts with no arguments attached, the graph map from the scratchpad file, and the path to this file (`${CLAUDE_SKILL_DIR}/SKILL.md`) so it can read the five reasons. Never describe the build as small or as Claude Code infrastructure unless it is.
- **Show each finding's one-line summary word for word, next to your response.** Never paraphrase a finding into something milder.
- **Say which findings you accept before arguing against any.**
- **Send every rejected Critical or Major finding back to the same skeptic in one rebuttal message.** It concedes or holds each one.
- **If it holds a Critical finding, give it to the user.** Show both positions in plain words. The user decides, and the decision goes in the note.
- **Re-run the skeptic only if the nodes or edges changed.** At most once. After that, ask the user how to proceed.

### 9. Check understanding

- **Ask two prediction questions in plain words before asking for approval.** For example: "If the checker rejects the draft twice, what happens next?" or "Which node is allowed to change the task list?" Ask more only if the user wants them.
- **If the user answers correctly, go to the gate. If they miss one, re-teach that one relationship.** Don't restart the walkthrough.

### 10. The gate

- **Ask the user to confirm the graph.**
- **If they don't, ask which kind of "no" it is.** "I don't follow" goes back to teaching that part. "I disagree" goes back to the design step it concerns.

### 11. Write the outputs

Only after the user confirms.

1. **Pick the folder.** Use the folder the user named. If they named none, ask where to save.
2. **Pick the version.** The files are `graph-<name>-v<N>.md` and `graph-<name>-v<N>.html`. If earlier versions exist, use the next number. Never overwrite one. Add a one-line "Superseded by [graph-<name>-v<N>](graph-<name>-v<N>.md)" header at the top of the previous note.
3. **Finish the data, then run the checks.** Run `python3 "${CLAUDE_SKILL_DIR}/scripts/graph_page.py" check <data.json>` and fix every error. Warnings need a reason to stay.
4. **Build the page.** Run `python3 "${CLAUDE_SKILL_DIR}/scripts/graph_page.py" build <data.json> <folder>/graph-<name>-v<N>.html`.
5. **Generate the tables.** Run `python3 "${CLAUDE_SKILL_DIR}/scripts/graph_page.py" tables <data.json>` and paste the output into the note.
6. **Write the note.** If the folder's notes follow conventions, like frontmatter or naming, follow them too. Use these sections, dropping any that don't apply:
   1. **What we're building:** the job, what "done" looks like, and what starts it.
   2. **Where it started:** the single loop, and where it strained.
   3. **The graph:** the generated tables and mermaid diagram, plus a link to the HTML page.
   4. **Why each node exists:** the reasoning, in prose.
   5. **Checks and failures.**
   6. **Skeptic review:** each finding, what was accepted, what was rejected and why, and anything the user decided.
   7. **Open questions:** anything the spec has to settle.
7. **Open the HTML page in the browser:** `open` on macOS, `xdg-open` on Linux, `start` on Windows.

After step 11, spec and plan work can start, outside this skill.

## Updating a Confirmed Graph

- **To change a confirmed graph, start from its data.** Run `python3 "${CLAUDE_SKILL_DIR}/scripts/graph_page.py" extract <old.html> <data.json>`, then walk the user through what changes, using the same steps, and write the next version.

## Files

- **The five reasons live in this file.** The `skeptic` agent reads them from the section above, so keep its heading, "Why a Node Exists."
- **`references/node-names.md`:** common node patterns and a worked example of plain names and descriptions. Read it before step 4.
- **`references/graph-data.md`:** how to write the graph data, the content rules, and the text tokens. Read it before step 5.
- **`references/demo-market-brief.html`:** a complete worked example, and also the template `build` fills. Open it to see what a finished page looks like. Never edit its template code for one project.
- **`scripts/graph_page.py`:** `extract`, `check`, `build`, and `tables`.
