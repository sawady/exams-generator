from pathlib import Path

from exams_generator.config import Settings, normalize_locale


def test_defaults():
    s = Settings.from_env({})
    assert s.transport == "stdio"
    assert s.data_dir == Path("data")
    assert s.exams_dir == Path("data/exams")
    assert s.git_backup is True
    assert s.git_push is False
    assert s.locale == "en"


def test_env_overrides(tmp_path):
    s = Settings.from_env(
        {
            "EXAMS_DATA_DIR": str(tmp_path / "d"),
            "EXAMS_DIR": str(tmp_path / "private-exams"),
            "EXAMS_GIT_BACKUP": "false",
            "EXAMS_GIT_PUSH": "yes",
            "EXAMS_LOCALE": "es_AR",
            "EXAMS_TRANSPORT": "HTTP",
            "EXAMS_HTTP_PORT": "9000",
            "EXAMS_BEARER_TOKEN": " secret ",
            "EXAMS_ALLOWED_HOSTS": "exams.example.org, other.example.org",
        }
    )
    assert s.exams_dir == tmp_path / "private-exams"
    assert s.git_backup is False and s.git_push is True
    assert s.locale == "es"
    assert s.transport == "http" and s.http_port == 9000
    assert s.bearer_token == "secret"
    assert s.allowed_hosts == ("exams.example.org", "other.example.org")


def test_normalize_locale():
    assert normalize_locale("ES") == "es"
    assert normalize_locale("fr", "en") == "en"
    assert normalize_locale(None, "es") == "es"
