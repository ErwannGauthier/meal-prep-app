import { HashRouter, Navigate, Route, Routes } from 'react-router'
import { ErrorBoundary } from './components/ErrorBoundary'
import { useCatalog } from './lib/catalog'
import { HomePage } from './pages/HomePage'
import { RecipePage } from './pages/RecipePage'

export function App({ fetchFn = fetch }: { fetchFn?: typeof fetch }) {
  const state = useCatalog(fetchFn)

  if (state.status === 'loading') return <p className="status">Chargement…</p>
  if (state.status === 'error') {
    return (
      <p className="status" role="alert">
        Impossible de charger les recettes ({state.message}).
      </p>
    )
  }
  return (
    // useTransitions={false} : le champ de recherche tire sa valeur de l'URL ; avec les
    // transitions de React, corriger une lettre au milieu renvoyait le curseur à la fin.
    <HashRouter useTransitions={false}>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<HomePage catalog={state.catalog} />} />
          <Route path="/recette/:id" element={<RecipePage catalog={state.catalog} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ErrorBoundary>
    </HashRouter>
  )
}
