"""The Claude Code plugin stays coherent with the package."""

import json
import re
import struct
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


def test_directory_icon_is_a_square_png_the_directory_accepts():
    # The directory wants a square PNG or JPEG, 512 to 2048 px a side, under 2 MB.
    icon = ROOT / MANIFEST["icon"]
    data = icon.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert width == height
    assert 512 <= width <= 2048
    assert len(data) < 2 * 1024 * 1024


def test_directory_listing_links_are_https():
    for field in ("homepage", "documentationUrl", "supportUrl", "privacyPolicyUrl"):
        assert MANIFEST[field].startswith("https://"), field
    assert (ROOT / "PRIVACY.md").is_file()
