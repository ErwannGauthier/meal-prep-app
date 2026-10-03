from pathlib import Path

from .errors import PublishError
from .proc import Runner, run_cmd

SITE_DATA = "web/public/data"   # ce que le site affiche : seule une nouveauté ici justifie un commit
STATE_FILE = "data/state.json"  # suit dans le même commit ; data/sources reste en local


def publish(repo: Path, message: str, runner: Runner = run_cmd) -> bool:
    if not (repo / SITE_DATA).exists():
        return False
    add = runner(["git", "add", "--", SITE_DATA], cwd=repo)
    if add.returncode != 0:
        raise PublishError(f"git add : {add.stderr.strip()}")
    if runner(["git", "diff", "--cached", "--quiet", "--", SITE_DATA], cwd=repo).returncode == 0:
        return False
    paths = [SITE_DATA]
    if (repo / STATE_FILE).exists():
        add = runner(["git", "add", "--", STATE_FILE], cwd=repo)
        if add.returncode != 0:
            raise PublishError(f"git add : {add.stderr.strip()}")
        paths.append(STATE_FILE)
    commit = runner(["git", "commit", "-q", "-m", message, "--", *paths], cwd=repo)
    if commit.returncode != 0:
        raise PublishError(f"git commit : {commit.stderr.strip()}")
    push = runner(["git", "push", "-q"], cwd=repo, timeout=120)
    if push.returncode != 0:
        raise PublishError(
            f"git push a échoué ; les données restent commitées localement : {push.stderr.strip()}"
        )
    return True
