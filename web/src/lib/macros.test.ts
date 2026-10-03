import { describe, expect, it } from 'vitest'
import { macroSplit } from './macros'

const m = (protein: number, carbs: number, fat: number) =>
  ({ kcal: 0, protein, carbs, fat, source: 'estimated' as const })

describe('macroSplit', () => {
  it('répartit les calories : 4 kcal/g pour protéines et glucides, 9 kcal/g pour les lipides', () => {
    const s = macroSplit(m(48, 55, 22))!   // 192 + 220 + 198 = 610 kcal
    expect(s.protein).toBeCloseTo(192 / 610)
    expect(s.carbs).toBeCloseTo(220 / 610)
    expect(s.fat).toBeCloseTo(198 / 610)
    expect(s.protein + s.carbs + s.fat).toBeCloseTo(1)
  })

  it('renvoie null quand il n’y a rien à répartir', () => {
    expect(macroSplit(m(0, 0, 0))).toBeNull()
  })
})
