import json

import pytest

from pipeline.errors import ClaudeUnavailable, ReelError
from pipeline.extractor import Extractor, build_prompt, loose_schema
from tests.conftest import FakeRunner, fail, ok
from tests.factories import POULET, extracted

RIZ_NEW = {"id": "riz", "name": "Riz", "category": "feculents"}


def claude_ok(structured) -> object:
    return ok(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                          "result": "", "structured_output": structured}))


def meal_prep(ids=("poulet", "riz"), new=(RIZ_NEW,)):
    return {"isMealPrep": True, "recipe": extracted(ids).model_dump(), "newIngredients": list(new)}


def run(outputs, tmp_path):
    queue = list(outputs)
    runner = FakeRunner(lambda args: queue.pop(0))
    ex = Extractor("claude-sonnet-5-5", tmp_path / "claude", runner)
    return ex, runner


def test_valid_meal_prep_is_returned_with_new_ingredients(tmp_path):
    ex, runner = run([claude_ok(meal_prep())], tmp_path)
    r = ex.extract("desc", "transcription", [POULET], ["France"])
    assert r.isMealPrep and r.recipe.title == "Poulet riz"
    assert [i.id for i in r.newIngredients] == ["riz"]
    [call] = runner.calls
    assert call.args[:2] == ["claude", "-p"]
    assert call.args[call.args.index("--tools") + 1] == ""
    assert "--json-schema" in call.args and "--no-session-persistence" in call.args
    assert call.cwd == tmp_path / "claude" and call.cwd.is_dir()


def test_prompt_contains_inputs_referential_and_regions():
    p = build_prompt("Meal prep satay", "on coupe le poulet", [POULET], ["Asie du Sud-Est"])
    assert "Meal prep satay" in p and "on coupe le poulet" in p
    assert "poulet: Poulet" in p
    assert "Asie du Sud-Est" in p
    assert "viandes-poissons" in p


def test_not_meal_prep(tmp_path):
    ex, _ = run([claude_ok({"isMealPrep": False})], tmp_path)
    r = ex.extract("vlog salle de sport", "", [POULET], [])
    assert not r.isMealPrep and r.recipe is None


def test_unknown_ingredient_triggers_one_retry(tmp_path):
    bad = meal_prep(ids=("poulet", "tofu"), new=())
    ex, runner = run([claude_ok(bad), claude_ok(meal_prep())], tmp_path)
    r = ex.extract("desc", "t", [POULET], [])
    assert len(runner.calls) == 2
    assert {i.ingredientId for i in r.recipe.ingredients} == {"poulet", "riz"}


def test_invalid_twice_is_a_reel_error(tmp_path):
    bad = meal_prep(ids=("poulet", "tofu"), new=())
    ex, runner = run([claude_ok(bad), claude_ok({"isMealPrep": True})], tmp_path)
    with pytest.raises(ReelError, match="extraction invalide"):
        ex.extract("desc", "t", [POULET], [])
    assert len(runner.calls) == 2


def test_new_ingredient_reusing_existing_id_is_dropped(tmp_path):
    rival = {"id": "poulet", "name": "Poulet fermier", "category": "autre"}
    ex, _ = run([claude_ok(meal_prep(new=(rival, RIZ_NEW, RIZ_NEW)))], tmp_path)
    r = ex.extract("desc", "t", [POULET], [])
    assert [i.id for i in r.newIngredients] == ["riz"]


def test_unused_new_ingredient_is_dropped(tmp_path):
    unused = {"id": "tofu", "name": "Tofu", "category": "autre"}
    ex, _ = run([claude_ok(meal_prep(new=(RIZ_NEW, unused)))], tmp_path)
    assert [i.id for i in ex.extract("d", "t", [POULET], []).newIngredients] == ["riz"]


def test_non_json_output_means_claude_unavailable(tmp_path):
    ex, _ = run([fail("Invalid API key · Please run /login")], tmp_path)
    with pytest.raises(ClaudeUnavailable, match="login"):
        ex.extract("d", "t", [], [])


def test_is_error_means_claude_unavailable(tmp_path):
    payload = ok(json.dumps({"type": "result", "subtype": "error_during_execution",
                             "is_error": True, "result": "Usage limit reached"}))
    ex, _ = run([payload], tmp_path)
    with pytest.raises(ClaudeUnavailable, match="Usage limit"):
        ex.extract("d", "t", [], [])


def test_loose_schema_has_no_validation_keywords():
    text = json.dumps(loose_schema())
    for kw in ('"pattern"', '"minLength"', '"minItems"', '"minimum"'):
        assert kw not in text
    assert "isMealPrep" in text and "newIngredients" in text
