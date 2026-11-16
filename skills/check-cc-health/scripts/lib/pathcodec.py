"""
Shared decoder for Claude Code's lossy project-path encoding.

Claude Code names each ~/.claude/projects/ folder after the project path with
every character that isn't a letter or digit replaced by "-". Both the config
and chats scanners resolve those names back to real paths with this module,
so they agree on which projects still exist.
"""

import re
from pathlib import Path

_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]")


def encode_name(name: str) -> str:
    """Encode a path or path segment the way Claude Code does."""
    return _NON_ALNUM.sub("-", name)


def _children(directory: Path) -> list[Path]:
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def _resolve_dfs(tokens: list[str], idx: int, current: Path) -> "Path | None":
    """DFS: find a real path under `current` whose encoding consumes tokens[idx:].

    At each level, tries consuming tokens[idx..j] as one entry name by encoding
    each real child of `current` and comparing. Matching against what exists
    covers every collapsed character, and directory listings bound the search.
    """
    if idx == len(tokens):
        return current

    children = _children(current)
    for j in range(idx, len(tokens)):
        target = "-".join(tokens[idx : j + 1])
        if not target:
            continue
        for child in children:
            if encode_name(child.name) == target:
                result = _resolve_dfs(tokens, j + 1, child)
                if result is not None:
                    return result

    return None


def resolve_encoded_path(encoded: str, root: Path = Path("/")) -> "Path | None":
    """Resolve a lossy hyphen-encoded project path against the real filesystem.

    Returns an existing Path that encodes to `encoded`, or None if no such
    path exists (the genuine orphan case). Handles names with any punctuation,
    e.g. `my_app`, `site.v2`, `pytest-of-jdoe`, `{Project}`, `.claude`.

    Not handled: Claude Code shortens encoded names longer than 200 characters
    and appends a hash, so very deep paths never resolve and read as orphans.
    """
    if not encoded.startswith("-"):
        return None
    tokens = encoded[1:].split("-")
    return _resolve_dfs(tokens, 0, root)
