import pytest

from exams_generator.checkers import Checker, CheckerRegistry, UnknownLanguageError
from exams_generator.checkers.haskell import _inject_module_header, module_name_for
from tests.conftest import has_toolchain, requires


@pytest.fixture
def registry():
    return CheckerRegistry(timeout=120, load_plugins=False)


# ------------------------------------------------------------- registry


def test_builtin_languages(registry):
    assert set(registry.names) >= {"haskell", "c", "cpp", "python"}


@pytest.mark.parametrize("alias,name", [("hs", "haskell"), ("C++", "cpp"), ("py", "python")])
def test_aliases(registry, alias, name):
    assert registry.get(alias).name == name


def test_unknown_language(registry):
    with pytest.raises(UnknownLanguageError):
        registry.get("cobol")


def test_describe_reports_availability(registry):
    rows = {row["language"]: row for row in registry.describe()}
    for name in ("haskell", "c", "cpp", "python"):
        assert isinstance(rows[name]["available"], bool)
        if not rows[name]["available"]:
            assert rows[name]["hint"]
    assert rows["python"]["available"]  # the interpreter running the tests


def test_routing(registry):
    files = {"Exam.hs": "", "q.h": "", "q.c": "", "x.cpp": "", "s.py": "", "notes.txt": ""}
    assert registry.languages_for(files) == ["haskell", "c", "cpp", "python"]
    assert registry.languages_for({"notes.txt": ""}) == []


def test_missing_toolchain_is_skipped_not_passed(monkeypatch, registry):
    monkeypatch.setenv("EXAMS_GHC", "definitely-not-a-real-ghc")
    checker = registry.get("haskell")
    assert not checker.availability().available
    result = checker.check_snippet("x = 1")
    assert result.skipped and not result.ok


def test_custom_checker_plugin(registry):
    class TrueChecker(Checker):
        name = "truthy"
        source_extensions = (".tru",)
        default_executables = ("true",)
        default_filename = "a.tru"

        def build_commands(self, exe, sources, workdir):
            return [[exe, *sources]]

    registry.register(TrueChecker)
    assert registry.languages_for({"a.tru": ""}) == ["truthy"]
    if registry.get("truthy").availability().available:
        assert registry.check_files({"a.tru": "anything"})[0].ok


def test_timeout(monkeypatch):
    class SleepChecker(Checker):
        name = "sleepy"
        source_extensions = (".zz",)
        default_executables = ("sleep",)

        def build_commands(self, exe, sources, workdir):
            return [[exe, "5"]]

    checker = SleepChecker(timeout=0.2)
    if not checker.availability().available:
        pytest.skip("no sleep binary")
    result = checker.check_files({"a.zz": ""})
    assert not result.ok and "Timed out" in result.stderr


# -------------------------------------------------------------- haskell


def test_module_name_for():
    assert module_name_for("exam.hs") == "Exam"
    assert module_name_for("my-exam.hs") == "My_exam"
    assert module_name_for("1st.hs") == "M1st"


def test_inject_header_after_pragmas():
    src = "{-# LANGUAGE LambdaCase #-}\n-- comment\nf = 1\n"
    out = _inject_module_header(src, "Exam", "Exam.hs")
    lines = out.splitlines()
    assert lines[0].startswith("{-# LANGUAGE")
    assert lines[2] == "module Exam where"
    assert lines[3] == '{-# LINE 3 "Exam.hs" #-}'


@requires("haskell")
def test_haskell_ok_and_error(registry):
    hs = registry.get("haskell")
    assert hs.check_snippet("module Exam where\nf :: Int -> Int\nf = (+ 1)\n").ok
    bad = hs.check_snippet("f :: Int -> Bool\nf x = x\n")
    assert not bad.ok
    assert "Exam.hs:2:" in bad.stderr  # original line numbers survive the injected header


@requires("haskell")
def test_haskell_multi_module(registry):
    files = {
        "Exam.hs": "module Exam where\nimport Helper\ng :: Int\ng = h 1\n",
        "Helper.hs": "module Helper where\nh :: Int -> Int\nh = (+ 1)\n",
    }
    (result,) = registry.check_files(files)
    assert result.ok, result.as_text()
    assert result.files == ["Exam.hs", "Helper.hs"]


# -------------------------------------------------------------------- C


@requires("c")
def test_c_ok_error_and_warning(registry):
    c = registry.get("c")
    assert c.check_snippet("int f(int x) { return x + 1; }\n").ok
    assert not c.check_snippet('int f(int x) { return x + "a"; }\n').ok
    warn = c.check_snippet("int f(int x) { int y; return x; }\n")
    assert warn.ok and warn.has_diagnostics


@requires("c")
def test_c_header_and_source(registry):
    files = {
        "stack.h": "struct S;\ntypedef struct S* Stack;\nStack emptyStack(void);\n",
        "stack.c": '#include <stdlib.h>\n#include "stack.h"\nstruct S { int top; };\n'
        "Stack emptyStack(void) { return malloc(sizeof(struct S)); }\n",
    }
    (result,) = registry.check_files(files)
    assert result.language == "c" and result.ok, result.as_text()
    assert result.files == ["stack.c"]


@requires("c")
def test_c_flags_override(monkeypatch, registry):
    monkeypatch.setenv("EXAMS_CFLAGS", "-std=c11 -Wall -Werror")
    assert not registry.get("c").check_snippet("int f(int x) { int y; return x; }\n").ok


# ------------------------------------------------------------------ C++


@requires("cpp")
def test_cpp_ok_and_error(registry):
    cpp = registry.get("cpp")
    assert cpp.check_snippet('#include <string>\nstd::string f() { return "a"; }\n').ok
    assert not cpp.check_snippet("int f() { return nope; }\n").ok


@requires("cpp")
def test_h_header_goes_to_cpp_when_there_are_cpp_sources(registry):
    files = {
        "q.h": "struct QSt;\ntypedef QSt* Q;\nQ newQ();\n",  # C++-only typedef
        "q.cpp": '#include "q.h"\nstruct QSt { int n; };\nQ newQ() { return new QSt; }\n',
    }
    results = registry.check_files(files)
    assert [r.language for r in results] == ["cpp"]
    assert results[0].ok, results[0].as_text()


# --------------------------------------------------------------- python


def test_python_syntax(registry):
    py = registry.get("python")
    assert py.check_snippet("def f(x):\n    return x\n").ok
    bad = py.check_snippet("def f(x:\n")
    assert not bad.ok and "SyntaxError" in bad.stderr


def test_python_typecheck_none(monkeypatch, registry):
    monkeypatch.setenv("EXAMS_PYTHON_TYPECHECK", "none")
    assert registry.get("python").check_snippet("def f(x: int) -> str:\n    return x\n").ok


@pytest.mark.skipif(not has_toolchain("python"), reason="no python")
def test_python_mypy(monkeypatch, registry):
    pytest.importorskip("mypy")
    monkeypatch.setenv("EXAMS_PYTHON_TYPECHECK", "mypy")
    bad = registry.get("python").check_snippet("def f(x: int) -> str:\n    return x\n")
    assert not bad.ok and "return-value" in bad.stdout
