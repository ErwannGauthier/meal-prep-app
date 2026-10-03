import { useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { FiltersBar } from '../components/FiltersBar'
import { RecipeGrid } from '../components/RecipeGrid'
import type { Catalog } from '../lib/catalog'
import { EMPTY_FILTERS, buildIngredientIndex, filterRecipes, groupIngredients, listRegions } from '../lib/filter'
import { sortRecipes } from '../lib/sort'
import { parseListState, toSearchParams, type ListState } from '../lib/urlState'

export function HomePage({ catalog }: { catalog: Catalog }) {
  const [params, setParams] = useSearchParams()
  const state = useMemo(() => parseListState(params), [params])
  const groups = useMemo(
    () => groupIngredients(catalog.ingredients, buildIngredientIndex(catalog.recipes)),
    [catalog],
  )
  const regions = useMemo(() => listRegions(catalog.recipes), [catalog])
  const names = useMemo(() => new Map(catalog.ingredients.map((i) => [i.id, i.name])), [catalog])
  const visible = useMemo(
    () => sortRecipes(filterRecipes(catalog.recipes, state.filters), state.sort),
    [catalog, state],
  )
  const update = (next: ListState) => setParams(toSearchParams(next), { replace: true })

  return (
    <main className="page">
      <header className="masthead">
        <h1 className="masthead__title">Meal preps</h1>
        <p className="masthead__sub">{catalog.recipes.length} recettes de @bourr_</p>
        <ul className="legend" aria-label="Couleurs de la barre de calories">
          <li className="legend__item legend__item--protein">protéines</li>
          <li className="legend__item legend__item--carbs">glucides</li>
          <li className="legend__item legend__item--fat">lipides</li>
        </ul>
      </header>
      <FiltersBar state={state} regions={regions} groups={groups} ingredientNames={names} resultCount={visible.length} onChange={update} />
      {catalog.recipes.length === 0 ? (
        <p className="empty">Aucune recette pour l’instant.</p>
      ) : visible.length === 0 ? (
        <div className="empty">
          <p>Aucune recette ne correspond.</p>
          <button type="button" className="btn" onClick={() => update({ filters: EMPTY_FILTERS, sort: state.sort })}>
            Réinitialiser les filtres
          </button>
        </div>
      ) : (
        <RecipeGrid recipes={visible} />
      )}
    </main>
  )
}
