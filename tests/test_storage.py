import json
import subprocess

import pytest

from exams_generator.storage import Storage, StorageError
from tests.conftest import requires_git


def git_log(path):
    out = subprocess.run(
        ["git", "log", "--format=%s"], cwd=path, capture_output=True, text=True, check=True
    )
    return out.stdout.split("\n")[:-1]


@pytest.fixture
def storage(tmp_path):
    return Storage(tmp_path / "exams", git_backup=False)


def test_save_load_roundtrip(storage):
    meta = storage.save_exam(
        "midterm-1",
        "# Statement\n",
        {"Exam.hs": "module Exam where\n", "notes.h": "int x;\n"},
        title="Trees",
        tags=["trees"],
        locale="es",
        languages=["haskell"],
    )
    assert meta.solution_files == ["Exam.hs", "notes.h"]
    exam = storage.load_exam("midterm-1")
    assert exam.statement == "# Statement\n"
    assert exam.solution == {"Exam.hs": "module Exam where\n", "notes.h": "int x;\n"}
    assert exam.metadata.title == "Trees"
    assert exam.metadata.locale == "es"
    assert [m.name for m in storage.list_exams()] == ["midterm-1"]


def test_resave_replaces_solution_and_keeps_created_at(storage):
    first = storage.save_exam("e", "v1", {"a.py": "x = 1\n", "b.py": "y = 2\n"}, title="T")
    second = storage.save_exam("e", "v2", {"a.py": "x = 3\n"})
    exam = storage.load_exam("e")
    assert exam.solution == {"a.py": "x = 3\n"}  # b.py is gone
    assert second.created_at == first.created_at
    assert second.title == "T"  # kept when not given again


def test_save_drops_stale_pdfs(storage):
    storage.save_exam("e", "v1", {})
    storage.pdf_path("e").write_bytes(b"%PDF")
    storage.save_exam("e", "v2", {})
    assert not storage.pdf_path("e").exists()


@pytest.mark.parametrize("name", ["", "../x", "a/b", "-start", "x" * 65, "sp ace"])
def test_invalid_names(storage, name):
    with pytest.raises(StorageError):
        storage.save_exam(name, "", {})


@pytest.mark.parametrize("filename", ["../evil.hs", "dir/file.c", ".hidden", "a..b", ""])
def test_invalid_solution_filenames(storage, filename):
    with pytest.raises(StorageError):
        storage.save_exam("ok", "", {filename: ""})
    assert not storage.exists("ok")


def test_missing_exam(storage):
    with pytest.raises(StorageError):
        storage.load_exam("nope")
    with pytest.raises(StorageError):
        storage.delete_exam("nope")


def test_delete(storage):
    storage.save_exam("e", "", {})
    storage.delete_exam("e")
    assert storage.list_exams() == []


def test_metadata_tolerates_garbage(storage):
    storage.save_exam("e", "", {"a.c": ""})
    storage.metadata_path("e").write_text("{not json")
    meta = storage.list_exams()[0]
    assert meta.name == "e"
    assert meta.solution_files == ["a.c"]


def test_mark_rendered_and_check(storage):
    storage.save_exam("e", "", {})
    storage.mark_rendered("e", "statement")
    meta = storage.record_check("e", True, [{"language": "c", "ok": True}])
    assert meta.rendered == ["statement"]
    assert meta.last_check["ok"] is True
    on_disk = json.loads(storage.metadata_path("e").read_text())
    assert on_disk["last_check"]["languages"] == {"c": True}


@requires_git
def test_git_backup_commits_each_change(tmp_path):
    storage = Storage(tmp_path / "exams", git_backup=True)
    storage.save_exam("e", "v1", {"a.py": ""})
    storage.mark_rendered("e", "statement")
    storage._commit("nothing changed")  # clean tree: no empty commit
    storage.delete_exam("e")
    assert git_log(tmp_path / "exams") == [
        "delete exam: e",
        "render statement pdf: e",
        "save exam: e",
    ]


@requires_git
def test_reuses_existing_repo_and_pushes(tmp_path):
    # A bare "remote" and a clone of it, like a private content repository.
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    for key, value in (("user.email", "t@example.org"), ("user.name", "T")):
        subprocess.run(["git", "config", key, value], cwd=clone, check=True)
    (clone / "README.md").write_text("private exams\n")
    subprocess.run(["git", "add", "."], cwd=clone, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=clone, check=True)
    subprocess.run(
        ["git", "push", "-q", "-u", "origin", "main"], cwd=clone, check=True, capture_output=True
    )

    storage = Storage(clone, git_backup=True, git_push=True)
    storage.save_exam("e", "stmt", {"a.py": ""})
    assert storage.last_git_error is None
    pushed = subprocess.run(
        ["git", "log", "--format=%s", "main"], cwd=remote, capture_output=True, text=True
    ).stdout.split("\n")[:-1]
    assert pushed == ["save exam: e", "init"]
    assert storage.git_status()["remotes"] == ["origin"]


@requires_git
def test_nested_dir_gets_its_own_repo(tmp_path):
    outer = tmp_path / "tool-clone"
    outer.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=outer, check=True)
    storage = Storage(outer / "data" / "exams", git_backup=True)
    storage.save_exam("e", "", {})
    assert (outer / "data" / "exams" / ".git").is_dir()
    outer_log = subprocess.run(["git", "log"], cwd=outer, capture_output=True, text=True)
    assert outer_log.returncode != 0  # the outer repo still has no commits


@requires_git
def test_git_failure_does_not_fail_save(tmp_path):
    storage = Storage(tmp_path / "exams", git_backup=True, git_push=True)  # no remote
    storage.save_exam("e", "", {})
    assert storage.exists("e")
    assert storage.last_git_error
