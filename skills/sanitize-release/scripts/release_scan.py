#!/usr/bin/env python3
"""
Release scanner for Claude Code skills, agents, and plugins.

Reads every file in a folder and reports anything that should not ship:

  - secrets: API keys, tokens, private key blocks, credential assignments
  - private terms: your own names and identifiers, loaded from a local file
  - portability: home paths, model pins, custom agents, MCP tools, sibling
    skills, hooks, author-specific output paths
  - workspace artifacts: __pycache__, .pyc, .DS_Store
  - binaries: images, PDFs, archives a regex cannot read (listed for a human)

Usage:
    python3 release_scan.py <folder> [--json] [--no-private]

The private-terms file is $LEAK_SCAN_PRIVATE if set, else
~/.config/leak-scan/private-terms. One rule per line: `<high|medium|low> <regex>`.
`#` comments and blank lines are ignored. Without that file the scan only knows
generic shapes, so it refuses to run unless --no-private is passed.

Exit codes: 0 no errors, 1 errors found, 2 bad invocation,
3 private-terms file missing or empty.
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------- private layer

def private_terms_path():
    return os.environ.get("LEAK_SCAN_PRIVATE") or os.path.expanduser(
        "~/.config/leak-scan/private-terms"
    )


def load_private_rules(path):
    """Return (rules, problems). Each rule is (severity, compiled_regex, source)."""
    rules, problems = [], []
    if not os.path.isfile(path):
        return rules, problems
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for num, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2 or parts[0] not in ("high", "medium", "low"):
                problems.append(f"line {num}: expected '<high|medium|low> <regex>'")
                continue
            try:
                rules.append((parts[0], re.compile(parts[1]), parts[1]))
            except re.error as exc:
                problems.append(f"line {num}: bad regex ({exc})")
    return rules, problems


def split_identifiers(line):
    """`AcmeNotesVault` -> `Acme Notes Vault`, so private terms inside
    joined-up names are still caught."""
    line = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", line)
    return re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", line)


# ---------------------------------------------------------------- secrets

PLACEHOLDER_VALUE = re.compile(
    r"^(?:[$<{%]|your[-_]|example|changeme|placeholder|xxx|redacted|none|null|"
    r"true|false|env\b|os\.environ|process\.env|getenv|\*{3,}|\.{3})",
    re.IGNORECASE,
)

SECRET_PATTERNS = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    ("age_secret_key", re.compile(r"AGE-SECRET-KEY-1[0-9A-Z]{50,}")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("anthropic_or_openai_key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_calendar_id", re.compile(r"\b[a-z0-9]{20,}@group\.calendar\.google\.com\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9\-._~+/]{20,}=*)")),
]

CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"client[_-]?secret|private[_-]?key)\b[\"']?\s*[:=]\s*[\"']?([^\s\"'#,;)]{6,})"
)


# ---------------------------------------------------------------- portability

OUTPUT_CONTEXT_PATTERN = re.compile(
    r"(?:write|save|output|export|create|store|dump|generate)s?\s+"
    r"(?:to|in|into|under|at|inside)\s*:?\s+",
    re.IGNORECASE,
)
OUTPUT_LABEL_PATTERN = re.compile(
    r"(?:output|destination|target|save|file|health)\s*"
    r"(?:folder|directory|dir|path|location|file)\s*:?\s*",
    re.IGNORECASE,
)
ENSURE_DIR_PATTERN = re.compile(
    r"(?:ensure|create|mkdir|make)\s+.*(?:directory|folder|dir)\s+(?:exists)?\s*:?\s*",
    re.IGNORECASE,
)
DEFAULT_CONTEXT_PATTERN = re.compile(
    r"(?:default|defaults?\s+to|falls?\s+back\s+to|by\s+default)\s*:?\s*",
    re.IGNORECASE,
)
RELATIVE_PATH_PATTERN = re.compile(
    r"(?:`|\"|')?([a-zA-Z][\w-]*/(?:[\w./-]*[/]|[\w-]+\.[\w]+))(?:`|\"|')?"
)
SKILL_INTERNAL_DIRS = {"references", "scripts", "assets", "evals", "agents"}
BUILTIN_AGENT_TYPES = {"fork", "general-purpose", "Explore", "Plan", "claude"}

PORTABILITY_CHECKS = [
    {
        "id": "hardcoded_path",
        "description": "Absolute path under a real user's home directory",
        "severity": "error",
        "patterns": [
            re.compile(r"/(?:Users|home)/([^/\s`\"']+)/[^\s`\"']*", re.IGNORECASE),
        ],
    },
    {
        "id": "home_relative_path",
        "description": "Path under ~/ (fine for standard locations; not for the author's own folders)",
        "severity": "warning",
        "patterns": [re.compile(r"~/[^\s`\"')]+")],
    },
    {
        "id": "model_pin",
        "description": "Pinned model ID (document why, or generalize)",
        "severity": "warning",
        "patterns": [re.compile(r"claude-(?:opus|sonnet|haiku|fable)-\d[\w\-\[\]]*")],
    },
    {
        "id": "named_agent_ref",
        "description": "Custom agent that won't exist on another machine unless bundled",
        "severity": "error",
        "patterns": [
            re.compile(r'subagent_type:\s*["\'`]?([a-zA-Z][\w-]+)["\'`]?'),
            re.compile(r'[Ss]pawn\s+(?:a\s+)?(?:an\s+)?agent\s+(?:type\s+)?["\'`]([a-zA-Z][\w-]+)["\'`]'),
        ],
    },
    {
        "id": "mcp_tool_ref",
        "description": "MCP tool that needs a specific server installed",
        "severity": "warning",
        "patterns": [re.compile(r"mcp__[a-zA-Z][\w-]*__[a-zA-Z][\w-]*")],
    },
    {
        "id": "skill_cross_ref",
        "description": "Another skill this one depends on, which may not be installed",
        "severity": "warning",
        "patterns": [
            re.compile(r"invoke\s+/[\w-]+"),
            re.compile(r'\bskill:\s*["\'][\w:-]+["\']'),
            re.compile(r'^\s*-?\s*skill:\s*[\w:-]+\s*$'),
            re.compile(r"/[\w-]+(?:\s+|$)(?:skill|command)", re.IGNORECASE),
        ],
    },
    {
        "id": "hook_ref",
        "description": "Reference to a hook configuration the user won't have",
        "severity": "warning",
        "patterns": [
            re.compile(
                r"(?:PreToolUse|PostToolUse|Notification|Stop|SessionStart|SessionEnd)\s*(?:hook|event)",
                re.IGNORECASE,
            ),
            re.compile(r"hooks?\.json", re.IGNORECASE),
        ],
    },
]

PLACEHOLDER_USERS = {
    "jdoe", "johndoe", "janedoe", "user", "username", "you", "yourname",
    "your-username", "me", "example", "name", "someone", "alice", "bob", "...",
}
# ~/ locations that exist on every machine, so naming them is not a leak.
STANDARD_HOME_PREFIXES = ("~/.claude", "~/.config", "~/Library", "~/.local", "~/...", "~/tmp")


def is_placeholder_user(name):
    """`jdoe`, `<user>`, `$USER`, or a regex fragment like `[\\w.` is not a real user."""
    return name.lower() in PLACEHOLDER_USERS or bool(re.search(r"[<>\[\]\\(){}$*?|]", name))


def is_standard_home_path(text):
    return text.startswith(STANDARD_HOME_PREFIXES)


ARTIFACT_DIRS = {"__pycache__"}
ARTIFACT_FILES = {".DS_Store"}
ARTIFACT_SUFFIXES = (".pyc", ".pyo")
SKIP_DIRS = {".git"}


# ---------------------------------------------------------------- scanning

def is_binary(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return False
    return b"\x00" in chunk


def finding(kind, check, severity, description, rel, num, match, line):
    return {
        "category": kind,
        "check": check,
        "severity": severity,
        "description": description,
        "file": rel,
        "line": num,
        "match": match,
        "context": line.rstrip()[:300],
    }


def mask(secret):
    """Keep the first 4 characters so the user can recognize the value, hide the rest."""
    return secret[:4] + "****"


def scan_line(line, num, rel, private_rules):
    found = []
    secrets = []

    # Secrets
    for check_id, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(line):
            # A pattern with a group marks just the secret part (the token after "Bearer").
            secrets.append(m.group(1) if m.lastindex else m.group(0))
            found.append(finding("secret", check_id, "error",
                                 "Secret-shaped value", rel, num, m.group(0), line))
    for m in CREDENTIAL_ASSIGNMENT.finditer(line):
        value = m.group(2)
        if PLACEHOLDER_VALUE.match(value):
            continue
        secrets.append(value)
        found.append(finding("secret", "credential_assignment", "error",
                             f"'{m.group(1)}' assigned a concrete value", rel, num,
                             m.group(0), line))

    # Private terms (checked against the line and its split-identifier form)
    if private_rules:
        variants = {line, split_identifiers(line)}
        seen = set()
        for severity, pattern, source in private_rules:
            for text in variants:
                m = pattern.search(text)
                if m and source not in seen:
                    seen.add(source)
                    found.append(finding(
                        "private_term", "private_term",
                        "warning" if severity == "low" else "error",
                        f"Matches private-terms rule: {source}", rel, num,
                        m.group(0), line))

    # Portability
    for check in PORTABILITY_CHECKS:
        for pattern in check["patterns"]:
            for m in pattern.finditer(line):
                text = m.group(0)
                if check["id"] == "named_agent_ref":
                    name = m.group(1) if m.lastindex else text
                    if name in BUILTIN_AGENT_TYPES:
                        continue
                if check["id"] == "hardcoded_path" and is_placeholder_user(m.group(1)):
                    continue
                if check["id"] == "home_relative_path" and is_standard_home_path(text):
                    continue
                found.append(finding("portability", check["id"], check["severity"],
                                     check["description"], rel, num, text, line))

    for m in RELATIVE_PATH_PATTERN.finditer(line):
        rel_dir = m.group(1)
        if rel_dir.split("/")[0] in SKILL_INTERNAL_DIRS:
            continue
        if (OUTPUT_CONTEXT_PATTERN.search(line) or OUTPUT_LABEL_PATTERN.search(line)
                or ENSURE_DIR_PATTERN.search(line) or DEFAULT_CONTEXT_PATTERN.search(line)):
            found.append(finding(
                "portability", "relative_output_path", "warning",
                "Relative output/default path that may encode the author's folder layout",
                rel, num, rel_dir, line))

    # Never print a secret in full: mask it in every finding from this line,
    # including private-term and portability findings that show the same line.
    for secret in sorted(set(secrets), key=len, reverse=True):
        for f in found:
            f["match"] = f["match"].replace(secret, mask(secret))
            f["context"] = f["context"].replace(secret, mask(secret))
    return found


def scan(root, private_rules):
    root = os.path.abspath(root)
    findings, binaries, artifacts = [], [], []
    files_read = 0

    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            if d in SKIP_DIRS:
                dirnames.remove(d)
            elif d in ARTIFACT_DIRS:
                artifacts.append(os.path.relpath(os.path.join(dirpath, d), root) + "/")
                dirnames.remove(d)
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if name in ARTIFACT_FILES or name.endswith(ARTIFACT_SUFFIXES):
                artifacts.append(rel)
                continue
            # The file name itself can leak (a private term in a filename).
            if private_rules:
                findings.extend(
                    f for f in scan_line(rel, 0, rel, private_rules)
                    if f["category"] == "private_term")
            if is_binary(path):
                binaries.append(rel)
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            files_read += 1
            for num, line in enumerate(lines, start=1):
                findings.extend(scan_line(line, num, rel, private_rules))

    for a in artifacts:
        findings.append(finding("artifact", "workspace_artifact", "error",
                                "Generated or OS file that should not ship",
                                a, 0, a, a))

    order = {"secret": 0, "private_term": 1, "portability": 2, "artifact": 3}
    findings.sort(key=lambda f: (order[f["category"]], f["severity"] != "error",
                                 f["file"], f["line"]))
    return findings, binaries, files_read


def print_text(result):
    print(f"Scanned: {result['path']}")
    print(f"Files read: {result['files_read']}")
    if result["private_layer"]["rules"]:
        print(f"Private terms: {result['private_layer']['rules']} rule(s) from "
              f"{result['private_layer']['path']}")
    else:
        print("Private terms: NONE LOADED. Only generic patterns were checked; "
              "a clean result here is not trustworthy.")
    for p in result["private_layer"]["problems"]:
        print(f"  private-terms {p}")
    print(f"Errors: {result['errors']}   Warnings: {result['warnings']}")

    current = None
    for f in result["findings"]:
        if f["category"] != current:
            current = f["category"]
            print(f"\n== {current}")
        where = f["file"] if not f["line"] else f"{f['file']}:{f['line']}"
        print(f"[{f['severity']}] {where}  {f['check']}: {f['match']}")
        if f["line"]:
            print(f"    {f['context'].strip()}")

    if result["binaries"]:
        print("\n== binaries (a scan cannot read these; open each one)")
        for b in result["binaries"]:
            print(f"  {b}")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    unknown = flags - {"--json", "--no-private"}
    if len(args) != 1 or unknown:
        print("usage: release_scan.py <folder> [--json] [--no-private]", file=sys.stderr)
        return 2
    root = args[0]
    if not os.path.isdir(root):
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    path = private_terms_path()
    rules, problems = load_private_rules(path)
    if not rules and "--no-private" not in flags:
        print(f"No private-terms rules found at {path}.\n"
              "Without them the scan cannot catch your own names and identifiers. "
              "Create the file (one '<high|medium|low> <regex>' per line), "
              "or pass --no-private to run with generic patterns only.",
              file=sys.stderr)
        return 3

    findings, binaries, files_read = scan(root, rules)
    result = {
        "path": os.path.abspath(root),
        "files_read": files_read,
        "private_layer": {"path": path, "rules": len(rules), "problems": problems},
        "trustworthy": bool(rules),
        "errors": sum(f["severity"] == "error" for f in findings),
        "warnings": sum(f["severity"] == "warning" for f in findings),
        "findings": findings,
        "binaries": binaries,
    }
    if "--json" in flags:
        print(json.dumps(result, indent=2))
    else:
        print_text(result)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
