import { describe, expect, it } from 'vitest'
import { recipes } from './test/fixtures'
import { CATEGORIES } from './types'

describe('CATEGORIES', () => {
  it('liste les 8 rayons dans l’ordre de la spec', () => {
    expect(CATEGORIES.map((c) => c.id)).toEqual([
      'viandes-poissons', 'fruits-legumes', 'feculents', 'produits-laitiers-oeufs',
      'epicerie', 'epices-condiments', 'surgeles', 'autre',
    ])
    expect(CATEGORIES[3].label).toBe('Produits laitiers & œufs')
  })

  it('les fixtures sont cohérentes', () => {
    expect(recipes.map((r) => r.id)).toEqual(['A1', 'B2', 'C3'])
  })
})
