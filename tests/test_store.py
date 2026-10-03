import json

import pytest

from pipeline.errors import IntegrityError
from pipeline.models import Ingredient, SourceDoc, State
from pipeline.store import Store, write_json_atomic
from tests.factories import POULET, RIZ, make_recipe


def test_missing_files_read_as_empty(tmp_path):
    s = Store(tmp_path)
    assert s.load_recipes() == []
    assert s.load_ingredients() == []
    assert s.load_state() == State()


def test_paths_follow_the_contract(tmp_path):
    s = Store(tmp_path)
    assert s.recipes_path == tmp_path / "web/public/data/recipes.json"
    assert s.ingredients_path == tmp_path / "web/public/data/ingredients.json"
    assert s.thumbs_dir == tmp_path / "web/public/data/thumbs"
    assert s.state_path == tmp_path / "data/state.json"
    assert s.sources_dir == tmp_path / "data/sources"
    assert s.work_dir == tmp_path / "data/work"


def test_upsert_writes_recipe_and_new_ingredients(tmp_path):
    s = Store(tmp_path)
    s.upsert_recipe(make_recipe(), [POULET])
    assert [r.id for r in s.load_recipes()] == ["ABC"]
    assert s.load_ingredients() == [POULET]
    raw = json.loads(s.recipes_path.read_text(encoding="utf-8"))
    assert raw[0]["ingredients"][0]["ingredientId"] == "poulet"


def test_upsert_replaces_recipe_with_same_id(tmp_path):
    s = Store(tmp_path)
    s.upsert_recipe(make_recipe(title="Avant"), [POULET])
    s.upsert_recipe(make_recipe(title="Après"), [])
    assert [r.title for r in s.load_recipes()] == ["Après"]


def test_new_ingredient_colliding_with_existing_keeps_existing(tmp_path):
    s = Store(tmp_path)
    s.upsert_recipe(make_recipe(), [POULET])
    rival = Ingredient(id="poulet", name="Poulet fermier", category="autre")
    s.upsert_recipe(make_recipe(rid="DEF", ingredient_ids=("poulet", "riz")), [rival, RIZ, RIZ])
    assert s.load_ingredients() == [POULET, RIZ]


def test_unknown_ingredient_is_rejected_and_nothing_written(tmp_path):
    s = Store(tmp_path)
    with pytest.raises(IntegrityError, match="tofu"):
        s.upsert_recipe(make_recipe(ingredient_ids=("tofu",)), [])
    assert not s.recipes_path.exists()


def test_recipes_sorted_newest_first_with_unknown_dates_last(tmp_path):
    s = Store(tmp_path)
    for rid, date in [("A", "2026-01-01"), ("B", None), ("C", "2026-03-01")]:
        s.upsert_recipe(make_recipe(rid=rid, posted_at=date), [POULET])
    assert [r.id for r in s.load_recipes()] == ["C", "A", "B"]


def test_atomic_write_keeps_previous_file_on_failure(tmp_path, monkeypatch):
    p = tmp_path / "x.json"
    write_json_atomic(p, {"a": 1})

    def boom(*args, **kwargs):
        raise RuntimeError("crash pendant l'écriture")

    monkeypatch.setattr("pipeline.store.json.dump", boom)
    with pytest.raises(RuntimeError):
        write_json_atomic(p, {"b": 2})
    assert json.loads(p.read_text()) == {"a": 1}
    assert list(tmp_path.iterdir()) == [p]


def test_atomic_write_keeps_accents_readable(tmp_path):
    p = tmp_path / "x.json"
    write_json_atomic(p, {"name": "Épicerie"})
    assert "Épicerie" in p.read_text(encoding="utf-8")


def test_source_roundtrip(tmp_path):
    s = Store(tmp_path)
    doc = SourceDoc(id="ABC", caption="desc", transcript="texte", postedAt="2026-05-14")
    assert not s.has_source("ABC")
    s.save_source(doc)
    assert s.has_source("ABC")
    assert s.load_source("ABC") == doc


def test_thumbnail_rel_only_when_file_exists(tmp_path):
    s = Store(tmp_path)
    assert s.thumbnail_rel("ABC") is None
    s.thumbs_dir.mkdir(parents=True)
    (s.thumbs_dir / "ABC.webp").write_bytes(b"x")
    assert s.thumbnail_rel("ABC") == "thumbs/ABC.webp"


def test_state_roundtrip(tmp_path):
    s = Store(tmp_path)
    state = State.model_validate(
        {"reels": {"ABC": {"source": "notion", "updatedAt": "2026-10-02T00:00:00Z"}}}
    )
    s.save_state(state)
    assert s.load_state() == state


def test_staged_thumbnail_is_promoted_to_the_site_only_on_request(tmp_path):
    s = Store(tmp_path)
    assert s.promote_thumbnail("ABC") is None
    s.sources_dir.mkdir(parents=True)
    s.staged_thumbnail("ABC").write_bytes(b"webp")
    assert s.staged_thumbnail("ABC") == s.sources_dir / "ABC.webp"
    assert not (s.thumbs_dir / "ABC.webp").exists()
    assert s.promote_thumbnail("ABC") == "thumbs/ABC.webp"
    assert (s.thumbs_dir / "ABC.webp").read_bytes() == b"webp"


def test_promote_keeps_an_already_published_thumbnail(tmp_path):
    s = Store(tmp_path)
    s.thumbs_dir.mkdir(parents=True)
    (s.thumbs_dir / "ABC.webp").write_bytes(b"old")
    assert s.promote_thumbnail("ABC") == "thumbs/ABC.webp"
