import subprocess

import pytest

from pipeline.errors import PublishError
from pipeline.publish import publish


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "test@example.com")
    git(r, "config", "user.name", "Test")
    (r / "README.md").write_text("x\n")
    git(r, "add", "README.md")
    git(r, "commit", "-q", "-m", "init")
    git(r, "remote", "add", "origin", str(remote))
    git(r, "push", "-q", "-u", "origin", "main")
    return r, remote


def test_nothing_to_publish_returns_false(repo):
    r, _ = repo
    assert publish(r, "data: rien") is False


def test_data_changes_are_committed_and_pushed_but_not_other_files(repo):
    r, remote = repo
    (r / "web/public/data").mkdir(parents=True)
    (r / "web/public/data/recipes.json").write_text("[]\n")
    (r / "data").mkdir()
    (r / "data/state.json").write_text("{}\n")
    (r / "README.md").write_text("modifié\n")
    assert publish(r, "data: 1 nouvelle recette") is True
    assert "data: 1 nouvelle recette" in git(remote, "log", "--oneline")
    assert git(r, "status", "--porcelain").strip() == "M README.md"


def test_push_failure_raises_but_keeps_local_commit(repo):
    r, _ = repo
    git(r, "remote", "set-url", "origin", str(r.parent / "absent.git"))
    (r / "web/public/data").mkdir(parents=True)
    (r / "web/public/data/recipes.json").write_text("[]\n")
    with pytest.raises(PublishError, match="push"):
        publish(r, "data: test")
    assert "data: test" in git(r, "log", "--oneline")


def test_state_change_alone_creates_no_commit(repo):
    # Pas de nouveauté pour le site → pas de commit (l'historique reste propre).
    r, remote = repo
    (r / "data").mkdir()
    (r / "data/state.json").write_text('{"lastFeedCheck": "2026-10-03T10:00:00Z"}\n')
    assert publish(r, "data: 0 nouvelle(s) recette(s)") is False
    assert git(remote, "log", "--oneline").count("\n") == 1
    assert git(r, "status", "--porcelain").strip() == "?? data/"


def test_state_rides_along_with_site_data_but_sources_stay_local(repo):
    r, remote = repo
    (r / "web/public/data").mkdir(parents=True)
    (r / "web/public/data/recipes.json").write_text("[]\n")
    (r / "data/sources").mkdir(parents=True)
    (r / "data/state.json").write_text("{}\n")
    (r / "data/sources/ABC.json").write_text('{"transcript": "texte du créateur"}\n')
    assert publish(r, "data: 1 nouvelle recette") is True
    tracked = git(r, "ls-files").split()
    assert "data/state.json" in tracked and "web/public/data/recipes.json" in tracked
    assert not any(f.startswith("data/sources") for f in tracked)
