from typing import Literal

from pydantic import BaseModel, Field

CATEGORIES: dict[str, str] = {
    "viandes-poissons": "Viandes & poissons",
    "fruits-legumes": "Fruits & légumes",
    "feculents": "Féculents",
    "produits-laitiers-oeufs": "Produits laitiers & œufs",
    "epicerie": "Épicerie",
    "epices-condiments": "Épices & condiments",
    "surgeles": "Surgelés",
    "autre": "Autre",
}

Category = Literal[
    "viandes-poissons", "fruits-legumes", "feculents", "produits-laitiers-oeufs",
    "epicerie", "epices-condiments", "surgeles", "autre",
]

SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class Ingredient(BaseModel):
    id: str = Field(pattern=SLUG)
    name: str = Field(min_length=1)
    category: Category


class RecipeIngredient(BaseModel):
    ingredientId: str = Field(pattern=SLUG)
    quantity: float | None
    unit: str | None
    raw: str = Field(min_length=1)


class Macros(BaseModel):
    kcal: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    source: Literal["announced", "estimated"]


class ExtractedRecipe(BaseModel):
    """Ce que Claude produit pour un reel meal prep."""

    title: str = Field(min_length=1)
    region: str | None
    portions: int | None = Field(ge=1)
    ingredients: list[RecipeIngredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    macros: Macros | None


class Recipe(ExtractedRecipe):
    """Une entrée de recipes.json (contrat avec le site)."""

    id: str
    url: str
    postedAt: str | None
    thumbnail: str | None
    extractedAt: str


class ExtractionResult(BaseModel):
    isMealPrep: bool
    recipe: ExtractedRecipe | None = None
    newIngredients: list[Ingredient] = Field(default_factory=list)


Status = Literal["pending", "done", "not_meal_prep", "failed"]
SourceKind = Literal["notion", "feed"]


class ReelState(BaseModel):
    status: Status = "pending"
    source: SourceKind
    attempts: int = 0
    stalls: int = 0  # lancements interrompus par ce reel sans verdict
    error: str | None = None
    updatedAt: str


class State(BaseModel):
    reels: dict[str, ReelState] = Field(default_factory=dict)
    lastFeedCheck: str | None = None


class SourceDoc(BaseModel):
    """data/sources/<id>.json : de quoi ré-extraire sans retoucher Instagram."""

    id: str
    caption: str
    transcript: str
    postedAt: str | None
