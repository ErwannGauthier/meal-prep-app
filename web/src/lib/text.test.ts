import { describe, expect, it } from 'vitest'
import { normalizeText } from './text'

describe('normalizeText', () => {
  it('retire accents, ligatures, casse et espaces superflus', () => {
    expect(normalizeText('  Bœuf   Épicé ')).toBe('boeuf epice')
    expect(normalizeText('Crème brûlée')).toBe('creme brulee')
  })

  it('unifie les apostrophes : le clavier iOS tape une apostrophe courbe', () => {
    expect(normalizeText('Curry d’agneau à l’ail')).toBe(normalizeText("Curry d'agneau à l'ail"))
  })
})
