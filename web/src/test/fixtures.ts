import type { Catalog } from '../lib/catalog'
import type { Ingredient, Recipe, RecipeIngredient } from '../types'

export const ingredients: Ingredient[] = [
  { id: 'poulet', name: 'Poulet', category: 'viandes-poissons' },
  { id: 'boeuf-hache', name: 'Bœuf haché', category: 'viandes-poissons' },
  { id: 'poivron', name: 'Poivron', category: 'fruits-legumes' },
  { id: 'riz', name: 'Riz', category: 'feculents' },
  { id: 'lait-de-coco', name: 'Lait de coco', category: 'epicerie' },
  { id: 'paprika', name: 'Paprika', category: 'epices-condiments' },
  { id: 'tofu', name: 'Tofu', category: 'autre' }, // utilisé par aucune recette
]

const ing = (ingredientId: string, raw: string, quantity: number | null = null,
  unit: string | null = null): RecipeIngredient => ({ ingredientId, quantity, unit, raw })

export function makeRecipe(overrides: Partial<Recipe> = {}): Recipe {
  return {
    id: 'X',
    title: 'Recette',
    url: 'https://www.instagram.com/reel/X/',
    postedAt: '2026-01-01',
    thumbnail: null,
    region: null,
    portions: 5,
    ingredients: [],
    steps: ['Cuire.'],
    macros: null,
    extractedAt: '2026-10-02T00:00:00Z',
    ...overrides,
  }
}

export const recipes: Recipe[] = [
  makeRecipe({
    id: 'A1',
    title: 'Poulet satay coco',
    url: 'https://www.instagram.com/reel/A1/',
    postedAt: '2026-05-14',
    thumbnail: 'thumbs/A1.webp',
    region: 'Asie du Sud-Est',
    portions: 5,
    ingredients: [
      ing('poulet', '1 kg de blanc de poulet', 1, 'kg'),
      ing('lait-de-coco', '400 ml de lait de coco', 400, 'ml'),
      ing('riz', '500 g de riz basmati', 500, 'g'),
    ],
    steps: ['Couper le poulet en dés.', 'Faire revenir avec la sauce satay.', 'Cuire le riz.'],
    macros: { kcal: 620, protein: 48, carbs: 55, fat: 22, source: 'estimated' },
  }),
  makeRecipe({
    id: 'B2',
    title: 'Bowl nachos épicé',
    url: 'https://www.instagram.com/reel/B2/',
    postedAt: '2026-06-01',
    region: 'Mexique',
    ingredients: [
      ing('boeuf-hache', '800 g de bœuf haché', 800, 'g'),
      ing('poivron', '3 poivrons', 3),
      ing('paprika', '1 c. à soupe de paprika', 1, 'c. à soupe'),
    ],
    macros: { kcal: 700, protein: 45, carbs: 60, fat: 30, source: 'announced' },
  }),
  makeRecipe({
    id: 'C3',
    title: 'Riz cantonais',
    url: 'https://www.instagram.com/reel/C3/',
    postedAt: null,
    region: 'Chine',
    portions: null,
    ingredients: [ing('riz', '600 g de riz', 600, 'g'), ing('poulet', '300 g de poulet', 300, 'g')],
    macros: null,
  }),
]

export function makeCatalog(rs: Recipe[] = recipes): Catalog {
  return { recipes: rs, ingredients, ingredientsById: new Map(ingredients.map((i) => [i.id, i])) }
}

export function fakeFetch(data: { recipes?: unknown; ingredients?: unknown; status?: number } = {}): typeof fetch {
  const { recipes: rs = recipes, ingredients: is = ingredients, status = 200 } = data
  return (async (input: RequestInfo | URL) => {
    const url = String(input)
    const body = url.endsWith('recipes.json') ? rs : is
    return new Response(JSON.stringify(body), { status })
  }) as unknown as typeof fetch
}
