import type { Recipe } from '../types'

export type SortKey = 'recent' | 'protein' | 'kcal' | 'ratio'

export const SORT_KEYS: readonly SortKey[] = ['recent', 'protein', 'kcal', 'ratio']

export const SORT_LABELS: Record<SortKey, string> = {
  recent: 'Plus récentes',
  protein: 'Plus de protéines',
  kcal: 'Moins de kcal',
  ratio: 'Meilleur ratio protéines/kcal',
}

export function isSortKey(v: string | null): v is SortKey {
  return v !== null && (SORT_KEYS as readonly string[]).includes(v)
}

function metric(r: Recipe, key: Exclude<SortKey, 'recent'>): number | null {
  const m = r.macros
  if (!m) return null
  if (key === 'protein') return m.protein
  if (key === 'kcal') return m.kcal
  return m.kcal > 0 ? m.protein / m.kcal : null
}

/** Compare deux valeurs, `null` toujours en dernier. `dir` : 1 croissant, -1 décroissant. */
function compareNullLast<T>(a: T | null, b: T | null, cmp: (x: T, y: T) => number, dir: 1 | -1): number {
  if (a === null && b === null) return 0
  if (a === null) return 1
  if (b === null) return -1
  return dir * cmp(a, b)
}

export function sortRecipes(recipes: Recipe[], key: SortKey): Recipe[] {
  const copy = [...recipes]
  if (key === 'recent') {
    return copy.sort((a, b) => compareNullLast(a.postedAt, b.postedAt, (x, y) => x.localeCompare(y), -1))
  }
  const dir = key === 'kcal' ? 1 : -1
  return copy.sort((a, b) => compareNullLast(metric(a, key), metric(b, key), (x, y) => x - y, dir))
}
