import json
from pathlib import Path

from .errors import ClaudeUnavailable, ReelError
from .models import CATEGORIES, ExtractionResult, Ingredient
from .proc import Runner, run_cmd

PROMPT = """Tu analyses un reel Instagram du créateur @bourr_, qui publie des meal preps \
(repas préparés à l'avance pour plusieurs jours).

À partir de la description et de la transcription audio ci-dessous :

1. isMealPrep : true seulement si le reel présente une recette de meal prep. \
Sinon renvoie uniquement {{"isMealPrep": false}}.
2. Sinon remplis "recipe" :
   - title : nom court et appétissant de la recette, en français.
   - region : région culinaire d'origine. Réutilise si possible une valeur de cette liste : {regions}. \
Sinon propose une valeur courte (ex. "Mexique", "Asie du Sud-Est"). null si aucune origine identifiable.
   - portions : nombre de portions ou de boîtes annoncé, sinon null.
   - ingredients : un élément par ingrédient.
     * raw : ligne lisible pour une liste de courses en français (ex. "1 kg de blanc de poulet").
     * quantity (nombre) et unit ("g", "kg", "ml", "cl", "l", "c. à soupe", "c. à café", "pièce"…), \
null si non précisés. Utilise des unités métriques.
     * ingredientId : l'id d'un ingrédient du référentiel ci-dessous s'il s'agit du même produit, \
sans tenir compte de la découpe ni de la marque ("blanc de poulet" → "poulet"). Sinon, ajoute \
l'ingrédient dans "newIngredients" avec un id en minuscules sans accents, mots séparés par des tirets, \
un "name" au singulier et une "category" parmi : {categories}.
   - steps : étapes de préparation courtes, à l'impératif, dans l'ordre.
   - macros : valeurs PAR PORTION (kcal, et protein, carbs, fat en grammes), entiers. \
source = "announced" si le créateur les donne (vidéo ou description), sinon "estimated" en les calculant \
à partir des ingrédients et quantités. null si les quantités sont trop imprécises pour estimer.

N'invente aucun ingrédient absent de la vidéo et de la description.

Référentiel d'ingrédients existant (id: nom) :
{ingredients}

Description :
<<<
{caption}
>>>

Transcription audio :
<<<
{transcript}
>>>
"""

_VALIDATION_KEYWORDS = {
    "pattern", "minLength", "maxLength", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems",
}


def loose_schema() -> dict:
    """Schéma JSON pour claude -p, sans contraintes de validation : pydantic les vérifie ensuite."""
    def clean(node):
        if isinstance(node, dict):
            return {k: clean(v) for k, v in node.items() if k not in _VALIDATION_KEYWORDS}
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node
    return clean(ExtractionResult.model_json_schema())


def build_prompt(caption: str, transcript: str, ingredients: list[Ingredient], regions: list[str]) -> str:
    referential = "\n".join(f"{i.id}: {i.name}" for i in ingredients) or "(vide)"
    return PROMPT.format(
        regions=", ".join(regions) or "(aucune pour l'instant)",
        categories=", ".join(CATEGORIES),
        ingredients=referential,
        caption=caption.strip() or "(aucune)",
        transcript=transcript.strip() or "(aucune parole)",
    )


def validate_result(data: object, known_ids: set[str]) -> ExtractionResult:
    result = ExtractionResult.model_validate(data)
    if not result.isMealPrep:
        return ExtractionResult(isMealPrep=False)
    if result.recipe is None:
        raise ValueError("isMealPrep vaut true mais la recette est absente")
    used = {x.ingredientId for x in result.recipe.ingredients}
    available = set(known_ids)
    new: list[Ingredient] = []
    for ing in result.newIngredients:
        if ing.id not in available and ing.id in used:
            new.append(ing)
        available.add(ing.id)
    missing = sorted(used - available)
    if missing:
        raise ValueError(f"ingrédients absents du référentiel et de newIngredients : {missing}")
    return ExtractionResult(isMealPrep=True, recipe=result.recipe, newIngredients=new)


class Extractor:
    def __init__(self, model: str, work_dir: Path, runner: Runner = run_cmd):
        self.model = model
        self.work_dir = work_dir
        self.runner = runner
        self._schema = json.dumps(loose_schema())

    def extract(self, caption: str, transcript: str, ingredients: list[Ingredient],
                regions: list[str]) -> ExtractionResult:
        prompt = build_prompt(caption, transcript, ingredients, regions)
        known = {i.id for i in ingredients}
        last_error = ""
        for _ in range(2):
            data = self._call(prompt)
            try:
                return validate_result(data, known)
            except ValueError as e:  # pydantic.ValidationError hérite de ValueError
                last_error = str(e)[:300]
        raise ReelError(f"extraction invalide : {last_error}")

    def _call(self, prompt: str) -> object:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        res = self.runner(
            ["claude", "-p", "--model", self.model, "--output-format", "json",
             "--json-schema", self._schema, "--tools", "",
             "--no-session-persistence", "--strict-mcp-config"],
            input=prompt, cwd=self.work_dir, timeout=600,
        )
        try:
            payload = json.loads(res.stdout)
        except json.JSONDecodeError:
            detail = (res.stderr or res.stdout).strip()[-300:]
            raise ClaudeUnavailable(f"claude -p a échoué (code {res.returncode}) : {detail}") from None
        if res.returncode != 0 or payload.get("is_error"):
            raise ClaudeUnavailable(f"claude -p : {payload.get('result') or payload.get('subtype')}")
        return payload.get("structured_output")
