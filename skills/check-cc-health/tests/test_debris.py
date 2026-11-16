"""Tests for check-cc-health-debris scanner."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "check-cc-health-debris.py"


def run_scanner(base_dir: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-dir", base_dir],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Scanner failed: {result.stderr}"
    return json.loads(result.stdout)


def test_orphaned_agent_directory(tmp_path):
    """Agent directories never referenced by any file are flagged."""
    claude_dir = tmp_path / ".claude"
    agents_dir = claude_dir / "agents"

    # Create an agent that IS referenced
    used_agent = agents_dir / "used-agent"
    used_agent.mkdir(parents=True)
    (used_agent / "AGENT.md").write_text("---\nmodel: opus\n---\nYou are helpful.")

    # Create an agent that is NOT referenced anywhere
    orphan_agent = agents_dir / "orphan-agent"
    orphan_agent.mkdir(parents=True)
    (orphan_agent / "AGENT.md").write_text("---\nmodel: opus\n---\nYou are forgotten.")

    # Create a CLAUDE.md that only references used-agent
    (claude_dir / "CLAUDE.md").write_text('Spawn Agent({subagent_type: "used-agent", prompt: "hi"})')

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "orphaned-directory" in checks
    orphan_findings = [f for f in report["findings"] if f["check"] == "orphaned-directory"]
    assert any("orphan-agent" in f["message"] for f in orphan_findings)


def test_orphaned_flat_agent_file(tmp_path):
    """A flat agent file (name.md) that nothing references is flagged like a folder agent."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "orphan-agent.md").write_text("---\nmodel: opus\n---\nYou are forgotten.")

    report = run_scanner(str(tmp_path))
    orphans = [f for f in report["findings"] if f["check"] == "orphaned-directory"]
    assert len(orphans) == 1
    assert "orphan-agent" in orphans[0]["message"]
    assert orphans[0]["severity"] == "warning"


def test_unreferenced_agent_with_description_is_info(tmp_path):
    """An unreferenced agent that has a description is reported as info, not a warning."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "reviewer.md").write_text("---\nname: reviewer\ndescription: Reviews things\n---\nYou review.")

    report = run_scanner(str(tmp_path))
    orphans = [f for f in report["findings"] if f["check"] == "orphaned-directory"]
    assert len(orphans) == 1
    assert orphans[0]["severity"] == "info"


def test_leftover_todo_markers(tmp_path):
    """TODO/FIXME markers in config files are flagged."""
    claude_dir = tmp_path / ".claude"
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir(parents=True)

    (rules_dir / "my-rule.md").write_text("# Rule\n\n- Do the thing\n- TODO: finish this section\n")

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "leftover-marker" in checks


def test_clean_setup_no_findings(tmp_path):
    """A clean setup with no orphans or markers produces no findings."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "only-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("---\nname: only-skill\n---\nDo the thing.")

    # Reference the skill
    (claude_dir / "CLAUDE.md").write_text('Invoke `Skill(skill: "only-skill")` when needed.')

    report = run_scanner(str(tmp_path))
    assert report["findings"] == []
