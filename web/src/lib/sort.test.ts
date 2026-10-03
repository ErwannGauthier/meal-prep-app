import { describe, expect, it } from 'vitest'
import { recipes } from '../test/fixtures'
import { SORT_LABELS, isSortKey, sortRecipes } from './sort'

const ids = (rs: { id: string }[]) => rs.map((r) => r.id)

describe('sortRecipes', () => {
  it('récentes : date décroissante, dates inconnues en dernier', () => {
    expect(ids(sortRecipes(recipes, 'recent'))).toEqual(['B2', 'A1', 'C3'])
  })

  it('protéines décroissantes, sans macros en dernier', () => {
    expect(ids(sortRecipes(recipes, 'protein'))).toEqual(['A1', 'B2', 'C3'])
  })

  it('kcal croissantes, sans macros en dernier', () => {
    expect(ids(sortRecipes(recipes, 'kcal'))).toEqual(['A1', 'B2', 'C3'])
    expect(ids(sortRecipes([recipes[2], recipes[1]], 'kcal'))).toEqual(['B2', 'C3'])
  })

  it('ratio protéines/kcal décroissant', () => {
    expect(ids(sortRecipes([recipes[1], recipes[2], recipes[0]], 'ratio'))).toEqual(['A1', 'B2', 'C3'])
  })

  it('ne modifie pas le tableau reçu', () => {
    const input = [...recipes]
    sortRecipes(input, 'recent')
    expect(ids(input)).toEqual(['A1', 'B2', 'C3'])
  })
})

describe('isSortKey', () => {
  it('valide les clés connues', () => {
    expect(isSortKey('ratio')).toBe(true)
    expect(isSortKey('xyz')).toBe(false)
    expect(isSortKey(null)).toBe(false)
    expect(SORT_LABELS.recent).toBe('Plus récentes')
  })
})
