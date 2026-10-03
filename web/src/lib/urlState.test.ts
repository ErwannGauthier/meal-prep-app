import { describe, expect, it } from 'vitest'
import { EMPTY_FILTERS } from './filter'
import { parseListState, toSearchParams } from './urlState'

describe('urlState', () => {
  it('URL vide → valeurs par défaut', () => {
    expect(parseListState(new URLSearchParams(''))).toEqual({ filters: EMPTY_FILTERS, sort: 'recent' })
  })

  it('les valeurs par défaut ne polluent pas l’URL', () => {
    expect(toSearchParams({ filters: EMPTY_FILTERS, sort: 'recent' }).toString()).toBe('')
  })

  it('aller-retour complet', () => {
    const state = { filters: { query: 'poulet coco', ingredientIds: ['poulet', 'riz'], region: 'Mexique' }, sort: 'ratio' as const }
    expect(parseListState(toSearchParams(state))).toEqual(state)
  })

  it('paramètres invalides → valeurs par défaut', () => {
    const s = parseListState(new URLSearchParams('sort=xyz&ing=,,poulet,&region='))
    expect(s.sort).toBe('recent')
    expect(s.filters.ingredientIds).toEqual(['poulet'])
    expect(s.filters.region).toBeNull()
  })
})
