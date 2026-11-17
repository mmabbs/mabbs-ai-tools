# Node Names and Descriptions

How to name and describe nodes so the user can judge a node list without asking what each one means. Read this before step 4 of the walkthrough.

## Contents

1. Common patterns
2. Renames that worked
3. Worked example: six nodes

## 1. Common patterns

These are starting points, not names. Pick the one that fits, then name the node after its specific job in this build.

1. **Verifier:** checks another node's output against a fixed rule before it moves on. Specific versions: "Status checker," "Gap checker."
2. **Skeptic:** argues against a design or a decision from fresh context. It never sees the reasoning it's judging.
3. **Writer:** produces a draft or a document from other nodes' output.

- **Watch for a pattern name that clashes with a person in the graph.** If the build has a human writer, an agent that drafts can't also be "Writer." Name it after what it drafts.

## 2. Renames that worked

Each first name told the user nothing they could judge. Each second name says what the node does.

1. "Authority checker" → "Status checker." "Authority" was a term from the source docs, used without saying authority of what.
2. "Filer" → "Organizer." "Filer" hid the three decisions the node makes.
3. "Impact finder" → "Ripple checker." "Impact" of what, on what, was unclear.
4. "Coordinator" → "Run script." "Coordinator" is a job type, not a name. What it coordinates is the order of one run, and it's a script.

## 3. Worked example: six nodes

From the Morning Market Brief graph in `demo-market-brief.html`. Match its level of detail: what the node reads, what it decides, what it produces, what it never does, and a concrete example wherever a rule could be misread.

1. **Writer (the starting loop).** It reads the merged notes and turns them into a one-page brief. When a draft comes back, it reads the comments attached to it:
   - from the Checker: "The second item says rates rose 0.5%. The notes say 0.25%."
   - from the person who approves the brief: "Lead with the earnings story, not the rate news."

   It fixes only the points raised and leaves the rest of the draft alone. It never scores its own draft, and it never decides whether the draft is ready. Its output is the draft, written to its slot in the shared state.
2. **Researcher ×5.** Five copies run at once, one per source. Each copy pulls today's articles from its source and writes short notes with a link back to each article. A separate summarizer was cut, because each researcher already summarizes its own source. A copy that can't reach its source retries once, then writes a gap note: "Source 3 was down at 6:05. Nothing from it today." It writes only to its own notes slot and never reads the other four.
3. **Synthesizer.** It reads all five note slots and makes two decisions:
   - Which notes are the same story told by two sources? It keeps one and lists both sources.
   - Did fewer than three sources come back? If so, it stops and flags the run as thin instead of passing on weak notes.

   Its output is one merged set of notes. It's the only node that writes the merged notes, so no researcher's notes get overwritten.
4. **Checker.** It reads the draft and the merged notes, checks every claim in the draft against the notes, and scores the draft out of 10, with a comment for each problem. Example: "Claims the merger closed Tuesday. No note says when it closed." It runs on a different model from the Writer, so it doesn't share the Writer's blind spots. It's read-only: it can judge the draft but never edit it, and it never decides where the draft goes next.
5. **Score router.** It's a script, not an agent. It reads the Checker's score and the round count, then applies fixed rules:
   1. Below 8, and fewer than two rounds so far: back to the Writer.
   2. 8 or higher: on to the person for approval.
   3. Still below 8 after two rounds: on to the person, flagged.
   4. Score missing or unreadable: on to the person, marked "unchecked."

   It logs every decision with its reason. The rules never change, so it doesn't need a model.
6. **Publish.** A script. It reads the approved draft, formats it, and posts it to the inbox. It runs only after the person approves, and it writes nothing back to the shared state. If posting fails, it retries once, then alerts the person. A formatter agent was considered and cut: formatting is fixed and predictable, so it needs no model.
