import { CATEGORIES, type Category, type Ingredient, type Recipe, type RecipeIngredient } from '../types'

export interface IngredientSection {
  category: Category
  label: string
  items: RecipeIngredient[]
}

export function groupRecipeIngredients(recipe: Recipe, ingredientsById: Map<string, Ingredient>): IngredientSection[] {
  const categoryOf = (i: RecipeIngredient): Category => ingredientsById.get(i.ingredientId)?.category ?? 'autre'
  return CATEGORIES.map(({ id, label }) => ({
    category: id,
    label,
    items: recipe.ingredients.filter((i) => categoryOf(i) === id),
  })).filter((s) => s.items.length > 0)
}

export function formatShoppingList(recipe: Recipe, ingredientsById: Map<string, Ingredient>): string {
  const lines = [`${recipe.title} — courses`]
  for (const section of groupRecipeIngredients(recipe, ingredientsById)) {
    lines.push('', section.label, ...section.items.map((i) => i.raw))
  }
  return lines.join('\n')
}
