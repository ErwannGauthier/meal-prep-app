import argparse
import fcntl
import logging
import shutil
import sys
from pathlib import Path

from .app import Services, import_notion, reextract, run
from .config import Config, load_config
from .downloader import Downloader
from .extractor import Extractor
from .publish import publish
from .sources.feed import Feed
from .state import retry_failed
from .store import Store
from .transcriber import Transcriber


def build_services(cfg: Config, root: Path, force_cpu: bool) -> Services:
    store = Store(root)
    return Services(
        store=store,
        downloader=Downloader(store.work_dir, store.sources_dir, cfg.cookies_file),
        transcriber=Transcriber(cfg.whisper, force_cpu=force_cpu),
        extractor=Extractor(cfg.claude_model, store.work_dir / "claude"),
        feed=Feed(cfg.account, cfg.cookies_file),
        publish=lambda message: publish(root, message),
    )


def acquire_lock(root: Path):
    """Un seul lancement à la fois : deux lancements feraient deux téléchargements en parallèle."""
    path = Store(root).work_dir / "pipeline.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def exit_code(summary) -> int:
    """0 : terminé ; 1 : arrêt anticipé ou publication en échec."""
    return 1 if summary.stopped or summary.publish_error else 0


def preflight(cfg: Config, force_cpu: bool, *, extraction_only: bool = False) -> list[str]:
    """Problèmes d'installation à corriger avant de toucher à la file."""
    problems = []
    tools = ["claude"] if extraction_only else ["ffmpeg", "claude"]
    problems += [f"commande introuvable : {t}" for t in tools if shutil.which(t) is None]
    if extraction_only:
        return problems
    w = cfg.whisper
    if not w.bin.is_file():
        problems.append(f"whisper-cli introuvable : {w.bin}")
    models = [w.cpu_model] + ([w.gpu_model] if w.use_gpu and not force_cpu else [])
    problems += [f"modèle Whisper introuvable : {m}" for m in models if not m.is_file()]
    if cfg.cookies_file and not cfg.cookies_file.is_file():
        problems.append(f"fichier de cookies introuvable : {cfg.cookies_file}")
    return problems


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m pipeline", description="Catalogue des meal preps @bourr_")
    p.add_argument("--root", type=Path, default=Path("."), help="racine du dépôt (défaut : .)")
    p.add_argument("--config", type=Path, default=None, help="fichier de config (défaut : <root>/config.toml)")
    sub = p.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="ajoute à la file les reels d'un export Notion")
    imp.add_argument("export", type=Path, help="fichier .csv/.md/.txt, dossier ou .zip")

    r = sub.add_parser("run", help="traite la file et les nouveautés, puis publie")
    r.add_argument("--no-publish", action="store_true", help="ne pas faire de git push")
    r.add_argument("--cpu", action="store_true", help="forcer whisper.cpp sur CPU")

    re_ = sub.add_parser("reextract", help="relance l'extraction Claude depuis les transcriptions")
    re_.add_argument("ids", nargs="*", help="shortcodes (défaut : toutes les recettes)")
    re_.add_argument("--no-publish", action="store_true")

    rt = sub.add_parser("retry", help="remet dans la file les reels en échec")
    rt.add_argument("ids", nargs="*", help="shortcodes (défaut : tous les reels en échec)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = args.root.resolve()

    lock = acquire_lock(root)
    if lock is None:
        print("Un autre lancement du pipeline est déjà en cours dans ce dossier.", file=sys.stderr)
        return 3
    try:
        return _dispatch(args, root)
    finally:
        lock.close()


def _dispatch(args: argparse.Namespace, root: Path) -> int:
    if args.command == "import":
        n = import_notion(Store(root), args.export)
        print(f"{n} reel(s) ajouté(s) à la file.")
        return 0

    if args.command == "retry":
        store = Store(root)
        state = store.load_state()
        requeued = retry_failed(state, args.ids or None)
        store.save_state(state)
        print(f"{len(requeued)} reel(s) remis dans la file.")
        return 0

    config_path = args.config or root / "config.toml"
    try:
        cfg = load_config(config_path)
    except FileNotFoundError:
        print(f"Config introuvable : {config_path}. Copie config.example.toml en config.toml puis adapte-le.",
              file=sys.stderr)
        return 2
    except (KeyError, ValueError) as e:
        print(f"Config invalide ({config_path}) : {e}", file=sys.stderr)
        return 2

    force_cpu = getattr(args, "cpu", False)
    problems = preflight(cfg, force_cpu, extraction_only=args.command == "reextract")
    if problems:
        print("Installation incomplète, rien n'a été traité :", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    svc = build_services(cfg, root, force_cpu=force_cpu)
    if args.command == "run":
        summary = run(cfg, svc, do_publish=not args.no_publish)
    else:
        summary = reextract(cfg, svc, args.ids or None, do_publish=not args.no_publish)
    print(summary.render())
    return exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
