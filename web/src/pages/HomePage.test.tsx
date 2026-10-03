import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { makeCatalog } from '../test/fixtures'
import { HomePage } from './HomePage'

function renderHome(path = '/', catalog = makeCatalog()) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<HomePage catalog={catalog} />} />
        <Route path="/recette/:id" element={<p>page recette</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

const titles = () => screen.queryAllByRole('heading', { level: 2 }).map((h) => h.textContent)

describe('HomePage', () => {
  it('affiche toutes les recettes, les plus récentes d’abord', () => {
    renderHome()
    expect(titles()).toEqual(['Bowl nachos épicé', 'Poulet satay coco', 'Riz cantonais'])
  })

  it('affiche les macros sur la carte seulement si elles existent', () => {
    renderHome()
    const card = screen.getByRole('link', { name: /Poulet satay coco/ })
    expect(within(card).getByText('48 g de protéines')).toBeInTheDocument()
    expect(within(card).getByText('620 kcal')).toBeInTheDocument()
    expect(within(card).getByRole('img', { name: /Répartition des calories/ })).toBeInTheDocument()
    const noMacros = screen.getByRole('link', { name: /Riz cantonais/ })
    expect(within(noMacros).queryByText(/kcal/)).toBeNull()
    expect(within(noMacros).queryByRole('img')).toBeNull()
  })

  it('recherche sans accents', async () => {
    renderHome()
    await userEvent.type(screen.getByLabelText('Rechercher une recette'), 'epice')
    expect(titles()).toEqual(['Bowl nachos épicé'])
  })

  it('reprend les ingrédients depuis l’URL et permet de les retirer', async () => {
    renderHome('/?ing=poulet,riz')
    expect(titles()).toEqual(['Poulet satay coco', 'Riz cantonais'])
    await userEvent.click(screen.getByRole('button', { name: 'Retirer Riz' }))
    expect(titles()).toEqual(['Poulet satay coco', 'Riz cantonais'])
    await userEvent.click(screen.getByRole('button', { name: 'Retirer Poulet' }))
    expect(titles()).toHaveLength(3)
  })

  it('sélectionne un ingrédient depuis le panneau groupé par rayon', async () => {
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: /^Ingrédients/ }))
    expect(screen.getByRole('group', { name: 'Épices & condiments' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Paprika (1)' }))
    expect(titles()).toEqual(['Bowl nachos épicé'])
  })

  it('filtre par région et trie par protéines', async () => {
    renderHome()
    await userEvent.selectOptions(screen.getByLabelText('Trier'), 'protein')
    expect(titles()).toEqual(['Poulet satay coco', 'Bowl nachos épicé', 'Riz cantonais'])
    await userEvent.selectOptions(screen.getByLabelText('Région'), 'Mexique')
    expect(titles()).toEqual(['Bowl nachos épicé'])
  })

  it('état vide avec réinitialisation', async () => {
    renderHome('/?q=lasagnes')
    expect(screen.getByText('Aucune recette ne correspond.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }))
    expect(titles()).toHaveLength(3)
  })

  it('catalogue vide', () => {
    renderHome('/', makeCatalog([]))
    expect(screen.getByText('Aucune recette pour l’instant.')).toBeInTheDocument()
  })

  it('une carte mène à la page recette', async () => {
    renderHome()
    await userEvent.click(screen.getByRole('link', { name: /Poulet satay coco/ }))
    expect(screen.getByText('page recette')).toBeInTheDocument()
  })
})

describe('HomePage : filtre par ingrédients avec beaucoup d’ingrédients', () => {
  it('le panneau a sa propre recherche, sans accents', async () => {
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: /^Ingrédients/ }))
    await userEvent.type(screen.getByLabelText('Chercher un ingrédient'), 'boeuf')
    expect(screen.getByRole('button', { name: 'Bœuf haché (1)' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Poulet (2)' })).toBeNull()
    expect(screen.queryByRole('group', { name: 'Féculents' })).toBeNull()
  })

  it('aucun ingrédient ne correspond : le panneau le dit', async () => {
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: /^Ingrédients/ }))
    await userEvent.type(screen.getByLabelText('Chercher un ingrédient'), 'zzz')
    expect(screen.getByText('Aucun ingrédient ne correspond.')).toBeInTheDocument()
  })

  it('affiche le nombre de recettes trouvées dès qu’un filtre est actif', async () => {
    renderHome()
    expect(screen.queryByRole('status')).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: /^Ingrédients/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Poulet (2)' }))
    expect(screen.getByRole('status')).toHaveTextContent('2 recettes trouvées')
    await userEvent.click(screen.getByRole('button', { name: 'Paprika (1)' }))
    expect(screen.getByRole('status')).toHaveTextContent('Aucune recette trouvée')
  })

  it('la photo d’une carte vient du dossier data/ du site', () => {
    const { container } = renderHome()
    expect(container.querySelector('img.card__img')?.getAttribute('src')).toMatch(/data\/thumbs\/A1\.webp$/)
  })
})
