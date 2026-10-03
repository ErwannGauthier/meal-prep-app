export type Category =
  | 'viandes-poissons'
  | 'fruits-legumes'
  | 'feculents'
  | 'produits-laitiers-oeufs'
  | 'epicerie'
  | 'epices-condiments'
  | 'surgeles'
  | 'autre'

export const CATEGORIES: readonly { id: Category; label: string }[] = [
  { id: 'viandes-poissons', label: 'Viandes & poissons' },
  { id: 'fruits-legumes', label: 'Fruits & légumes' },
  { id: 'feculents', label: 'Féculents' },
  { id: 'produits-laitiers-oeufs', label: 'Produits laitiers & œufs' },
  { id: 'epicerie', label: 'Épicerie' },
  { id: 'epices-condiments', label: 'Épices & condiments' },
  { id: 'surgeles', label: 'Surgelés' },
  { id: 'autre', label: 'Autre' },
]

export interface Ingredient {
  id: string
  name: string
  category: Category
}

export interface RecipeIngredient {
  ingredientId: string
  quantity: number | null
  unit: string | null
  raw: string
}

export interface Macros {
  kcal: number
  protein: number
  carbs: number
  fat: number
  source: 'announced' | 'estimated'
}

export interface Recipe {
  id: string
  title: string
  url: string
  postedAt: string | null
  thumbnail: string | null
  region: string | null
  portions: number | null
  ingredients: RecipeIngredient[]
  steps: string[]
  macros: Macros | null
  extractedAt: string
}
