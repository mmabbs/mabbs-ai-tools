"""Tests for check-cc-health-assets scanner."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "check-cc-health-assets.py"


def run_scanner(base_dir: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-dir", base_dir],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Scanner failed: {result.stderr}"
    return json.loads(result.stdout)


def test_broken_skill_reference(tmp_path):
    """Skill() calls referencing non-existent skills are flagged."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "my-skill"
    skills_dir.mkdir(parents=True)

    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text(textwrap.dedent("""\
        ---
        name: my-skill
        description: Test skill
        ---
        Use `Skill(skill: "nonexistent-skill")` to do the thing.
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "broken-skill-reference" in checks


def test_broken_agent_reference(tmp_path):
    """Agent calls referencing non-existent agents are flagged."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "orchestrator"
    skills_dir.mkdir(parents=True)

    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text(textwrap.dedent("""\
        ---
        name: orchestrator
        description: Orchestrates things
        ---
        Spawn Agent({subagent_type: "ghost-agent", prompt: "do stuff"})
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "broken-agent-reference" in checks


def test_plugin_agent_reference_resolves(tmp_path):
    """A flat plugin agent is found under both its bare and <plugin>:<name> forms."""
    plugin_root = tmp_path / ".claude" / "plugins" / "local" / "my-plugin"
    (plugin_root / ".claude-plugin").mkdir(parents=True)
    (plugin_root / ".claude-plugin" / "plugin.json").write_text('{"name": "my-plugin"}')
    (plugin_root / "agents").mkdir()
    (plugin_root / "agents" / "helper.md").write_text(textwrap.dedent("""\
        ---
        name: helper
        description: A helper agent
        ---
        You help.
    """))
    skill_dir = plugin_root / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: my-skill
        description: Uses the helper
        ---
        Agent({ subagent_type: "my-plugin:helper" })
        Agent({ subagent_type: "helper" })
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "broken-agent-reference" not in checks


def test_dead_at_import(tmp_path):
    """@-imports pointing at non-existent files are flagged."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("@AGENTS.md\n@NONEXISTENT.md\n\n# Project\nSome content.")

    # AGENTS.md exists
    (claude_dir / "AGENTS.md").write_text("# Agents")
    # NONEXISTENT.md does not exist

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "dead-at-import" in checks


def test_plugin_scoped_agent_reference_resolves(tmp_path):
    """A plugin-scoped subagent_type resolves to a flat agent file in that plugin."""
    claude_dir = tmp_path / ".claude"
    plugin_dir = claude_dir / "plugins" / "local" / "my-plugin"
    (plugin_dir / "agents").mkdir(parents=True)
    (plugin_dir / "agents" / "reviewer.md").write_text(textwrap.dedent("""\
        ---
        name: reviewer
        description: Reviews things
        ---
        You review things.
    """))
    skill_dir = plugin_dir / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: my-skill
        description: Uses the plugin's own agent
        ---
        Spawn Agent({subagent_type: "my-plugin:reviewer", prompt: "review"})
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "broken-agent-reference" not in checks


def test_invalid_effort_in_flat_agent_file(tmp_path):
    """Effort values are checked in flat agent files (name.md), not only name/AGENT.md."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "my-agent.md").write_text(textwrap.dedent("""\
        ---
        name: my-agent
        description: Does things
        effort: turbo
        ---
        You are a helpful agent.
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "invalid-effort" in checks


def test_bare_model_alias_not_flagged(tmp_path):
    """Agent definitions using bare model aliases are valid and not flagged."""
    claude_dir = tmp_path / ".claude"
    agents_dir = claude_dir / "agents" / "my-agent"
    agents_dir.mkdir(parents=True)

    agent_md = agents_dir / "AGENT.md"
    agent_md.write_text(textwrap.dedent("""\
        ---
        model: opus
        effort: high
        ---
        You are a helpful agent.
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "invalid-model-id" not in checks
    assert "pinned-model-id" not in checks


def test_pinned_model_id(tmp_path):
    """Flat-file agent definitions pinning a full model ID get an info finding."""
    claude_dir = tmp_path / ".claude"
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)

    (agents_dir / "my-agent.md").write_text(textwrap.dedent("""\
        ---
        name: my-agent
        model: claude-example-1-0
        effort: high
        ---
        You are a helpful agent.
    """))

    report = run_scanner(str(tmp_path))
    pinned = [f for f in report["findings"] if f["check"] == "pinned-model-id"]
    assert len(pinned) == 1
    assert pinned[0]["severity"] == "info"


def test_pinned_model_id_subdirectory_layout(tmp_path):
    """The name/AGENT.md layout is checked too."""
    claude_dir = tmp_path / ".claude"
    agents_dir = claude_dir / "agents" / "my-agent"
    agents_dir.mkdir(parents=True)

    (agents_dir / "AGENT.md").write_text(textwrap.dedent("""\
        ---
        model: claude-sample-2-0
        ---
        You are a helpful agent.
    """))

    report = run_scanner(str(tmp_path))
    checks = [f["check"] for f in report["findings"]]
    assert "pinned-model-id" in checks


def test_clean_assets_no_findings(tmp_path):
    """Well-formed assets produce no findings."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "good-skill"
    skills_dir.mkdir(parents=True)
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)

    (skills_dir / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: good-skill
        description: A well-formed skill
        ---
        Do the thing directly.
    """))

    (agents_dir / "good-agent.md").write_text(textwrap.dedent("""\
        ---
        name: good-agent
        model: opus
        effort: high
        ---
        You are a good agent.
    """))

    report = run_scanner(str(tmp_path))
    assert report["findings"] == []
