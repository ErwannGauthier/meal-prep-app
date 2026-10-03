import { CATEGORIES, type Category, type Ingredient, type Recipe } from '../types'
import { normalizeText } from './text'

export interface Filters {
  query: string
  ingredientIds: string[]
  region: string | null
}

export const EMPTY_FILTERS: Filters = { query: '', ingredientIds: [], region: null }

export function hasActiveFilters(f: Filters): boolean {
  return f.query.trim() !== '' || f.ingredientIds.length > 0 || f.region !== null
}

export function filterRecipes(recipes: Recipe[], f: Filters): Recipe[] {
  const words = normalizeText(f.query).split(' ').filter(Boolean)
  return recipes.filter((r) => {
    const title = normalizeText(r.title)
    if (!words.every((w) => title.includes(w))) return false
    if (f.region && r.region !== f.region) return false
    const present = new Set(r.ingredients.map((i) => i.ingredientId))
    return f.ingredientIds.every((id) => present.has(id))
  })
}

export function buildIngredientIndex(recipes: Recipe[]): Map<string, Set<string>> {
  const index = new Map<string, Set<string>>()
  for (const r of recipes) {
    for (const i of r.ingredients) {
      if (!index.has(i.ingredientId)) index.set(i.ingredientId, new Set())
      index.get(i.ingredientId)!.add(r.id)
    }
  }
  return index
}

export interface IngredientOption {
  id: string
  name: string
  count: number
}

export interface IngredientGroup {
  category: Category
  label: string
  items: IngredientOption[]
}

export function groupIngredients(ingredients: Ingredient[], index: Map<string, Set<string>>): IngredientGroup[] {
  return CATEGORIES.map(({ id, label }) => ({
    category: id,
    label,
    items: ingredients
      .filter((i) => i.category === id && index.has(i.id))
      .map((i) => ({ id: i.id, name: i.name, count: index.get(i.id)!.size }))
      .sort((a, b) => a.name.localeCompare(b.name, 'fr')),
  })).filter((g) => g.items.length > 0)
}

export function listRegions(recipes: Recipe[]): string[] {
  const regions = new Set(recipes.map((r) => r.region).filter((r): r is string => !!r))
  return [...regions].sort((a, b) => a.localeCompare(b, 'fr'))
}
