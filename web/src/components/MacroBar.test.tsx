import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MacroBar } from './MacroBar'

describe('MacroBar', () => {
  it('décrit la répartition pour les lecteurs d’écran et dimensionne les trois segments', () => {
    render(<MacroBar macros={{ kcal: 620, protein: 48, carbs: 55, fat: 22, source: 'estimated' }} />)
    const bar = screen.getByRole('img', {
      name: 'Répartition des calories : 31 % protéines, 36 % glucides, 32 % lipides',
    })
    const widths = [...bar.children].map((c) => (c as HTMLElement).style.flexGrow)
    expect(widths.map(Number).map((w) => Math.round(w * 100))).toEqual([31, 36, 32])
  })

  it('n’affiche rien sans valeurs', () => {
    const { container } = render(<MacroBar macros={{ kcal: 0, protein: 0, carbs: 0, fat: 0, source: 'estimated' }} />)
    expect(container).toBeEmptyDOMElement()
  })
})
