# Graph Data Guide

How to write the graph data that drives both outputs: the HTML page and the note's tables. Read this before step 5 of the walkthrough, when you start saving the graph data. The worked example is the data block in `demo-market-brief.html`. To see it as JSON, run `python3 <skill-folder>/scripts/graph_page.py extract <skill-folder>/references/demo-market-brief.html demo.json`. `<skill-folder>` is the folder that holds this skill's `SKILL.md`.

## Contents

1. The data at a glance
2. Nodes
3. Edges
4. Steps
5. Text tokens
6. Content rules
7. Large graphs

## 1. The data at a glance

One JSON object with these keys:

1. `title`: the build's name.
2. `subtitle`: one sentence saying what the build does.
3. `roles`: the seven node jobs. Copy them from the demo unchanged.
4. `reasons`: the five reasons a node can exist. Copy them from the demo unchanged.
5. `groups`: boxes that fold into one node. Empty list if none.
6. `nodes`: every node, including cut ones.
7. `edges`: every edge, including cut and temporary ones.
8. `steps`: two step orders, `run` and `build`.
9. `glossary`: a one-sentence plain definition for every `{term}` used. Always include `graph`, `node`, `edge`, and `shared state`.

- **Never change the colors, shapes, or layout code.** They live in the template, not the data. The data only says what each node is.

## 2. Nodes

Required fields:

1. `id`: short, lowercase, no spaces. Used in tokens.
2. `label`: the name on the node.
3. `sub`: the small second line. What it's built from, and its model if it has one.
4. `role`: its job, which sets the color. One of `trigger`, `coordinator`, `worker`, `checker`, `merge`, `human`, `store`.
5. `build`: what it's made of, which sets the shape. One of `model`, `code`, `store`, `event`, `person`.
6. `why`: why it exists (every node that isn't cut). See below.
7. `card`: `headline`, `what`, `fail`, and `rw` (reads and writes). Shared-state stores also get `table`.

Optional fields:

8. `kind`: the type shown next to the name on its card. Defaults from `build`.
9. `external`: `true` for anything outside the user's control, like a third-party API. Draws a dashed outline.
10. `layer`: `data` for stores and data sources. They show by default, and "Hide data" hides them.
11. `count`: number of parallel copies. Draws stacked cards. Pair it with `tag: "×N"`.
12. `tag`: a short pill at the top right, like `×5` or `cut`.
13. `group`: the id of the group box it sits in.
14. `ghost`: `true` for a node that was considered and cut. It needs `card.cut` instead of the other card fields.

- **Pick `build` by what the node is made of, not by how important it is.** A billing service is `code`. A Postgres table is `store`. A game's physics system is `code`. An LLM step is `model`. A person's approval is `person`. A cron schedule, a webhook, or a button press is `event`.
- **Use `store` only for data the build owns.** An outside system you reach through its API, like a firm's practice-management software or a calendar service, is `code` with `external: true`, even when its job is holding data. Its role can still be `store`.
- **Set `kind` whenever the default word undersells the node.** Defaults are Agent, Script, Stored data, Event, Person, and Outside service. Use "Web app," "Database," "Game system," "Service," or "Hook" when they're more accurate.
- **Name a model in `sub` only if the user chose it.** Otherwise write "Agent · model not chosen yet." The user owns model choices.

### why

Every node that isn't cut has exactly one of three types:

1. **`start`:** the one node the graph grew from. Exactly one per graph. It needs no reason.
2. **`earned`:** the node split off because a reason forced it. Give `main` (1 to 5) and, if a second reason also applies, `also` (a list).
3. **`required`:** the job can't run without it: triggers, data sources, stores, a person's approval. It isn't split off from the loop, so it needs no reason.

- **If a node has `also`, write the text in two parts: "Main reason: ... Also: ..."** The user needs to see which reason carries the weight. Never list two reasons as equals, and never lead with the minor one.
- **Say in the text what would go wrong without the node.** "Reading five sources one after another was the slowest part" beats "for parallelism."

### The who-writes-what table

- **Give every shared-state store a `table` of rows: data, the only node allowed to write it, and who reads it.** One writer per row. If two nodes write the same data, that's a design problem to raise in the walkthrough, not a row to write.

## 3. Edges

Fields:

1. `id` (required): a short id, used in `{@id}` tokens.
2. `from` and `to` (required): node ids.
3. `style` (required): `solid` (always happens), `dashed` (only sometimes), or `dotted` (data moving).
4. `layer`: `data` for dotted edges, `fail` for failure paths. Both show by default and can be hidden.
5. `label`: short text on the edge. Required for dashed and dotted edges.
6. `card`: `headline` and `text`. Edges with a card get a letter.
7. `kind` (required with a card): the edge type shown on its card, like "Fan-out," "Conditional," "Conditional · loop-back," "Failure path," or "Trigger."
8. `ghost`: an edge to or from a cut node.
9. `buildOnly`: a temporary edge shown only in "How we built it." Needs `until`, the last step index (counting from 0) it shows at.

- **A dashed edge's label is the rule that decides it:** "score below 8 · max 2 rounds," not "retry."
- **Every conditional needs a labeled edge for each way it can go.** If a node can send work to three places, draw all three.
- **A dotted edge's label names the data that moves:** "articles," "draft," "routing log." Never a verb like "reads," because the arrow already shows the direction.
- **The arrow on a dotted edge points the way the data travels.** Data coming from an API or store points into the node that receives it. A write points into the store.
- **Start a failure path at the thing that fails.** A source going down starts at the source, not at the node downstream.
- **End a failure path where the work goes next.** If the work waits in place, end it at whoever is told to act.
- **Give a card to every edge the user needs explained:** fan-outs, conditionals, loop-backs, and every failure path. Plain "draft" or "merged notes" handoffs don't need one.
- **Use `buildOnly` edges to keep "How we built it" connected.** In early build steps, the real edges don't exist yet. A temporary edge like "one loop did everything" shows what connected the pieces at that point.

## 4. Steps

`steps.run` is the order the build runs. `steps.build` is the order the design grew in the walkthrough.

- **Every node, cut ones included, appears exactly once in each order.**
- **The build order starts with the starting loop and its trigger.** Each later step adds the nodes one reason earned, in the order the walkthrough added them.
- **Add a required-by-the-job node in the build step that first needed it,** usually alongside the node that uses it. A calendar arrives with the scheduler that books into it.
- **Put a cut node in the step where it was considered.** In `run`, place it next to the node that made it unnecessary.
- **Every step has a short title and two or three sentences of text.** The text says what happens and uses graph terms as `{term}` tokens.
- **Don't write reason numbers in step titles.** The page adds a reason chip for each node in the step automatically.

## 5. Text tokens

Any text can use three tokens. The page fills in numbers and letters from the current step order, so they never go stale.

1. `{fan-out}`: the term in bold, with its glossary definition on hover.
2. `{@eLoop}`: "edge C," or whatever letter the edge has in the current order.
3. `{#state}`: the node's name, highlighted and linked on hover.

- **Never type "edge B" or "node 3" into text.** Use a token. Hand-typed labels break when the step order changes.
- **Never reference an element before it appears.** A card can only name nodes and edges revealed at or before its own step, in both orders. `check` catches this. When it fails, reword the text instead of reordering steps just to pass.
- **Every `{term}` needs a glossary entry.** Use the term every time it applies. Repeated exposure is the point.

## 6. Content rules

- **The page must stand on its own a week later.** The user won't reread the chat. Every node says what it is, why it exists, what happens when it fails, and what it reads and writes.
- **Write in plain English and keep the technical terms.** Use the term, and let the glossary and the sentence around it carry the meaning.
- **Card headlines are one sentence, visible when collapsed.** Put the detail in `what`.
- **`fail` says what actually happens, not "handle errors."** Retry how many times, then what? Where does the work go? Who finds out?
- **Never invent a failure the walkthrough didn't settle.** Write "Not settled yet." and list it under Open questions in the note. `check` warns on these so they don't get lost.

## 7. Large graphs

- **Past about 12 nodes, group related nodes.** Name groups the way the user would: "Backend," "Game loop," "Research stage." Each group folds into one node on the page.
- **Keep one node per real part.** Five parallel copies are one node with `count: 5`, not five nodes.
- **Keep `run` steps to one idea each.** A step can reveal several nodes when they happen together, like a worker, its data source, and the store it writes to.
