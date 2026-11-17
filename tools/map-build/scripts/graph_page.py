#!/usr/bin/env python3
"""Build, check, and summarize /map-build pages.

One data file drives both outputs: the interactive HTML page and the tables in
the markdown note. The HTML template is references/demo-market-brief.html; this
script swaps the block between its GRAPH-DATA markers.

Commands:
  extract <page.html> <out.json>      Pull the graph data out of any graph page (the demo included).
  check   <graph.json>                Enforce the content rules. Exit 1 on any error.
  build   <graph.json> <out.html>     Check, then write the page from the template.
  tables  <graph.json>                Print the note's tables and mermaid diagram as markdown.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "references" / "demo-market-brief.html"
START, END = "/* GRAPH-DATA-START */", "/* GRAPH-DATA-END */"

ROLES = {"trigger", "coordinator", "worker", "checker", "merge", "human", "store"}
BUILDS = {"model", "code", "store", "event", "person"}
STYLES = {"solid", "dashed", "dotted"}
LAYERS = {"flow", "data", "fail"}
ROLE_FILL = {"trigger": "#2cc4dc", "coordinator": "#4f8dfd", "worker": "#4ccf7a", "checker": "#f7bd35",
             "merge": "#a78bfa", "human": "#f27ab6", "store": "#c9a27a"}
TOKEN = re.compile(r"\{([@#]?)([^}|]+)(?:\|[^}]+)?\}")


def is_placeholder(text, m, gloss):
    """A non-glossary {...} sitting inside a path or name, like {project}/notes.md or draft-{N}.
    It stays as literal text. Mirrors isPlaceholder() in the template."""
    if m.group(1) or m.group(2) in gloss:
        return False
    before = text[m.start() - 1] if m.start() > 0 else ""
    after = text[m.end(): m.end() + 2]
    return bool(re.match(r"[\w/-]", before) or after[:1] == "/" or re.match(r"\.\w", after))


# ---------- reading and writing the data block ----------
def split_template(html):
    a, b = html.index(START), html.index(END)
    return html[: a + len(START)], html[a + len(START): b], html[b:]


def extract(page, out):
    _, block, _ = split_template(Path(page).read_text())
    body = block.strip()
    body = body[body.index("=") + 1:].strip().rstrip(";")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        # Hand-written blocks (like the demo) are JS object literals, not strict JSON.
        if not shutil.which("node"):
            sys.exit("extract: block isn't plain JSON and node isn't installed to read it.")
        js = f"const GRAPH = {body};\nprocess.stdout.write(JSON.stringify(GRAPH, null, 2));"
        data = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    Path(out).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}")


def build(data_path, out):
    data = json.loads(Path(data_path).read_text())
    if not check(data):
        sys.exit("build: fix the errors above first.")
    head, _, tail = split_template(TEMPLATE.read_text())
    block = "\nconst GRAPH = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    html = head + block + tail
    html = re.sub(r"<title>.*?</title>", f"<title>{data['title']}</title>", html, count=1)
    Path(out).write_text(html)
    print(f"wrote {out}")


# ---------- step order helpers (mirror the template's logic) ----------
def reveal(data, order):
    idx = {}
    for i, st in enumerate(data["steps"][order]):
        for nid in st["nodes"]:
            idx[nid] = i
    return idx


def edge_reveal(e, ri):
    return max(ri.get(e["from"], 10 ** 6), ri.get(e["to"], 10 ** 6))


def numbering(data, order):
    ri, nodes = reveal(data, order), {n["id"]: n for n in data["nodes"]}
    num, let, k, l = {}, {}, 1, 0
    for i, st in enumerate(data["steps"][order]):
        for nid in st["nodes"]:
            num[nid] = "✕" if nodes[nid].get("ghost") else str(k)
            k += 0 if nodes[nid].get("ghost") else 1
        for e in data["edges"]:
            if e.get("card") and edge_reveal(e, ri) == i:
                let[e["id"]] = chr(65 + l)
                l += 1
    return num, let


# ---------- rules ----------
def texts_of(obj):
    """Every string inside a card, why, or step, for token checks."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from texts_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from texts_of(v)


def check(data):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    edges = {e["id"]: e for e in data.get("edges", [])}
    groups = {g["id"] for g in data.get("groups", [])}
    gloss = data.get("glossary", {})
    reasons = {str(k) for k in data.get("reasons", {})}

    if len(nodes) != len(data.get("nodes", [])):
        err("Two nodes share an id.")
    if len(edges) != len(data.get("edges", [])):
        err("Two edges share an id.")
    if reasons != {"1", "2", "3", "4", "5"}:
        err("reasons must hold exactly the five reasons, keyed 1 to 5.")
    for key in ("graph", "node", "edge", "shared state"):
        if key not in gloss:
            err(f'glossary is missing "{key}". The page defines it under "The basics".')

    for n in nodes.values():
        nid = n["id"]
        if n.get("role") not in ROLES:
            err(f"Node {nid}: role must be one of {sorted(ROLES)}.")
        if n.get("build") not in BUILDS:
            err(f"Node {nid}: build must be one of {sorted(BUILDS)}.")
        if n.get("group") and n["group"] not in groups:
            err(f"Node {nid}: group {n['group']} isn't in groups.")
        card = n.get("card", {})
        if n.get("ghost"):
            if not card.get("cut"):
                err(f"Cut node {nid}: card.cut must say why it was cut.")
            continue
        why = n.get("why")
        if not why or why.get("type") not in ("start", "earned", "required") or not why.get("text"):
            err(f"Node {nid}: why needs a type (start, earned, or required) and text.")
        elif why["type"] == "earned":
            rs = [why.get("main")] + list(why.get("also", []))
            if any(str(r) not in reasons for r in rs):
                err(f"Node {nid}: earned reasons must be numbers 1 to 5.")
            if why.get("also") and "also" not in why["text"].lower():
                warn(f"Node {nid}: has a second reason, but the why text doesn't say which part is the 'also'.")
        for field in ("headline", "what", "fail", "rw"):
            if not card.get(field):
                err(f"Node {nid}: card.{field} is missing.")
        if re.search(r"[.!?]\s+\S", card.get("headline", "")):
            warn(f"Node {nid}: the headline is more than one sentence. It shows when the card is collapsed.")
        if card.get("fail", "").lower().startswith("not settled"):
            warn(f"Node {nid}: failure isn't settled. Make sure it's listed under Open questions in the note.")
        if n["build"] == "store" and n.get("layer") == "data" and not card.get("table"):
            warn(f"Node {nid}: a shared-state store with no who-writes-what table.")
    if sum(1 for n in nodes.values() if n.get("why", {}).get("type") == "start") != 1:
        err("Exactly one node must be the starting loop (why.type = start).")

    for e in edges.values():
        eid = e["id"]
        for end in ("from", "to"):
            if e.get(end) not in nodes:
                err(f"Edge {eid}: {end} node {e.get(end)} doesn't exist.")
        if e.get("style") not in STYLES:
            err(f"Edge {eid}: style must be one of {sorted(STYLES)}.")
        if e.get("layer", "flow") not in LAYERS:
            err(f"Edge {eid}: layer must be one of {sorted(LAYERS)}.")
        if e.get("buildOnly"):
            if not isinstance(e.get("until"), int):
                err(f"Temporary edge {eid}: until must be a step index.")
            continue
        if e.get("style") == "dashed" and not e.get("label"):
            err(f"Edge {eid}: dashed means 'only sometimes', so the label must give the rule.")
        if e.get("style") == "dotted" and not e.get("label"):
            err(f"Edge {eid}: dotted edges carry data, so the label must name the data.")
        if e.get("layer") == "fail" and not e.get("card"):
            warn(f"Edge {eid}: a failure path with no explainer card.")
        if e.get("card") and not (e.get("kind") and e["card"].get("headline") and e["card"].get("text")):
            err(f"Edge {eid}: a card needs kind, card.headline, and card.text.")

    linked = {e[k] for e in edges.values() if not e.get("buildOnly") for k in ("from", "to")}
    for nid, n in nodes.items():
        if nid not in linked:
            warn(f"Node {nid}: no edges touch it.")

    for order in ("run", "build"):
        steps = data.get("steps", {}).get(order)
        if not steps:
            err(f"steps.{order} is missing. Both orders are required.")
            continue
        seen = [nid for st in steps for nid in st["nodes"]]
        for nid in nodes:
            if seen.count(nid) != 1:
                err(f"steps.{order}: node {nid} appears {seen.count(nid)} times. Each node appears exactly once.")
        for nid in seen:
            if nid not in nodes:
                err(f"steps.{order}: unknown node {nid}.")
        for st in steps:
            if not st.get("title") or not st.get("text"):
                err(f"steps.{order}: every step needs a title and text.")

    # Tokens: known targets, glossary terms, and no forward references in either order.
    def scan(text, where, step, ri):
        for m in TOKEN.finditer(text):
            kind, key = m.group(1), m.group(2)
            if is_placeholder(text, m, gloss):
                continue
            if kind == "@":
                if key not in edges or not edges[key].get("card"):
                    err(f"{where}: {{@{key}}} must name an edge that has a card.")
                elif ri is not None and edge_reveal(edges[key], ri) > step:
                    err(f"{where}: names edge {key} before it appears ({order_name}).")
            elif kind == "#":
                if key not in nodes:
                    err(f"{where}: {{#{key}}} names an unknown node.")
                elif ri is not None and ri.get(key, 10 ** 6) > step:
                    err(f"{where}: names node {key} before it appears ({order_name}).")
            elif key not in gloss:
                err(f"{where}: {{{key}}} isn't in the glossary.")

    for order_name in ("run", "build"):
        if order_name not in data.get("steps", {}):
            continue
        ri = reveal(data, order_name)
        for n in nodes.values():
            for t in texts_of({"card": n.get("card"), "why": n.get("why")}):
                scan(t, f"Node {n['id']}", ri.get(n["id"], 0), ri)
        for e in edges.values():
            if e.get("card"):
                for t in texts_of(e["card"]):
                    scan(t, f"Edge {e['id']}", edge_reveal(e, ri), ri)
        for i, st in enumerate(data["steps"][order_name]):
            scan(st["text"], f"steps.{order_name}[{i}]", i, ri)

    used = sorted({str(n["why"]["main"]) for n in nodes.values() if n.get("why", {}).get("type") == "earned"})
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"check: {len(errors)} errors, {len(warnings)} warnings. Main reasons used: {', '.join(used) or 'none'}.")
    return not errors


# ---------- note tables ----------
def md(s, data=None, let=None):
    """Plain markdown text: tokens become words, pipes are escaped for tables."""
    s = str(s)

    def word(m):
        kind, key = m.group(1), m.group(2)
        if is_placeholder(s, m, (data or {}).get("glossary", {})):
            return m.group(0)
        if kind == "@":
            return f"edge {let[key]}" if let and key in let else "an edge"
        if kind == "#" and data:
            return next((n["label"] for n in data["nodes"] if n["id"] == key), key)
        return key
    return TOKEN.sub(word, s).replace("|", "\\|")


def tables(data_path):
    data = json.loads(Path(data_path).read_text())
    nodes = {n["id"]: n for n in data["nodes"]}
    num, let = numbering(data, "run")
    reasons = data["reasons"]
    order = [nid for st in data["steps"]["run"] for nid in st["nodes"]]
    real = [nodes[nid] for nid in order if not nodes[nid].get("ghost")]

    def why(n):
        w = n["why"]
        if w["type"] == "start":
            return "Starting loop"
        if w["type"] == "required":
            return "Required by the job"
        return f"Reason {w['main']}" + (f", also {', '.join(map(str, w['also']))}" if w.get("also") else "")

    out = ["### Nodes", "", "Numbered in the order they run. Reasons are listed under the table.", "",
           "| # | Node | What it is | Job | Why it exists |", "| --- | --- | --- | --- | --- |"]
    for n in real:
        out.append(f"| {num[n['id']]} | {md(n['label'])} | {md(n['sub'])} | {data['roles'][n['role']]['name']} | {why(n)} |")
    out += ["", "Reasons:", ""]
    out += [f"{r}. {v['name']}: {v['desc']}" for r, v in reasons.items()]
    out += ["", "### If a node fails", ""]
    out += [f"{num[n['id']]}. {md(n['label'])}: {md(n['card']['fail'], data, let)}" for n in real]

    kind = {"solid": "Always", "dashed": "Only sometimes", "dotted": "Data"}
    out += ["", "### Edges", "", "In the order they first appear. Lettered edges have an explainer on the page.", "",
            "| Edge | From → To | Type | Rule or data |", "| --- | --- | --- | --- |"]
    ri = reveal(data, "run")
    shown = [e for e in data["edges"] if not e.get("buildOnly") and not e.get("ghost")]
    shown.sort(key=lambda e: (edge_reveal(e, ri), let.get(e["id"], "~")))
    for e in shown:
        t = "Failure path" if e.get("layer") == "fail" else e.get("kind") or kind[e["style"]]
        out.append(f"| {let.get(e['id'], '')} | {md(nodes[e['from']]['label'])} → {md(nodes[e['to']]['label'])} "
                   f"| {t} | {md(e.get('label', ''))} |")

    for n in real:
        if n["card"].get("table"):
            out += ["", f"### Who writes what: {md(n['label'])}", "", "| Data | Written only by | Read by |", "| --- | --- | --- |"]
            out += [f"| {' | '.join(md(c) for c in row)} |" for row in n["card"]["table"]]

    cut = [n for n in data["nodes"] if n.get("ghost")]
    if cut:
        out += ["", "### What we cut", ""]
        out += [f"{i}. {md(n['label'])}: {md(n['card']['cut'], data, let)}" for i, n in enumerate(cut, 1)]

    out += ["", "### Flow diagram", "", "```mermaid", mermaid(data, real, num, let), "```"]
    print("\n".join(out))


def mermaid(data, real, num, let):
    shape = {"model": ('("', '")'), "code": ('["', '"]'), "store": ('[("', '")]'),
             "event": ('(["', '"])'), "person": ('{{"', '"}}')}
    q = lambda s: md(s).replace('"', "#quot;")
    lines = ["flowchart TB"]
    grouped = {}
    for n in real:
        grouped.setdefault(n.get("group"), []).append(n)
    groups = {g["id"]: g["label"] for g in data.get("groups", [])}
    for gid, members in grouped.items():
        pad = "    " if gid else "  "
        if gid:
            lines.append(f'  subgraph {gid}["{q(groups[gid])}"]')
        for n in members:
            a, b = shape[n["build"]]
            lines.append(f"{pad}{n['id']}{a}{num[n['id']]} · {q(n['label'])}<br/><small>{q(n['sub'])}</small>{b}")
        if gid:
            lines.append("  end")
    link_styles, i = [], 0
    ids = {n["id"] for n in real}
    for e in data["edges"]:
        if e.get("buildOnly") or e.get("ghost") or e["from"] not in ids or e["to"] not in ids:
            continue
        label = (f"{let[e['id']]} · " if e["id"] in let else "") + e.get("label", "")
        arrow = "-->" if e["style"] == "solid" else "-.->"
        lines.append(f'  {e["from"]} {arrow}' + (f'|"{q(label)}"|' if label else "") + f' {e["to"]}')
        style = []
        if e["style"] == "dashed":
            style.append("stroke-dasharray:7 5")
        if e["style"] == "dotted":
            style.append("stroke-dasharray:1 5")
        if e.get("layer") == "fail":
            style.append("stroke:#d92d20")
        if style:
            link_styles.append(f"  linkStyle {i} {','.join(style)}")
        i += 1
    lines += link_styles
    for role, fill in ROLE_FILL.items():
        lines.append(f"  classDef {role} fill:{fill},stroke:#333,color:#14141a")
    lines.append("  classDef external stroke-dasharray:6 4,stroke-width:2px")
    for n in real:
        lines.append(f"  class {n['id']} {n['role']}" + (",external" if n.get("external") else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "extract" and len(args) == 2:
        extract(*args)
    elif cmd == "check" and len(args) == 1:
        sys.exit(0 if check(json.loads(Path(args[0]).read_text())) else 1)
    elif cmd == "build" and len(args) == 2:
        build(*args)
    elif cmd == "tables" and len(args) == 1:
        tables(*args)
    else:
        sys.exit(__doc__)
