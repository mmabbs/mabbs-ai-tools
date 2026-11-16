"""Tests for the shared project-path decoder (scripts/lib/pathcodec.py)."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from lib.pathcodec import encode_name, resolve_encoded_path  # noqa: E402


def _load_chats():
    spec = importlib.util.spec_from_file_location("check_cc_health_chats", SCRIPTS / "check-cc-health-chats.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolves_every_collapsed_character(tmp_path):
    """Underscore, dot, hyphen, space, and dotfile names all resolve."""
    names = ["my_app", "site.v2", "pytest-of-jdoe", "foo bar", ".claude", "{Project}", "Notes (2024)"]
    for name in names:
        (tmp_path / "projects" / name).mkdir(parents=True)

    for name in names:
        encoded = "-projects-" + encode_name(name)
        assert resolve_encoded_path(encoded, tmp_path) == tmp_path / "projects" / name, name


def test_resolves_nested_punctuated_path(tmp_path):
    """A braced folder mid-path resolves (the "--Project--" case)."""
    target = tmp_path / "Script Asst" / "{Project}" / "Research"
    target.mkdir(parents=True)
    assert resolve_encoded_path("-Script-Asst--Project--Research", tmp_path) == target


def test_missing_path_is_orphan(tmp_path):
    (tmp_path / "projects").mkdir()
    assert resolve_encoded_path("-projects-gone-app", tmp_path) is None


def test_chats_uses_shared_decoder(tmp_path):
    """The chats scanner no longer reports underscore or dotted projects as orphaned."""
    chats = _load_chats()
    (tmp_path / "work" / "my_app").mkdir(parents=True)
    (tmp_path / "work" / "site.v2").mkdir(parents=True)

    exists, resolved = chats.verify_path_exists("-work-my-app", tmp_path)
    assert exists and resolved == str(tmp_path / "work" / "my_app")

    exists, resolved = chats.verify_path_exists("-work-site-v2", tmp_path)
    assert exists and resolved == str(tmp_path / "work" / "site.v2")

    exists, _ = chats.verify_path_exists("-work-gone", tmp_path)
    assert not exists
