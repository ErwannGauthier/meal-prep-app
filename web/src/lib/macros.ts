import type { Macros } from '../types'

export interface MacroSplit {
  protein: number
  carbs: number
  fat: number
}

/** Part des calories apportée par chaque macro (somme = 1), ou null s'il n'y a rien à répartir. */
export function macroSplit(m: Macros): MacroSplit | null {
  const protein = m.protein * 4
  const carbs = m.carbs * 4
  const fat = m.fat * 9
  const total = protein + carbs + fat
  if (total <= 0) return null
  return { protein: protein / total, carbs: carbs / total, fat: fat / total }
}
