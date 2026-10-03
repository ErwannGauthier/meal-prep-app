import { useEffect, useState } from 'react'
import type { Ingredient, Recipe } from '../types'

export interface Catalog {
  recipes: Recipe[]
  ingredients: Ingredient[]
  ingredientsById: Map<string, Ingredient>
}

export type CatalogState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; catalog: Catalog }

export function dataUrl(path: string): string {
  return `${import.meta.env.BASE_URL}data/${path}`
}

function isUsableRecipe(r: unknown): r is Recipe {
  if (typeof r !== 'object' || r === null) return false
  const x = r as Record<string, unknown>
  return typeof x.id === 'string' && typeof x.title === 'string' && Array.isArray(x.ingredients) && Array.isArray(x.steps)
}

export async function loadCatalog(fetchFn: typeof fetch = fetch): Promise<Catalog> {
  async function getList<T>(name: string): Promise<T[]> {
    const res = await fetchFn(dataUrl(name), { cache: 'no-cache' })
    if (!res.ok) throw new Error(`${name} : HTTP ${res.status}`)
    const data: unknown = await res.json()
    if (!Array.isArray(data)) throw new Error(`${name} : format inattendu`)
    return data as T[]
  }
  // Une recette incomplète est écartée plutôt que de faire tomber tout le site.
  const recipes = (await getList<Recipe>('recipes.json')).filter(isUsableRecipe)
  const ingredients = await getList<Ingredient>('ingredients.json')
  return { recipes, ingredients, ingredientsById: new Map(ingredients.map((i) => [i.id, i])) }
}

export function useCatalog(fetchFn: typeof fetch = fetch): CatalogState {
  const [state, setState] = useState<CatalogState>({ status: 'loading' })
  useEffect(() => {
    let alive = true
    loadCatalog(fetchFn)
      .then((catalog) => alive && setState({ status: 'ready', catalog }))
      .catch((e: unknown) => alive && setState({ status: 'error', message: e instanceof Error ? e.message : String(e) }))
    return () => {
      alive = false
    }
  }, [fetchFn])
  return state
}
