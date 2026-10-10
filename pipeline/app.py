import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .downloader import REEL_URL
from .errors import Blocked, ClaudeUnavailable, PublishError, ReelError
from .models import ExtractedRecipe, Recipe, SourceDoc, State
from .sources.notion import read_export
from .state import add_pending, give_up, now_iso, record_attempt, select_batch, stall
from .store import Store

log = logging.getLogger(__name__)

NOT_MEAL_PREP_ERROR = "classé non meal prep par Claude — à vérifier"
MAX_STALLS = 5                # lancements interrompus par un même reel avant abandon
MAX_CONSECUTIVE_FAILURES = 3  # au-delà, le problème vient sans doute de l'installation


@dataclass
class Services:
    store: Store
    downloader: object      # Downloader
    transcriber: object     # Transcriber
    extractor: object       # Extractor
    feed: object            # Feed
    publish: Callable[[str], bool]
    sleep: Callable[[float], None] = time.sleep
    rand: Callable[[float, float], float] = random.uniform


@dataclass
class RunSummary:
    new_in_feed: int = 0
    processed: int = 0
    new_recipes: list[str] = field(default_factory=list)
    not_meal_prep: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)
    stopped: str | None = None
    feed_error: str | None = None
    published: bool = False
    publish_error: str | None = None

    def render(self) -> str:
        lines = []
        if self.feed_error:
            lines.append(f"Feed indisponible : {self.feed_error}")
        else:
            lines.append(f"Feed : {self.new_in_feed} nouveau(x) reel(s)")
        lines.append(
            f"Traités : {self.processed} — nouvelles recettes : {len(self.new_recipes)}"
            f" — non meal prep : {self.not_meal_prep} — échecs : {len(self.failed)}"
        )
        lines += [f"  ✓ {t}" for t in self.new_recipes]
        lines += [f"  ✗ {rid} : {err}" for rid, err in self.failed]
        if self.stopped:
            lines.append(f"Arrêt anticipé (reprise au prochain lancement) : {self.stopped}")
        if self.publish_error:
            lines.append(f"Publication : échec — {self.publish_error}")
        else:
            lines.append(f"Publication : {'faite' if self.published else 'rien à publier'}")
        return "\n".join(lines)


def import_notion(store: Store, export: Path) -> int:
    state = store.load_state()
    added = add_pending(state, read_export(export), "notion")
    store.save_state(state)
    return len(added)


def _regions(store: Store) -> list[str]:
    return sorted({r.region for r in store.load_recipes() if r.region})


def _build_recipe(rid: str, src: SourceDoc, extracted: ExtractedRecipe, thumbnail: str | None) -> Recipe:
    return Recipe(
        **extracted.model_dump(),
        id=rid,
        url=REEL_URL.format(rid),
        postedAt=src.postedAt,
        thumbnail=thumbnail,
        extractedAt=now_iso(),
    )


def _extract(svc: Services, rid: str):
    src = svc.store.load_source(rid)
    result = svc.extractor.extract(src.caption, src.transcript, svc.store.load_ingredients(), _regions(svc.store))
    return src, result


def _store_result(cfg: Config, svc: Services, state: State, rid: str, summary: RunSummary) -> None:
    store = svc.store
    src, result = _extract(svc, rid)
    if not result.isMealPrep:
        if state.reels[rid].source == "notion":
            give_up(state, rid, NOT_MEAL_PREP_ERROR, cfg.max_attempts)
            summary.failed.append((rid, NOT_MEAL_PREP_ERROR))
        else:
            record_attempt(state, rid, "not_meal_prep")
            summary.not_meal_prep += 1
        return
    recipe = _build_recipe(rid, src, result.recipe, store.promote_thumbnail(rid))
    store.upsert_recipe(recipe, result.newIngredients)
    record_attempt(state, rid, "done")
    summary.new_recipes.append(recipe.title)


def _publish(svc: Services, summary: RunSummary, message: str) -> None:
    try:
        summary.published = svc.publish(message)
    except PublishError as e:
        summary.publish_error = str(e)


def _clean(message: str) -> str:
    """Les erreurs sont publiées dans state.json : pas de chemin personnel dedans."""
    return message.replace(str(Path.home()), "~")


def _fail(state: State, summary: RunSummary, rid: str, error: str) -> None:
    error = _clean(error)
    record_attempt(state, rid, "failed", error)
    summary.failed.append((rid, error))
    summary.processed += 1


def _stall(cfg: Config, state: State, summary: RunSummary, rid: str, error: str) -> None:
    error = _clean(error)
    if stall(state, rid, error, MAX_STALLS, cfg.max_attempts):
        summary.failed.append((rid, state.reels[rid].error))


def _instagram_answers(svc: Services, state: State) -> bool | None:
    """Sonde jusqu'à deux reels déjà traités. None : aucun reel de référence."""
    refs = [rid for rid, r in state.reels.items() if r.status == "done"][-2:]
    if not refs:
        return None
    return any(svc.downloader.probe(rid) for rid in reversed(refs))


def run(cfg: Config, svc: Services, *, do_publish: bool = True) -> RunSummary:
    summary = RunSummary()
    store = svc.store
    state = store.load_state()

    try:
        posts = svc.feed.latest_reels(known=state.reels.keys())
        summary.new_in_feed = len(add_pending(state, [p.shortcode for p in posts], "feed"))
        state.lastFeedCheck = now_iso()
    except Blocked as e:
        summary.feed_error = _clean(str(e))
    store.save_state(state)

    # yt-dlp répond la même chose (« use --cookies ») pour un blocage et pour un reel
    # supprimé. Pour trancher, on sonde un reel déjà traité : s'il répond, le refus
    # vient du reel ; sinon c'est un blocage. Sans reel de référence, le refus reste
    # « suspect » jusqu'au prochain téléchargement réussi.
    suspects: list[tuple[str, str]] = []
    consecutive_failures = 0
    downloaded = False
    for rid in select_batch(state, cfg.max_reels_per_run, cfg.max_attempts):
        needs_download = not store.has_source(rid)
        if needs_download and downloaded:
            svc.sleep(svc.rand(cfg.delay_min_s, cfg.delay_max_s))
        downloaded = downloaded or needs_download
        try:
            if needs_download:
                dl = svc.downloader.fetch(rid)
                for dead, message in suspects:
                    _fail(state, summary, dead, f"reel inaccessible (un autre reel se télécharge) : {message}")
                suspects = []
                transcript = svc.transcriber.transcribe(dl.wav) if dl.wav else ""
                store.save_source(SourceDoc(id=rid, caption=dl.caption, transcript=transcript, postedAt=dl.posted_at))
            _store_result(cfg, svc, state, rid, summary)
            summary.processed += 1
            consecutive_failures = 0
        except Blocked as e:
            answers = _instagram_answers(svc, state)
            if answers:
                _fail(state, summary, rid, f"reel inaccessible (Instagram répond pour d'autres reels) : {e}")
            elif answers is None:
                suspects.append((rid, str(e)))
                if len(suspects) >= 2:
                    break
            else:
                summary.stopped = _clean(str(e))
                break
        except ClaudeUnavailable as e:
            _stall(cfg, state, summary, rid, str(e))
            summary.stopped = _clean(str(e))
            break
        except Exception as e:  # un reel ne doit jamais faire tomber tout le lancement
            detail = str(e) if isinstance(e, ReelError) else f"{type(e).__name__}: {e}"
            _fail(state, summary, rid, detail)
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                summary.stopped = (
                    f"{MAX_CONSECUTIVE_FAILURES} échecs consécutifs, l'installation est sans doute en cause "
                    f"(dernier : {_clean(detail)})"
                )
                break
        finally:
            svc.downloader.cleanup(rid)
            store.save_state(state)

    if suspects:  # refus restés sans verdict : on s'en souvient pour ne pas buter dessus indéfiniment
        for rid, message in suspects:
            _stall(cfg, state, summary, rid, message)
        summary.stopped = summary.stopped or _clean(suspects[-1][1])
        store.save_state(state)

    if do_publish:
        _publish(svc, summary, f"🍱 data: {len(summary.new_recipes)} nouvelle(s) recette(s)")
    return summary


def reextract(cfg: Config, svc: Services, ids: list[str] | None, *, do_publish: bool = True) -> RunSummary:
    summary = RunSummary()
    store = svc.store
    state = store.load_state()
    targets = ids or [rid for rid, r in state.reels.items() if r.status == "done"]
    for rid in targets:
        if not store.has_source(rid):
            summary.failed.append((rid, "aucune source enregistrée"))
            continue
        try:
            src, result = _extract(svc, rid)
        except ClaudeUnavailable as e:
            summary.stopped = str(e)
            break
        except ReelError as e:
            summary.failed.append((rid, str(e)))
            continue
        summary.processed += 1
        if not result.isMealPrep:
            summary.failed.append((rid, "classé non meal prep à la ré-extraction ; recette conservée"))
            continue
        existing = next((r for r in store.load_recipes() if r.id == rid), None)
        thumbnail = store.promote_thumbnail(rid) or (existing.thumbnail if existing else None)
        recipe = _build_recipe(rid, src, result.recipe, thumbnail)
        store.upsert_recipe(recipe, result.newIngredients)
        if rid in state.reels:
            record_attempt(state, rid, "done")
        summary.new_recipes.append(recipe.title)
    store.save_state(state)
    if do_publish:
        _publish(svc, summary, f"🍱 data: {len(summary.new_recipes)} recette(s) ré-extraite(s)")
    return summary
