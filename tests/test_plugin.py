"""The Claude Code plugin stays coherent with the package."""

import json
import re
from pathlib import Path

import exams_generator

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def test_plugin_version_matches_package():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "(.+)"$', pyproject, re.MULTILINE)[1]
    assert MANIFEST["version"] == version
    assert exams_generator.__version__ == version


def test_commands_and_skill_exist():
    for path in MANIFEST["commands"]:
        assert list((ROOT / path).glob("*.md")), path
    assert (ROOT / "skills" / "exam-writing" / "SKILL.md").is_file()


def test_every_user_config_reference_is_declared():
    declared = set(MANIFEST["userConfig"])
    server = json.dumps(MANIFEST["mcpServers"])
    assert set(re.findall(r"\$\{user_config\.(\w+)\}", server)) == declared


def test_demos_are_off_by_default_in_the_plugin():
    assert MANIFEST["userConfig"]["run_demos"]["default"] is False
