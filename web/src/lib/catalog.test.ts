import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { fakeFetch, recipes } from '../test/fixtures'
import { dataUrl, loadCatalog, useCatalog } from './catalog'

describe('loadCatalog', () => {
  it('charge les deux fichiers et indexe les ingrédients', async () => {
    const spy = vi.fn(fakeFetch())
    const c = await loadCatalog(spy as unknown as typeof fetch)
    expect(c.recipes.map((r) => r.id)).toEqual(recipes.map((r) => r.id))
    expect(c.ingredientsById.get('riz')?.name).toBe('Riz')
    expect(spy.mock.calls.map(([url]) => String(url))).toEqual([dataUrl('recipes.json'), dataUrl('ingredients.json')])
    expect(dataUrl('recipes.json')).toMatch(/data\/recipes\.json$/)
  })

  it('échoue avec un message explicite si un fichier manque', async () => {
    await expect(loadCatalog(fakeFetch({ status: 404 }))).rejects.toThrow('recipes.json : HTTP 404')
  })
})

describe('loadCatalog avec un fichier de mauvaise forme', () => {
  it('refuse un recipes.json qui n’est pas une liste', async () => {
    await expect(loadCatalog(fakeFetch({ recipes: {} }))).rejects.toThrow('recipes.json : format inattendu')
    await expect(loadCatalog(fakeFetch({ recipes: null }))).rejects.toThrow('recipes.json : format inattendu')
  })

  it('refuse un ingredients.json qui n’est pas une liste', async () => {
    await expect(loadCatalog(fakeFetch({ ingredients: {} }))).rejects.toThrow('ingredients.json : format inattendu')
  })

  it('écarte les recettes incomplètes au lieu de faire tomber tout le site', async () => {
    const broken = [{ id: 'KO', title: 'Sans ingrédients' }, { id: 'KO2', title: null, ingredients: [], steps: [] }, recipes[0]]
    const c = await loadCatalog(fakeFetch({ recipes: broken }))
    expect(c.recipes.map((r) => r.id)).toEqual(['A1'])
  })
})

describe('useCatalog', () => {
  it('passe de loading à ready', async () => {
    const fetchFn = fakeFetch()
    const { result } = renderHook(() => useCatalog(fetchFn))
    expect(result.current.status).toBe('loading')
    await waitFor(() => expect(result.current.status).toBe('ready'))
  })

  it('expose l’erreur', async () => {
    const fetchFn = fakeFetch({ status: 500 })
    const { result } = renderHook(() => useCatalog(fetchFn))
    await waitFor(() => expect(result.current).toEqual({ status: 'error', message: 'recipes.json : HTTP 500' }))
  })
})
