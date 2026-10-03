import shutil
from pathlib import Path

from pipeline.__main__ import acquire_lock, build_services, exit_code, main
from pipeline.app import RunSummary
from pipeline.config import load_config
from pipeline.store import Store

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def test_import_command_queues_links(tmp_path, capsys):
    export = tmp_path / "export.txt"
    export.write_text("https://www.instagram.com/reel/AAAAA1/")
    assert main(["--root", str(tmp_path), "import", str(export)]) == 0
    assert "1 reel(s) ajouté(s)" in capsys.readouterr().out
    assert list(Store(tmp_path).load_state().reels) == ["AAAAA1"]


def test_run_without_config_explains_what_to_do(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "run", "--no-publish"]) == 2
    assert "config.example.toml" in capsys.readouterr().err


def test_build_services_wires_paths_and_cpu_flag(tmp_path):
    shutil.copy(EXAMPLE, tmp_path / "config.toml")
    cfg = load_config(tmp_path / "config.toml")
    svc = build_services(cfg, tmp_path, force_cpu=True)
    assert svc.store.root == tmp_path
    assert svc.downloader.work_dir == tmp_path / "data/work"
    assert svc.downloader.thumbs_dir == tmp_path / "data/sources"   # en attente, hors du site
    assert svc.transcriber.use_gpu is False
    assert svc.extractor.model == "claude-sonnet-5-5"
    assert svc.feed.username == "bourr_"


def test_run_refuses_to_start_when_tools_are_missing_and_touches_no_reel(tmp_path, capsys):
    shutil.copy(EXAMPLE, tmp_path / "config.toml")
    text = (tmp_path / "config.toml").read_text().replace("~/whisper.cpp", str(tmp_path / "absent"))
    (tmp_path / "config.toml").write_text(text)
    export = tmp_path / "export.txt"
    export.write_text("https://www.instagram.com/reel/AAAAA1/")
    main(["--root", str(tmp_path), "import", str(export)])
    assert main(["--root", str(tmp_path), "run", "--no-publish"]) == 2
    assert "whisper-cli introuvable" in capsys.readouterr().err
    reel = Store(tmp_path).load_state().reels["AAAAA1"]
    assert (reel.status, reel.attempts) == ("pending", 0)


def test_retry_command_requeues_failed_reels(tmp_path, capsys):
    from pipeline.state import add_pending, give_up
    store = Store(tmp_path)
    state = store.load_state()
    add_pending(state, ["A", "B"], "notion")
    give_up(state, "A", "boom", max_attempts=3)
    store.save_state(state)
    assert main(["--root", str(tmp_path), "retry"]) == 0
    assert "1 reel(s) remis dans la file" in capsys.readouterr().out
    assert Store(tmp_path).load_state().reels["A"].status == "pending"


def test_a_second_run_is_refused_while_one_is_in_progress(tmp_path, capsys):
    # Deux lancements en même temps = deux téléchargements en parallèle sur Instagram.
    lock = acquire_lock(tmp_path)
    assert lock is not None
    assert acquire_lock(tmp_path) is None
    assert main(["--root", str(tmp_path), "retry"]) == 3
    assert "déjà en cours" in capsys.readouterr().err
    lock.close()
    assert main(["--root", str(tmp_path), "retry"]) == 0


def test_exit_code_is_non_zero_on_early_stop_or_publish_failure():
    assert exit_code(RunSummary()) == 0
    assert exit_code(RunSummary(failed=[("A", "lien mort")])) == 0
    assert exit_code(RunSummary(stopped="use --cookies")) == 1
    assert exit_code(RunSummary(publish_error="git push a échoué")) == 1
