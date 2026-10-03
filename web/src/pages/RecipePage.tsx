import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { MacroBar } from '../components/MacroBar'
import { ShareButton } from '../components/ShareButton'
import { dataUrl, type Catalog } from '../lib/catalog'
import { formatShoppingList, groupRecipeIngredients } from '../lib/shoppingList'

export function RecipePage({ catalog }: { catalog: Catalog }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const recipe = catalog.recipes.find((r) => r.id === id)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [id])

  // Retour navigateur si on vient de la liste (filtres conservés), sinon accueil.
  const back = () => (location.key !== 'default' ? navigate(-1) : navigate('/'))

  if (!recipe) {
    return (
      <main className="page">
        <p className="empty">Recette introuvable.</p>
        <Link to="/" className="link">← Toutes les recettes</Link>
      </main>
    )
  }

  const sections = groupRecipeIngredients(recipe, catalog.ingredientsById)
  const m = recipe.macros

  return (
    <main className="page recipe">
      <button type="button" className="link recipe__back" onClick={back}>← Recettes</button>
      {recipe.thumbnail && <img className="recipe__img" src={dataUrl(recipe.thumbnail)} alt="" />}
      <h1 className="recipe__title">{recipe.title}</h1>
      <p className="recipe__meta">
        {recipe.region && <span>{recipe.region}</span>}
        {recipe.portions && <span>{recipe.portions} portions</span>}
      </p>

      <section className="macros" aria-label="Macros par portion">
        {m ? (
          <>
            <div className="macros__head">
              <h2 className="macros__title">Valeurs par portion</h2>
              {m.source === 'estimated' && <span className="badge">estimé</span>}
            </div>
            <dl className="macros__grid">
              <div className="macros__row macros__row--kcal"><dt>Calories (kcal)</dt><dd>{m.kcal}</dd></div>
              <div className="macros__row macros__row--protein"><dt>Protéines</dt><dd>{m.protein}<small> g</small></dd></div>
              <div className="macros__row macros__row--carbs"><dt>Glucides</dt><dd>{m.carbs}<small> g</small></dd></div>
              <div className="macros__row macros__row--fat"><dt>Lipides</dt><dd>{m.fat}<small> g</small></dd></div>
            </dl>
            <MacroBar macros={m} />
          </>
        ) : (
          <p className="macros__none">Macros non disponibles</p>
        )}
      </section>

      <a className="btn recipe__reel" href={recipe.url} target="_blank" rel="noopener noreferrer">
        Voir le reel sur Instagram
      </a>

      <section className="recipe__section">
        <h2>Ingrédients</h2>
        {sections.map((s) => (
          <div key={s.category} className="aisle">
            <h3>{s.label}</h3>
            <ul>
              {s.items.map((i, idx) => (
                <li key={`${i.ingredientId}-${idx}`}>{i.raw}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="recipe__section">
        <h2>Étapes</h2>
        <ol className="steps" aria-label="Étapes">
          {recipe.steps.map((s, idx) => (
            <li key={idx}>{s}</li>
          ))}
        </ol>
      </section>

      <ShareButton title={`${recipe.title} — courses`} text={formatShoppingList(recipe, catalog.ingredientsById)} />
    </main>
  )
}
