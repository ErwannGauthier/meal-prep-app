import type { Filters } from './filter'
import { isSortKey, type SortKey } from './sort'

export interface ListState {
  filters: Filters
  sort: SortKey
}

export function parseListState(params: URLSearchParams): ListState {
  const sort = params.get('sort')
  return {
    filters: {
      query: params.get('q') ?? '',
      ingredientIds: (params.get('ing') ?? '').split(',').filter(Boolean),
      region: params.get('region') || null,
    },
    sort: isSortKey(sort) ? sort : 'recent',
  }
}

export function toSearchParams({ filters, sort }: ListState): URLSearchParams {
  const p = new URLSearchParams()
  if (filters.query) p.set('q', filters.query)
  if (filters.ingredientIds.length) p.set('ing', filters.ingredientIds.join(','))
  if (filters.region) p.set('region', filters.region)
  if (sort !== 'recent') p.set('sort', sort)
  return p
}
