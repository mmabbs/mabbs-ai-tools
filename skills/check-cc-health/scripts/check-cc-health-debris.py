#!/usr/bin/env python3
"""
check-cc-health debris domain — finds loose ends and broken references.

Checks:
1. Orphaned agent directories — never referenced by any active file
2. Leftover TODO/FIXME/HACK/XXX markers in config files

Usage:
    python3 check-cc-health-debris.py [--base-dir PATH]

Outputs AuditReport JSON to stdout.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.schema import AuditReport, Finding, progress

# Marker patterns
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

# Files to scan for markers (relative to .claude/)
MARKER_SCAN_DIRS = ["rules", "skills", "agents"]
MARKER_SCAN_FILES = ["CLAUDE.md", "AGENTS.md"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default=str(Path.home()),
                        help="Base directory (defaults to $HOME, override for testing)")
    return parser.parse_args()


def _agent_has_description(agent_file: Path) -> bool:
    """True if the agent's frontmatter has a description, so Claude can pick it without being told its name."""
    try:
        content = agent_file.read_text()
    except (OSError, UnicodeDecodeError):
        return False
    if not content.startswith("---"):
        return False
    try:
        end = content.index("---", 3)
    except ValueError:
        return False
    return any(line.strip().startswith("description:") for line in content[3:end].split("\n"))


def check_orphaned_directories(claude_dir: Path, findings: list[Finding]):
    """Find agents (name.md or name/AGENT.md) that no other file refers to by name."""

    for subdir_name in ("agents",):  # skills are user/description-triggered;
                                      # unreferenced is their normal state
        target_dir = claude_dir / subdir_name
        if not target_dir.exists():
            continue

        for item_dir in target_dir.iterdir():
            # Agents are either a folder (name/AGENT.md) or a flat file (name.md)
            if item_dir.is_dir():
                dir_name = item_dir.name
                agent_file = item_dir / "AGENT.md"
            elif item_dir.is_file() and item_dir.suffix == ".md":
                dir_name = item_dir.stem
                agent_file = item_dir
            else:
                continue

            # Check if this name appears in any file outside its own directory
            referenced_externally = False
            for md_file in claude_dir.rglob("*.md"):
                if "archive" in md_file.parts:
                    continue
                # Skip files inside this directory itself
                try:
                    md_file.relative_to(item_dir)
                    continue  # File is inside the directory — skip
                except ValueError:
                    pass  # File is outside — check it

                try:
                    content = md_file.read_text()
                except (OSError, UnicodeDecodeError):
                    continue

                if dir_name in content:
                    referenced_externally = True
                    break

            if not referenced_externally:
                # An agent with a description can still be picked by Claude on its own,
                # so being unnamed elsewhere is normal for it. Without one, nothing can reach it.
                if _agent_has_description(agent_file):
                    findings.append(Finding(
                        severity="info",
                        check="orphaned-directory",
                        message=f"{subdir_name.rstrip('s').title()} '{dir_name}' is never referenced by name; Claude can still pick it by its description",
                        path=str(item_dir),
                        action=None
                    ))
                else:
                    findings.append(Finding(
                        severity="warning",
                        check="orphaned-directory",
                        message=f"{subdir_name.rstrip('s').title()} '{dir_name}' is never referenced by any file outside itself",
                        path=str(item_dir),
                        action="Move it out of agents/ if you no longer use it"
                    ))


def check_leftover_markers(claude_dir: Path, findings: list[Finding]):
    """Find TODO/FIXME/HACK/XXX markers in config files."""
    scan_paths = []

    for dirname in MARKER_SCAN_DIRS:
        dirpath = claude_dir / dirname
        if dirpath.exists():
            scan_paths.extend(dirpath.rglob("*.md"))

    for filename in MARKER_SCAN_FILES:
        filepath = claude_dir / filename
        if filepath.exists():
            scan_paths.append(filepath)

    for filepath in scan_paths:
        # Skip archive and the check-cc-health plugin's own files (avoids self-flagging)
        if "archive" in filepath.parts:
            continue
        if "check-cc-health" in filepath.parts and "plugins" in filepath.parts:
            continue
        try:
            content = filepath.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        for i, line in enumerate(content.split("\n"), 1):
            match = MARKER_RE.search(line)
            if match:
                marker = match.group(1).upper()
                context = line.strip()[:100]
                findings.append(Finding(
                    severity="info",
                    check="leftover-marker",
                    message=f"{marker} marker at line {i}: {context}",
                    path=str(filepath),
                    action=f"Resolve or remove the {marker} marker"
                ))


def main():
    args = parse_args()
    base_dir = Path(args.base_dir)
    claude_dir = base_dir / ".claude"
    findings: list[Finding] = []
    checks_run = 0

    if not claude_dir.exists():
        report = AuditReport(domain="debris", findings=[], meta={"checks_run": 0})
        report.emit()
        return

    progress("Checking for orphaned directories...")
    check_orphaned_directories(claude_dir, findings)
    checks_run += 1

    progress("Checking for leftover markers...")
    check_leftover_markers(claude_dir, findings)
    checks_run += 1

    report = AuditReport(
        domain="debris",
        findings=findings,
        meta={"checks_run": checks_run}
    )
    report.emit()


if __name__ == "__main__":
    main()
