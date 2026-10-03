from typing import get_args

import pytest
from pydantic import ValidationError

from pipeline.models import CATEGORIES, Category, ExtractionResult, Ingredient, Recipe
from tests.factories import make_recipe


def test_categories_are_the_eight_aisles_in_order():
    assert list(CATEGORIES) == [
        "viandes-poissons", "fruits-legumes", "feculents", "produits-laitiers-oeufs",
        "epicerie", "epices-condiments", "surgeles", "autre",
    ]
    assert set(get_args(Category)) == set(CATEGORIES)


def test_ingredient_rejects_non_slug_id():
    with pytest.raises(ValidationError):
        Ingredient(id="Blanc de poulet", name="Poulet", category="viandes-poissons")


def test_ingredient_rejects_unknown_category():
    with pytest.raises(ValidationError):
        Ingredient(id="poulet", name="Poulet", category="boucherie")


def test_extraction_result_not_meal_prep_is_minimal():
    r = ExtractionResult.model_validate({"isMealPrep": False})
    assert r.recipe is None
    assert r.newIngredients == []


def test_recipe_roundtrips_through_json():
    r = make_recipe()
    assert Recipe.model_validate_json(r.model_dump_json()) == r
