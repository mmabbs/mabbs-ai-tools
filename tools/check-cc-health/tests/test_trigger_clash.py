"""Tests for skill trigger clash detection."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "check-cc-health-assets.py"


@pytest.fixture(autouse=True)
def clean_trigger_clash_state(tmp_path_factory, monkeypatch):
    """Point state at a fresh temp file per test to keep them hermetic.

    The scanner subprocess inherits CHECK_CC_HEALTH_STATE_FILE, so it never
    touches the real ~/.claude/check-cc-health-state.json.
    """
    state_file = tmp_path_factory.mktemp("check-cc-health-state") / "state.json"
    monkeypatch.setenv("CHECK_CC_HEALTH_STATE_FILE", str(state_file))


def run_scanner(base_dir: str, threshold: float | None = None, all_clashes: bool = False) -> dict:
    cmd = [sys.executable, str(SCRIPT), "--base-dir", base_dir]
    if threshold is not None:
        cmd.extend(["--clash-threshold", str(threshold)])
    if all_clashes:
        cmd.append("--all-clashes")
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Scanner failed: {result.stderr}"
    return json.loads(result.stdout)


def _make_skill(tmp_path: Path, name: str, description: str) -> Path:
    """Create a minimal skill directory with SKILL.md."""
    skill_dir = tmp_path / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(textwrap.dedent(f"""\
        ---
        name: {name}
        description: {description}
        ---
        Body content.
    """))
    return skill_dir


def test_identical_descriptions_flagged(tmp_path):
    """Two skills with identical descriptions are flagged as clashing."""
    desc = "Audit and review code for quality issues and patterns"
    _make_skill(tmp_path, "skill-a", desc)
    _make_skill(tmp_path, "skill-b", desc)

    report = run_scanner(str(tmp_path))
    clashes = [f for f in report["findings"] if f["check"] == "trigger-clash"]
    assert len(clashes) == 1
    assert "skill-a" in clashes[0]["message"]
    assert "skill-b" in clashes[0]["message"]


def test_different_descriptions_not_flagged(tmp_path):
    """Two skills with completely different descriptions are not flagged."""
    _make_skill(tmp_path, "skill-a", "Audit infrastructure health and configuration files")
    _make_skill(tmp_path, "skill-b", "Create beautiful watercolor paintings from photographs")

    report = run_scanner(str(tmp_path))
    clashes = [f for f in report["findings"]
               if f["check"] == "trigger-clash"]
    assert len(clashes) == 0


def test_threshold_tuning(tmp_path):
    """A pair just below default threshold is caught with a lower threshold."""
    _make_skill(tmp_path, "skill-a",
                "Audit configuration files for missing settings and invalid values")
    _make_skill(tmp_path, "skill-b",
                "Audit memory entries for stale paths and dead references")

    # At default threshold — may or may not flag (depends on similarity)
    report_default = run_scanner(str(tmp_path))
    clashes_default = [f for f in report_default["findings"]
                       if f["check"] == "trigger-clash"]
    assert len(clashes_default) == 0

    # At very low threshold — should flag anything with any overlap
    report_low = run_scanner(str(tmp_path), threshold=0.05)
    clashes_low = [f for f in report_low["findings"]
                   if f["check"] == "trigger-clash"]
    assert len(clashes_low) >= 1


def test_multiline_description_parsed(tmp_path):
    """Skills with multiline (folded scalar) descriptions are compared correctly."""
    skill_dir = tmp_path / ".claude" / "skills" / "skill-a"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: skill-a
        description: >
          Audit and review code for quality issues
          and patterns in the codebase.
        ---
        Body.
    """))
    _make_skill(tmp_path, "skill-b",
                "Audit and review code for quality issues and patterns in the codebase.")

    report = run_scanner(str(tmp_path))
    clashes = [f for f in report["findings"]
               if f["check"] == "trigger-clash"]
    assert len(clashes) == 1


def test_meta_includes_pairs_checked(tmp_path):
    """Report meta includes the number of trigger pairs checked."""
    _make_skill(tmp_path, "skill-a", "Do thing A")
    _make_skill(tmp_path, "skill-b", "Do thing B")
    _make_skill(tmp_path, "skill-c", "Do thing C")

    report = run_scanner(str(tmp_path))
    # 3 skills → 3 pairs
    assert report["meta"]["trigger_clashes_checked"] == 3


def test_shared_terms_in_message(tmp_path):
    """Clash findings include the top shared terms."""
    desc = "Audit and review code for quality issues and patterns"
    _make_skill(tmp_path, "skill-a", desc)
    _make_skill(tmp_path, "skill-b", desc)

    report = run_scanner(str(tmp_path))
    clashes = [f for f in report["findings"] if "trigger-clash" in f["check"]]
    assert len(clashes) == 1
    assert "shared terms:" in clashes[0]["message"]


def test_delta_suppresses_known_clashes(tmp_path):
    """Second run suppresses previously-seen clashes."""
    desc = "Audit and review code for quality issues and patterns"
    _make_skill(tmp_path, "skill-a", desc)
    _make_skill(tmp_path, "skill-b", desc)

    # First run — clash is new, should be reported
    report1 = run_scanner(str(tmp_path))
    clashes1 = [f for f in report1["findings"] if "trigger-clash" in f["check"]]
    assert len(clashes1) == 1
    assert clashes1[0]["check"] == "trigger-clash"

    # Second run — same skills, clash is now known, should be suppressed
    report2 = run_scanner(str(tmp_path))
    clashes2 = [f for f in report2["findings"] if f["check"] == "trigger-clash"]
    assert len(clashes2) == 0
    suppressed = [f for f in report2["findings"] if f["check"] == "suppressed-trigger-clashes"]
    assert len(suppressed) == 1
    assert "1 previously-seen" in suppressed[0]["message"]


def test_all_clashes_bypasses_delta(tmp_path):
    """--all-clashes shows everything including known clashes."""
    desc = "Audit and review code for quality issues and patterns"
    _make_skill(tmp_path, "skill-a", desc)
    _make_skill(tmp_path, "skill-b", desc)

    # First run to populate state
    run_scanner(str(tmp_path))

    # Second run with --all-clashes — should show the clash again
    report = run_scanner(str(tmp_path), all_clashes=True)
    clashes = [f for f in report["findings"] if "trigger-clash" in f["check"]]
    assert len(clashes) == 1


def test_new_clash_after_known(tmp_path):
    """A new clashing pair is reported even when other clashes are suppressed."""
    desc = "Audit and review code for quality issues and patterns"
    _make_skill(tmp_path, "skill-a", desc)
    _make_skill(tmp_path, "skill-b", desc)

    # First run — establishes skill-a/skill-b as known
    run_scanner(str(tmp_path))

    # Add a third skill that clashes with both
    _make_skill(tmp_path, "skill-c", desc)

    # Second run — skill-a/skill-b suppressed, but skill-a/skill-c and skill-b/skill-c are new
    report = run_scanner(str(tmp_path))
    new_clashes = [f for f in report["findings"] if f["check"] == "trigger-clash"]
    suppressed = [f for f in report["findings"] if f["check"] == "suppressed-trigger-clashes"]
    assert len(new_clashes) == 2  # skill-a/skill-c and skill-b/skill-c
    assert len(suppressed) == 1   # skill-a/skill-b
