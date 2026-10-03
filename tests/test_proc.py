from pipeline.proc import run_cmd


def test_run_cmd_captures_output():
    res = run_cmd(["python3", "-c", "import sys; print('ok'); print('err', file=sys.stderr)"])
    assert (res.returncode, res.stdout.strip(), res.stderr.strip()) == (0, "ok", "err")


def test_run_cmd_passes_stdin():
    res = run_cmd(["python3", "-c", "import sys; print(sys.stdin.read().upper())"], input="abc")
    assert res.stdout.strip() == "ABC"


def test_run_cmd_missing_binary_returns_127():
    res = run_cmd(["commande-qui-n-existe-pas-42"])
    assert res.returncode == 127
    assert "introuvable" in res.stderr


def test_run_cmd_tolerates_invalid_utf8_output():
    res = run_cmd(["python3", "-c", "import sys; sys.stdout.buffer.write(b'ok \\xff fin')"])
    assert res.returncode == 0 and res.stdout.startswith("ok ") and res.stdout.endswith(" fin")
