"""Tests for check-cc-health-chats project-directory handling.

Covers the guard for custom-named project directories: as of Claude Code
2.1.234, CLAUDE_CODE_PROJECT_DIR_NAME can give a directory under
~/.claude/projects/ a short name instead of the hyphen-encoded working
directory path. Encoded names always start with '-'; custom names don't,
and must never be decoded or reported as orphans.

check-cc-health-chats.py takes no --base-dir flag, so these tests import the
module and point its PROJECTS_DIR at a temp directory.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "check-cc-health-chats.py"

MISSING_ENCODED = "-Users-jdoe-Documents-deleted-project"
CUSTOM_NAMED = "my_nickname"


def load_chats_module():
    """Import check-cc-health-chats.py by path (its name isn't a valid module name)."""
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("check_cc_health_chats", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def chats(tmp_path, monkeypatch):
    """Module with PROJECTS_DIR pointed at a temp projects tree.

    Contains three project dirs: an encoded path that no longer exists,
    an encoded path that does exist, and a custom-named dir.
    """
    module = load_chats_module()

    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # (a) encoded dir whose decoded path no longer exists
    (projects_dir / MISSING_ENCODED).mkdir()
    (projects_dir / MISSING_ENCODED / "a.jsonl").write_text("")

    # (b) encoded dir whose decoded path exists
    real_project = tmp_path / "real-project"
    real_project.mkdir()
    existing_encoded = str(real_project).replace("/", "-")
    (projects_dir / existing_encoded).mkdir()
    (projects_dir / existing_encoded / "b.jsonl").write_text("")

    # (c) custom-named dir (CLAUDE_CODE_PROJECT_DIR_NAME)
    (projects_dir / CUSTOM_NAMED).mkdir()
    (projects_dir / CUSTOM_NAMED / "c.jsonl").write_text("")

    monkeypatch.setattr(module, "PROJECTS_DIR", projects_dir)
    module.existing_encoded = existing_encoded
    return module


def test_missing_encoded_dir_is_orphaned(chats):
    """An encoded dir whose decoded path is gone is still flagged as an orphan."""
    result = chats.audit_orphans()
    orphaned = [o["encoded_path"] for o in result["orphans"]]
    assert MISSING_ENCODED in orphaned
    assert result["summary"]["total_orphaned_projects"] == 1


def test_existing_encoded_dir_not_orphaned(chats):
    """An encoded dir whose decoded path exists is not flagged."""
    result = chats.audit_orphans()
    orphaned = [o["encoded_path"] for o in result["orphans"]]
    assert chats.existing_encoded not in orphaned


def test_custom_named_dir_not_orphaned(chats):
    """A custom-named dir is reported as informational, never as an orphan."""
    result = chats.audit_orphans()
    orphaned = [o["encoded_path"] for o in result["orphans"]]
    assert CUSTOM_NAMED not in orphaned
    assert result["custom_named_dirs"] == [CUSTOM_NAMED]
    assert result["summary"]["custom_named_dir_count"] == 1


def test_usage_marks_custom_named_dir(chats):
    """Usage reports custom-named dirs as existing, without decoding them."""
    result = chats.audit_projects()
    by_name = {p["encoded_path"]: p for p in result["projects"]}

    custom = by_name[CUSTOM_NAMED]
    assert custom["custom_named"] is True
    assert custom["path_exists"] is True
    assert custom["decoded_path"] == CUSTOM_NAMED


def test_usage_marks_missing_encoded_dir(chats):
    """Usage still reports a missing encoded path as non-existent."""
    result = chats.audit_projects()
    by_name = {p["encoded_path"]: p for p in result["projects"]}

    missing = by_name[MISSING_ENCODED]
    assert missing["path_exists"] is False
    assert missing["custom_named"] is False
