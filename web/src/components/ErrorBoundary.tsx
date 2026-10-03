import { Component, type ReactNode } from 'react'

/** Dernier filet : une erreur d'affichage donne un message, jamais une page blanche. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="page">
        <p className="status" role="alert">
          Une erreur empêche d’afficher cette page. Recharge-la ; si le problème persiste, les données du site sont à vérifier.
        </p>
        <a className="link" href="#/" onClick={() => this.setState({ failed: false })}>
          Toutes les recettes
        </a>
      </main>
    )
  }
}
