from pipeline.models import ExtractedRecipe, Ingredient, Macros, Recipe, RecipeIngredient

POULET = Ingredient(id="poulet", name="Poulet", category="viandes-poissons")
RIZ = Ingredient(id="riz", name="Riz", category="feculents")


def extracted(ingredient_ids: tuple[str, ...] = ("poulet",), title: str = "Poulet riz") -> ExtractedRecipe:
    return ExtractedRecipe(
        title=title,
        region="France",
        portions=5,
        ingredients=[
            RecipeIngredient(ingredientId=i, quantity=1, unit="kg", raw=f"1 kg de {i}")
            for i in ingredient_ids
        ],
        steps=["Cuire."],
        macros=Macros(kcal=600, protein=45, carbs=60, fat=15, source="estimated"),
    )


def make_recipe(
    rid: str = "ABC",
    posted_at: str | None = "2026-01-01",
    ingredient_ids: tuple[str, ...] = ("poulet",),
    title: str = "Poulet riz",
) -> Recipe:
    return Recipe(
        **extracted(ingredient_ids, title).model_dump(),
        id=rid,
        url=f"https://www.instagram.com/reel/{rid}/",
        postedAt=posted_at,
        thumbnail=None,
        extractedAt="2026-10-02T00:00:00Z",
    )
