import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { fakeFetch, recipes } from './test/fixtures'

describe('App', () => {
  it('charge puis affiche les recettes', async () => {
    render(<App fetchFn={fakeFetch()} />)
    expect(screen.getByText('Chargement…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Poulet satay coco' })).toBeInTheDocument()
  })

  it('affiche une erreur lisible si les données ne chargent pas', async () => {
    render(<App fetchFn={fakeFetch({ status: 404 })} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de charger les recettes (recipes.json : HTTP 404)')
  })
})

describe('App face à une erreur d’affichage', () => {
  it('montre un message au lieu d’une page blanche', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const poisoned = [{ ...recipes[0], ingredients: [null] }]   // passe le contrôle de forme, casse à l'affichage
    render(<App fetchFn={fakeFetch({ recipes: poisoned })} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Une erreur empêche d’afficher cette page')
    spy.mockRestore()
  })
})

describe('recherche', () => {
  it('corriger une faute au milieu du texte ne déplace pas le curseur à la fin', async () => {
    window.location.hash = ''
    render(<App fetchFn={fakeFetch()} />)
    const input = (await screen.findByLabelText('Rechercher une recette')) as HTMLInputElement
    await userEvent.type(input, 'poulet')
    await userEvent.type(input, 'XY', { initialSelectionStart: 2, initialSelectionEnd: 2 })
    expect(input.value).toBe('poXYulet')
  })
})
