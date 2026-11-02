import pytest

from exams_generator.checkers import CheckerRegistry
from exams_generator.config import SUPPORTED_LOCALES
from exams_generator.content import Content
from tests.conftest import has_toolchain

LANGS = ["haskell", "c", "cpp", "python"]


@pytest.fixture
def content(tmp_path):
    return Content(tmp_path / "data")


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
@pytest.mark.parametrize("language", LANGS)
def test_bundled_guides_and_templates(content, language, locale):
    guide = content.style_guide(language, locale)
    assert guide.count("\n# ") >= 1  # general + language-specific
    assert content.template(language, "statement", locale)
    assert content.template(language, "solution", locale)


def test_unknown_locale_falls_back(content):
    assert content.style_guide(None, "fr") == content.style_guide(None, "en")


def test_data_dir_overrides(content):
    (content.data_dir / "style" / "en").mkdir(parents=True)
    (content.data_dir / "style" / "en" / "general.md").write_text("# House rules\n")
    (content.data_dir / "course.md").write_text("# My course\n")
    assert content.style_guide(None, "en").startswith("# House rules")
    assert content.course_profile() == "# My course\n"


def test_no_course_profile_by_default(content):
    assert content.course_profile() is None


def test_prompts_format(content):
    text = content.prompt("write_exam").format(
        topic="t",
        languages="c",
        locale="es",
        locale_name="Spanish",
        kind="exam",
        exercises="4",
        notes="-",
    )
    assert "Spanish" in text
    assert content.prompt("review_exam").format(name="x")


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
@pytest.mark.parametrize("language", LANGS)
def test_solution_templates_compile(content, language, locale):
    if not has_toolchain(language):
        pytest.skip(f"{language} toolchain not installed")
    checker = CheckerRegistry(timeout=120, load_plugins=False).get(language)
    result = checker.check_snippet(content.template(language, "solution", locale))
    assert result.ok, result.as_text()
