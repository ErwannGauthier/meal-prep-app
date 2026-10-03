import { describe, expect, it } from 'vitest'
import { ingredients, makeRecipe, recipes } from '../test/fixtures'
import { formatShoppingList, groupRecipeIngredients } from './shoppingList'

const byId = new Map(ingredients.map((i) => [i.id, i]))

describe('formatShoppingList', () => {
  it('produit le texte exact, rayons dans l’ordre, rayons vides omis', () => {
    expect(formatShoppingList(recipes[0], byId)).toBe(
      [
        'Poulet satay coco — courses',
        '',
        'Viandes & poissons',
        '1 kg de blanc de poulet',
        '',
        'Féculents',
        '500 g de riz basmati',
        '',
        'Épicerie',
        '400 ml de lait de coco',
      ].join('\n'),
    )
  })

  it('range un ingrédient absent du référentiel dans « Autre »', () => {
    const r = makeRecipe({
      title: 'Mystère',
      ingredients: [
        { ingredientId: 'inconnu', quantity: null, unit: null, raw: '1 pincée de mystère' },
        { ingredientId: 'riz', quantity: 200, unit: 'g', raw: '200 g de riz' },
      ],
    })
    expect(formatShoppingList(r, byId)).toBe(
      'Mystère — courses\n\nFéculents\n200 g de riz\n\nAutre\n1 pincée de mystère',
    )
    expect(groupRecipeIngredients(r, byId).map((s) => s.category)).toEqual(['feculents', 'autre'])
  })
})
