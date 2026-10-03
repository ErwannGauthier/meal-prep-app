import { useState } from 'react'
import { EMPTY_FILTERS, hasActiveFilters, type Filters, type IngredientGroup } from '../lib/filter'
import { normalizeText } from '../lib/text'
import { SORT_KEYS, SORT_LABELS, type SortKey } from '../lib/sort'
import type { ListState } from '../lib/urlState'

interface FiltersBarProps {
  state: ListState
  regions: string[]
  groups: IngredientGroup[]
  ingredientNames: Map<string, string>
  resultCount: number
  onChange: (next: ListState) => void
}

function countLabel(n: number): string {
  if (n === 0) return 'Aucune recette trouvée'
  return n === 1 ? '1 recette trouvée' : `${n} recettes trouvées`
}

export function FiltersBar({ state, regions, groups, ingredientNames, resultCount, onChange }: FiltersBarProps) {
  const [open, setOpen] = useState(false)
  const [needle, setNeedle] = useState('')
  const { filters, sort } = state
  const setFilters = (patch: Partial<Filters>) => onChange({ sort, filters: { ...filters, ...patch } })
  const toggle = (id: string) =>
    setFilters({
      ingredientIds: filters.ingredientIds.includes(id)
        ? filters.ingredientIds.filter((x) => x !== id)
        : [...filters.ingredientIds, id],
    })
  const nameOf = (id: string) => ingredientNames.get(id) ?? id
  const count = filters.ingredientIds.length
  const wanted = normalizeText(needle)
  const shownGroups = groups
    .map((g) => ({ ...g, items: g.items.filter((i) => normalizeText(i.name).includes(wanted)) }))
    .filter((g) => g.items.length > 0)

  return (
    <section className="filters" aria-label="Filtres">
      <input
        type="search"
        className="filters__search"
        placeholder="Rechercher une recette…"
        aria-label="Rechercher une recette"
        value={filters.query}
        onChange={(e) => setFilters({ query: e.target.value })}
      />
      <div className="filters__row">
        <select aria-label="Région" value={filters.region ?? ''} onChange={(e) => setFilters({ region: e.target.value || null })}>
          <option value="">Toutes les régions</option>
          {regions.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select aria-label="Trier" value={sort} onChange={(e) => onChange({ filters, sort: e.target.value as SortKey })}>
          {SORT_KEYS.map((k) => (
            <option key={k} value={k}>{SORT_LABELS[k]}</option>
          ))}
        </select>
      </div>
      <div className="filters__chips">
        <button type="button" className="chip chip--toggle" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          Ingrédients{count > 0 ? ` (${count})` : ''} {open ? '▴' : '▾'}
        </button>
        {filters.ingredientIds.map((id) => (
          <button key={id} type="button" className="chip chip--active" aria-label={`Retirer ${nameOf(id)}`} onClick={() => toggle(id)}>
            {nameOf(id)} ×
          </button>
        ))}
        {hasActiveFilters(filters) && (
          <button type="button" className="link" onClick={() => onChange({ filters: EMPTY_FILTERS, sort })}>
            Effacer les filtres
          </button>
        )}
      </div>
      {hasActiveFilters(filters) && (
        <p className="filters__count" role="status">{countLabel(resultCount)}</p>
      )}
      {open && (
        <div className="filters__panel">
          <input
            type="search"
            className="filters__search"
            placeholder="Chercher un ingrédient…"
            aria-label="Chercher un ingrédient"
            value={needle}
            onChange={(e) => setNeedle(e.target.value)}
          />
          {shownGroups.length === 0 && <p className="filters__none">Aucun ingrédient ne correspond.</p>}
          {shownGroups.map((g) => (
            <fieldset key={g.category} className="filters__group">
              <legend>{g.label}</legend>
              {g.items.map((i) => (
                <button
                  key={i.id}
                  type="button"
                  className="chip"
                  aria-pressed={filters.ingredientIds.includes(i.id)}
                  onClick={() => toggle(i.id)}
                >
                  {i.name} <span className="chip__count">({i.count})</span>
                </button>
              ))}
            </fieldset>
          ))}
        </div>
      )}
    </section>
  )
}
