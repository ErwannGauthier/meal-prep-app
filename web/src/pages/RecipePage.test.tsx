import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { makeCatalog } from '../test/fixtures'
import { RecipePage } from './RecipePage'

function ListProbe() {
  const { search } = useLocation()
  return <p>liste {search}</p>
}

function renderRecipe(entries: string[]) {
  return render(
    <MemoryRouter initialEntries={entries} initialIndex={entries.length - 1}>
      <Routes>
        <Route path="/" element={<ListProbe />} />
        <Route path="/recette/:id" element={<RecipePage catalog={makeCatalog()} />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RecipePage', () => {
  it('affiche titre, région, macros estimées, portions, ingrédients par rayon, étapes et lien', () => {
    renderRecipe(['/recette/A1'])
    expect(screen.getByRole('heading', { level: 1, name: 'Poulet satay coco' })).toBeInTheDocument()
    expect(screen.getByText('Asie du Sud-Est')).toBeInTheDocument()
    expect(screen.getByText('620')).toBeInTheDocument()
    expect(screen.getByText('estimé')).toBeInTheDocument()
    expect(screen.getByText('5 portions')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Répartition des calories/ })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'Viandes & poissons', 'Féculents', 'Épicerie',
    ])
    const steps = within(screen.getByRole('list', { name: 'Étapes' })).getAllByRole('listitem')
    expect(steps.map((s) => s.textContent)).toEqual([
      'Couper le poulet en dés.', 'Faire revenir avec la sauce satay.', 'Cuire le riz.',
    ])
    expect(screen.getByRole('link', { name: /Voir le reel/ })).toHaveAttribute('href', 'https://www.instagram.com/reel/A1/')
    expect(screen.getByRole('button', { name: 'Copier la liste' })).toBeInTheDocument()
  })

  it('macros annoncées : pas de badge « estimé »', () => {
    renderRecipe(['/recette/B2'])
    expect(screen.getByText('700')).toBeInTheDocument()
    expect(screen.queryByText('estimé')).toBeNull()
  })

  it('sans macros : message dédié', () => {
    renderRecipe(['/recette/C3'])
    expect(screen.getByText('Macros non disponibles')).toBeInTheDocument()
  })

  it('id inconnu : recette introuvable', () => {
    renderRecipe(['/recette/ZZZ'])
    expect(screen.getByText('Recette introuvable.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Toutes les recettes/ })).toHaveAttribute('href', '/')
  })

  it('le retour revient à la liste filtrée', async () => {
    renderRecipe(['/?ing=poulet', '/recette/A1'])
    await userEvent.click(screen.getByRole('button', { name: '← Recettes' }))
    expect(screen.getByText('liste ?ing=poulet')).toBeInTheDocument()
  })
})

describe('RecipePage : ce qui part vers Notes et ce qui s’affiche', () => {
  it('« Copier la liste » copie la liste de courses complète de la recette', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    renderRecipe(['/recette/A1'])
    fireEvent.click(screen.getByRole('button', { name: 'Copier la liste' }))
    await screen.findByText('Copié !')
    expect(writeText).toHaveBeenCalledWith(
      'Poulet satay coco — courses\n\nViandes & poissons\n1 kg de blanc de poulet\n\nFéculents\n500 g de riz basmati\n\nÉpicerie\n400 ml de lait de coco',
    )
    delete (navigator as unknown as Record<string, unknown>).clipboard
  })

  it('la photo vient du dossier data/ du site', () => {
    const { container } = renderRecipe(['/recette/A1'])
    expect(container.querySelector('img.recipe__img')?.getAttribute('src')).toMatch(/data\/thumbs\/A1\.webp$/)
  })
})
