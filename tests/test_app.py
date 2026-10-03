from pathlib import Path

import pytest

from pipeline.app import MAX_STALLS, NOT_MEAL_PREP_ERROR, Services, import_notion, reextract, run
from pipeline.config import Config, WhisperConfig
from pipeline.downloader import Download
from pipeline.errors import Blocked, ClaudeUnavailable, ReelError
from pipeline.models import ExtractionResult
from pipeline.sources.feed import FeedPost
from pipeline.state import add_pending, record_attempt
from pipeline.store import Store
from tests.factories import RIZ, extracted

NOT_MP = ExtractionResult(isMealPrep=False)


def mp(title="Poulet riz"):
    return ExtractionResult(isMealPrep=True, recipe=extracted(("riz",), title), newIngredients=[RIZ])


def cfg(**kw):
    base = dict(account="bourr_", max_reels_per_run=30, max_attempts=3, delay_min_s=1,
                delay_max_s=2, cookies_file=None, claude_model="m",
                whisper=WhisperConfig(Path("w"), Path("g"), Path("c"), True))
    return Config(**{**base, **kw})


class FakeDownloader:
    def __init__(self, work: Path, errors=None, probe_ok=False, staging: Path | None = None):
        self.work, self.errors, self.fetched, self.cleaned = work, errors or {}, [], []
        self.staging = staging
        self.probe_ok, self.probed = probe_ok, []

    def probe(self, rid):
        self.probed.append(rid)
        return self.probe_ok

    def fetch(self, rid):
        self.fetched.append(rid)
        if rid in self.errors:
            raise self.errors[rid]
        self.work.mkdir(parents=True, exist_ok=True)
        wav = self.work / f"{rid}.16k.wav"
        wav.write_bytes(b"x")
        thumb = None
        if self.staging:
            self.staging.mkdir(parents=True, exist_ok=True)
            thumb = self.staging / f"{rid}.webp"
            thumb.write_bytes(b"webp")
        return Download(wav=wav, caption=f"caption {rid}", posted_at="2026-05-14", thumbnail=thumb)

    def cleanup(self, rid):
        self.cleaned.append(rid)


class FakeTranscriber:
    def transcribe(self, wav):
        return "transcription"


class FakeExtractor:
    """Réponse choisie selon la description : 'caption <rid>'."""

    def __init__(self, by_rid):
        self.by_rid, self.calls = by_rid, []

    def extract(self, caption, transcript, ingredients, regions):
        rid = caption.removeprefix("caption ")
        self.calls.append(rid)
        out = self.by_rid[rid]
        if isinstance(out, Exception):
            raise out
        return out


class FakeFeed:
    def __init__(self, posts=(), error=None):
        self.posts, self.error = list(posts), error

    def latest_reels(self):
        if self.error:
            raise self.error
        return self.posts


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def services(store, extractor, downloader=None, feed=None):
    published, sleeps = [], []
    svc = Services(
        store=store,
        downloader=downloader or FakeDownloader(store.work_dir),
        transcriber=FakeTranscriber(),
        extractor=extractor,
        feed=feed or FakeFeed(),
        publish=lambda msg: published.append(msg) or True,
        sleep=sleeps.append,
        rand=lambda a, b: a,
    )
    return svc, published, sleeps


def queue(store, *ids, source="notion"):
    state = store.load_state()
    add_pending(state, ids, source)
    store.save_state(state)


def test_import_notion_queues_links(store, tmp_path):
    export = tmp_path / "export.md"
    export.write_text("https://www.instagram.com/reel/AAAAA1/ https://www.instagram.com/reel/BBBBB2/")
    assert import_notion(store, export) == 2
    assert import_notion(store, export) == 0
    state = store.load_state()
    assert [(k, v.status, v.source) for k, v in state.reels.items()] == [
        ("AAAAA1", "pending", "notion"), ("BBBBB2", "pending", "notion")]


def test_run_processes_queue_saves_recipes_sources_and_publishes(store):
    queue(store, "A", "B")
    svc, published, sleeps = services(store, FakeExtractor({"A": mp("Recette A"), "B": mp("Recette B")}))
    s = run(cfg(), svc)
    assert s.new_recipes == ["Recette A", "Recette B"] and s.processed == 2
    recipes = {r.id: r for r in store.load_recipes()}
    assert recipes["A"].url == "https://www.instagram.com/reel/A/"
    assert recipes["A"].postedAt == "2026-05-14"
    assert store.load_source("A").transcript == "transcription"
    assert {k: v.status for k, v in store.load_state().reels.items()} == {"A": "done", "B": "done"}
    assert sleeps == [1]                       # une pause entre deux téléchargements
    assert published == ["🍱 data: 2 nouvelle(s) recette(s)"] and s.published
    assert svc.downloader.cleaned == ["A", "B"]


def test_feed_reels_are_queued_and_non_meal_preps_skipped(store):
    feed = FakeFeed([FeedPost("F1", "2026-09-01", True), FeedPost("F2", "2026-09-02", True)])
    svc, _, _ = services(store, FakeExtractor({"F1": NOT_MP, "F2": mp()}), feed=feed)
    s = run(cfg(), svc)
    state = store.load_state()
    assert s.new_in_feed == 2 and s.not_meal_prep == 1
    assert (state.reels["F1"].source, state.reels["F1"].status) == ("feed", "not_meal_prep")
    assert state.reels["F2"].status == "done"
    assert state.lastFeedCheck is not None


def test_notion_reel_classified_not_meal_prep_fails_for_manual_check(store):
    queue(store, "A")
    svc, _, _ = services(store, FakeExtractor({"A": NOT_MP}))
    s = run(cfg(), svc)
    reel = store.load_state().reels["A"]
    assert (reel.status, reel.error, reel.attempts) == ("failed", NOT_MEAL_PREP_ERROR, 3)
    assert s.failed == [("A", NOT_MEAL_PREP_ERROR)]
    svc2, _, _ = services(store, FakeExtractor({}))
    assert run(cfg(), svc2).processed == 0     # jamais repris automatiquement


def test_reel_error_marks_failed_and_continues(store):
    queue(store, "A", "B")
    dl = FakeDownloader(store.work_dir, errors={"A": ReelError("yt-dlp : no longer available")})
    svc, _, _ = services(store, FakeExtractor({"B": mp()}), downloader=dl)
    s = run(cfg(), svc)
    state = store.load_state()
    assert (state.reels["A"].status, state.reels["A"].attempts) == ("failed", 1)
    assert state.reels["B"].status == "done"
    assert s.failed == [("A", "yt-dlp : no longer available")]


BLOCK = Blocked("empty media response, use --cookies")


def seed_done(store, *ids):
    """Reels déjà traités : ils servent de référence pour sonder Instagram."""
    state = store.load_state()
    add_pending(state, ids, "notion")
    for rid in ids:
        record_attempt(state, rid, "done")
    store.save_state(state)


def statuses(store):
    return {k: (v.status, v.attempts) for k, v in store.load_state().reels.items()}


def test_refusal_while_known_reels_are_refused_too_is_a_block(store):
    seed_done(store, "REF")
    queue(store, "A", "B")
    dl = FakeDownloader(store.work_dir, errors={"A": BLOCK}, probe_ok=False)
    svc, published, _ = services(store, FakeExtractor({}), downloader=dl)
    s = run(cfg(), svc)
    reel = store.load_state().reels["A"]
    assert s.stopped == str(BLOCK)
    assert dl.probed == ["REF"] and dl.fetched == ["A"]      # B n'est pas tenté
    assert (reel.status, reel.attempts, reel.stalls) == ("pending", 0, 0)
    assert len(published) == 1


def test_adjacent_dead_links_do_not_freeze_the_queue(store):
    # yt-dlp répond « use --cookies » aussi pour un reel supprimé. Si un reel déjà
    # traité reste accessible, le refus vient du reel, pas d'un blocage.
    seed_done(store, "REF")
    queue(store, "A", "B", "C", "D")
    dl = FakeDownloader(store.work_dir, errors={"A": BLOCK, "B": BLOCK}, probe_ok=True)
    svc, _, _ = services(store, FakeExtractor({"C": mp("Recette C"), "D": mp("Recette D")}), downloader=dl)
    s = run(cfg(), svc)
    st = statuses(store)
    assert s.stopped is None
    assert st["A"] == ("failed", 1) and st["B"] == ("failed", 1)
    assert "empty media response" in store.load_state().reels["A"].error
    assert s.new_recipes == ["Recette C", "Recette D"]


def test_without_reference_a_later_successful_download_marks_the_refused_reel_failed(store):
    queue(store, "A", "B", "C")
    dl = FakeDownloader(store.work_dir, errors={"A": BLOCK})
    svc, _, _ = services(store, FakeExtractor({"B": mp("Recette B"), "C": mp("Recette C")}), downloader=dl)
    s = run(cfg(), svc)
    assert s.stopped is None
    assert statuses(store)["A"] == ("failed", 1)
    assert s.failed and s.failed[0][0] == "A"
    assert s.new_recipes == ["Recette B", "Recette C"]


def test_download_that_works_clears_suspicion_even_if_extraction_then_fails(store):
    queue(store, "A", "B")
    dl = FakeDownloader(store.work_dir, errors={"A": BLOCK})
    svc, _, _ = services(store, FakeExtractor({"B": ReelError("extraction invalide")}), downloader=dl)
    s = run(cfg(), svc)
    st = statuses(store)
    assert s.stopped is None
    assert st["A"] == ("failed", 1) and st["B"] == ("failed", 1)


def test_without_reference_two_refusals_stop_the_run_and_are_remembered(store):
    queue(store, "A", "B", "C")
    dl = FakeDownloader(store.work_dir, errors={"A": BLOCK, "B": BLOCK})
    svc, _, _ = services(store, FakeExtractor({}), downloader=dl)
    s = run(cfg(), svc)
    state = store.load_state()
    assert s.stopped == str(BLOCK) and dl.fetched == ["A", "B"]
    for rid in ("A", "B"):
        assert (state.reels[rid].status, state.reels[rid].attempts, state.reels[rid].stalls) == ("pending", 0, 1)


def test_reels_that_keep_interrupting_runs_are_given_up_so_the_queue_advances(store):
    queue(store, "A", "B", "C")
    for _ in range(MAX_STALLS):
        dl = FakeDownloader(store.work_dir, errors={"A": BLOCK, "B": BLOCK})
        svc, _, _ = services(store, FakeExtractor({}), downloader=dl)
        assert run(cfg(), svc).stopped
    st = statuses(store)
    assert st["A"][0] == "failed" and st["B"][0] == "failed"
    assert "lancements" in store.load_state().reels["A"].error

    dl = FakeDownloader(store.work_dir)
    svc, _, _ = services(store, FakeExtractor({"C": mp("Recette C")}), downloader=dl)
    s = run(cfg(), svc)
    assert dl.fetched == ["C"] and s.new_recipes == ["Recette C"] and s.stopped is None


def test_claude_error_tied_to_one_reel_does_not_freeze_the_queue(store):
    queue(store, "A", "B")
    for _ in range(MAX_STALLS):
        svc, _, _ = services(store, FakeExtractor({"A": ClaudeUnavailable("timeout")}))
        assert run(cfg(), svc).stopped == "timeout"
    assert statuses(store)["A"][0] == "failed"
    svc, _, _ = services(store, FakeExtractor({"B": mp("Recette B")}))
    assert run(cfg(), svc).new_recipes == ["Recette B"]


def test_unexpected_exception_fails_the_reel_and_the_run_continues(store):
    queue(store, "A", "B")
    dl = FakeDownloader(store.work_dir, errors={"A": RuntimeError("octet invalide")})
    svc, published, _ = services(store, FakeExtractor({"B": mp()}), downloader=dl)
    s = run(cfg(), svc)
    state = store.load_state()
    assert (state.reels["A"].status, state.reels["A"].attempts) == ("failed", 1)
    assert "RuntimeError" in state.reels["A"].error and "octet invalide" in state.reels["A"].error
    assert state.reels["B"].status == "done" and len(published) == 1


def test_three_consecutive_failures_stop_the_run_before_burning_the_whole_queue(store):
    queue(store, "A", "B", "C", "D")
    boom = ReelError("whisper (CPU) : commande introuvable")
    dl = FakeDownloader(store.work_dir, errors={"A": boom, "B": boom, "C": boom})
    svc, _, _ = services(store, FakeExtractor({"D": mp()}), downloader=dl)
    s = run(cfg(), svc)
    assert "3 échecs consécutifs" in s.stopped
    assert dl.fetched == ["A", "B", "C"]
    assert statuses(store)["D"] == ("pending", 0)


def test_stored_errors_do_not_reveal_the_home_directory(store):
    queue(store, "A")
    dl = FakeDownloader(store.work_dir, errors={"A": ReelError(f"ffmpeg (audio) : {Path.home()}/x/A.wav: invalid data")})
    svc, _, _ = services(store, FakeExtractor({}), downloader=dl)
    s = run(cfg(), svc)
    error = store.load_state().reels["A"].error
    assert str(Path.home()) not in error and "~/x/A.wav" in error
    assert str(Path.home()) not in s.render()


def test_claude_unavailable_keeps_transcript_and_resumes_without_download(store):
    queue(store, "A")
    svc, _, _ = services(store, FakeExtractor({"A": ClaudeUnavailable("quota")}))
    assert run(cfg(), svc).stopped == "quota"
    assert store.has_source("A")
    assert store.load_state().reels["A"].status == "pending"

    dl = FakeDownloader(store.work_dir)
    svc2, _, _ = services(store, FakeExtractor({"A": mp()}), downloader=dl)
    run(cfg(), svc2)
    assert dl.fetched == []
    assert store.load_state().reels["A"].status == "done"


def test_feed_blocked_is_reported_and_queue_still_processed(store):
    queue(store, "A")
    svc, _, _ = services(store, FakeExtractor({"A": mp()}), feed=FakeFeed(error=Blocked("401")))
    s = run(cfg(), svc)
    assert s.feed_error == "401" and s.new_recipes == ["Poulet riz"]


def test_batch_limit_and_no_publish(store):
    queue(store, "A", "B", "C")
    svc, published, _ = services(store, FakeExtractor({"A": mp(), "B": mp()}))
    s = run(cfg(max_reels_per_run=2), svc, do_publish=False)
    assert s.processed == 2 and published == []
    assert store.load_state().reels["C"].status == "pending"


def test_reextract_updates_recipe_from_sources_without_download(store):
    queue(store, "A")
    svc, _, _ = services(store, FakeExtractor({"A": mp("Ancien titre")}))
    run(cfg(), svc)
    dl = FakeDownloader(store.work_dir)
    svc2, published, _ = services(store, FakeExtractor({"A": mp("Nouveau titre")}), downloader=dl)
    s = reextract(cfg(), svc2, None)
    assert [r.title for r in store.load_recipes()] == ["Nouveau titre"]
    assert dl.fetched == [] and s.new_recipes == ["Nouveau titre"]
    assert published == ["🍱 data: 1 recette(s) ré-extraite(s)"]


def test_reextract_not_meal_prep_keeps_existing_recipe(store):
    queue(store, "A")
    svc, _, _ = services(store, FakeExtractor({"A": mp()}))
    run(cfg(), svc)
    svc2, _, _ = services(store, FakeExtractor({"A": NOT_MP}))
    s = reextract(cfg(), svc2, ["A"])
    assert [r.id for r in store.load_recipes()] == ["A"]
    assert s.failed and s.failed[0][0] == "A"


def test_summary_render_mentions_key_facts(store):
    queue(store, "A", "B")
    dl = FakeDownloader(store.work_dir, errors={"B": ReelError("boom")})
    svc, _, _ = services(store, FakeExtractor({"A": mp("Recette A")}), downloader=dl)
    text = run(cfg(), svc).render()
    assert "Recette A" in text and "B : boom" in text and "Publication" in text


def test_only_kept_recipes_get_a_thumbnail_on_the_site(store):
    feed = FakeFeed([FeedPost("VLOG", "2026-09-01", True), FeedPost("PREP", "2026-09-02", True)])
    queue(store, "KO")
    dl = FakeDownloader(store.work_dir, staging=store.sources_dir)
    extractor = FakeExtractor({"KO": ReelError("extraction invalide"), "VLOG": NOT_MP, "PREP": mp()})
    svc, _, _ = services(store, extractor, downloader=dl, feed=feed)
    run(cfg(), svc)
    assert sorted(p.name for p in store.thumbs_dir.iterdir()) == ["PREP.webp"]
    assert {r.id: r.thumbnail for r in store.load_recipes()} == {"PREP": "thumbs/PREP.webp"}


def test_thumbnail_survives_a_resume_without_download(store):
    queue(store, "A")
    dl = FakeDownloader(store.work_dir, staging=store.sources_dir)
    svc, _, _ = services(store, FakeExtractor({"A": ClaudeUnavailable("quota")}), downloader=dl)
    run(cfg(), svc)
    svc2, _, _ = services(store, FakeExtractor({"A": mp()}), downloader=FakeDownloader(store.work_dir))
    run(cfg(), svc2)
    assert store.load_recipes()[0].thumbnail == "thumbs/A.webp"
