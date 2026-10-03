import json
import os
import shutil
import tempfile
from pathlib import Path

from .errors import IntegrityError
from .models import Ingredient, Recipe, SourceDoc, State


def write_json_atomic(path: Path, data: object) -> None:
    """Écrit dans un fichier temporaire puis le renomme : jamais de JSON à moitié écrit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class Store:
    def __init__(self, root: Path):
        self.root = root
        web_data = root / "web" / "public" / "data"
        self.recipes_path = web_data / "recipes.json"
        self.ingredients_path = web_data / "ingredients.json"
        self.thumbs_dir = web_data / "thumbs"
        self.state_path = root / "data" / "state.json"
        self.sources_dir = root / "data" / "sources"
        self.work_dir = root / "data" / "work"

    # --- catalogue -------------------------------------------------------
    def load_recipes(self) -> list[Recipe]:
        return [Recipe.model_validate(r) for r in _read_json(self.recipes_path, [])]

    def load_ingredients(self) -> list[Ingredient]:
        return [Ingredient.model_validate(i) for i in _read_json(self.ingredients_path, [])]

    def save_catalog(self, recipes: list[Recipe], ingredients: list[Ingredient]) -> None:
        ids = [i.id for i in ingredients]
        if len(ids) != len(set(ids)):
            raise IntegrityError("identifiants d'ingrédients en double")
        known = set(ids)
        for r in recipes:
            missing = sorted({x.ingredientId for x in r.ingredients} - known)
            if missing:
                raise IntegrityError(f"{r.id} : ingrédients inconnus {missing}")
        recipes = sorted(recipes, key=lambda r: r.postedAt or "", reverse=True)
        ingredients = sorted(ingredients, key=lambda i: i.id)
        # Ingrédients d'abord : si on s'arrête entre les deux écritures,
        # le référentiel contient des extras mais reste cohérent.
        write_json_atomic(self.ingredients_path, [i.model_dump() for i in ingredients])
        write_json_atomic(self.recipes_path, [r.model_dump() for r in recipes])

    def upsert_recipe(self, recipe: Recipe, new_ingredients: list[Ingredient]) -> None:
        ingredients = self.load_ingredients()
        known = {i.id for i in ingredients}
        for ing in new_ingredients:
            if ing.id not in known:
                ingredients.append(ing)
                known.add(ing.id)
        recipes = [r for r in self.load_recipes() if r.id != recipe.id] + [recipe]
        self.save_catalog(recipes, ingredients)

    def thumbnail_rel(self, reel_id: str) -> str | None:
        if (self.thumbs_dir / f"{reel_id}.webp").exists():
            return f"thumbs/{reel_id}.webp"
        return None

    def staged_thumbnail(self, reel_id: str) -> Path:
        """Miniature téléchargée, gardée hors du site tant que le reel n'est pas retenu."""
        return self.sources_dir / f"{reel_id}.webp"

    def promote_thumbnail(self, reel_id: str) -> str | None:
        staged = self.staged_thumbnail(reel_id)
        if staged.exists():
            self.thumbs_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged, self.thumbs_dir / f"{reel_id}.webp")
        return self.thumbnail_rel(reel_id)

    # --- état et sources ---------------------------------------------------
    def load_state(self) -> State:
        return State.model_validate(_read_json(self.state_path, {}))

    def save_state(self, state: State) -> None:
        write_json_atomic(self.state_path, state.model_dump())

    def _source_path(self, reel_id: str) -> Path:
        return self.sources_dir / f"{reel_id}.json"

    def has_source(self, reel_id: str) -> bool:
        return self._source_path(reel_id).exists()

    def load_source(self, reel_id: str) -> SourceDoc:
        return SourceDoc.model_validate(_read_json(self._source_path(reel_id), None))

    def save_source(self, doc: SourceDoc) -> None:
        write_json_atomic(self._source_path(doc.id), doc.model_dump())
