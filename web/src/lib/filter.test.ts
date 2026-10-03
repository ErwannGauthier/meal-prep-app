import { describe, expect, it } from 'vitest'
import { ingredients, recipes } from '../test/fixtures'
import {
  EMPTY_FILTERS, buildIngredientIndex, filterRecipes, groupIngredients, hasActiveFilters, listRegions,
} from './filter'

const ids = (rs: { id: string }[]) => rs.map((r) => r.id)

describe('filterRecipes', () => {
  it('sans filtre, renvoie tout dans l’ordre', () => {
    expect(ids(filterRecipes(recipes, EMPTY_FILTERS))).toEqual(['A1', 'B2', 'C3'])
  })

  it('cherche dans le titre sans tenir compte des accents ni de la casse', () => {
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, query: 'EPICE' }))).toEqual(['B2'])
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, query: 'riz' }))).toEqual(['C3'])
  })

  it('cherche chaque mot séparément, dans n’importe quel ordre', () => {
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, query: 'poulet coco' }))).toEqual(['A1'])
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, query: 'coco poulet' }))).toEqual(['A1'])
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, query: 'poulet nachos' }))).toEqual([])
  })

  it('exige tous les ingrédients sélectionnés', () => {
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, ingredientIds: ['poulet', 'riz'] }))).toEqual(['A1', 'C3'])
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, ingredientIds: ['poulet', 'paprika'] }))).toEqual([])
  })

  it('filtre par région et combine les critères', () => {
    expect(ids(filterRecipes(recipes, { ...EMPTY_FILTERS, region: 'Mexique' }))).toEqual(['B2'])
    expect(ids(filterRecipes(recipes, { query: 'poulet', ingredientIds: ['riz'], region: 'Chine' }))).toEqual([])
  })
})

describe('hasActiveFilters', () => {
  it('détecte un filtre actif', () => {
    expect(hasActiveFilters(EMPTY_FILTERS)).toBe(false)
    expect(hasActiveFilters({ ...EMPTY_FILTERS, query: '  ' })).toBe(false)
    expect(hasActiveFilters({ ...EMPTY_FILTERS, region: 'Chine' })).toBe(true)
  })
})

describe('index et groupes d’ingrédients', () => {
  it('indexe les recettes par ingrédient', () => {
    const index = buildIngredientIndex(recipes)
    expect([...index.get('poulet')!]).toEqual(['A1', 'C3'])
    expect(index.has('tofu')).toBe(false)
  })

  it('groupe par rayon dans l’ordre, trie par nom, omet les ingrédients et rayons vides', () => {
    const groups = groupIngredients(ingredients, buildIngredientIndex(recipes))
    expect(groups.map((g) => g.label)).toEqual([
      'Viandes & poissons', 'Fruits & légumes', 'Féculents', 'Épicerie', 'Épices & condiments',
    ])
    expect(groups[0].items).toEqual([
      { id: 'boeuf-hache', name: 'Bœuf haché', count: 1 },
      { id: 'poulet', name: 'Poulet', count: 2 },
    ])
  })
})

describe('listRegions', () => {
  it('renvoie les régions distinctes triées', () => {
    expect(listRegions(recipes)).toEqual(['Asie du Sud-Est', 'Chine', 'Mexique'])
  })
})
