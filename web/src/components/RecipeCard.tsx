import { Link } from 'react-router'
import { dataUrl } from '../lib/catalog'
import type { Recipe } from '../types'
import { MacroBar } from './MacroBar'

export function RecipeCard({ recipe }: { recipe: Recipe }) {
  return (
    <Link to={`/recette/${recipe.id}`} className="card">
      {recipe.thumbnail ? (
        <img className="card__img" src={dataUrl(recipe.thumbnail)} alt="" loading="lazy" />
      ) : (
        <div className="card__img card__img--empty" aria-hidden="true" />
      )}
      {recipe.macros && <MacroBar macros={recipe.macros} />}
      <div className="card__body">
        <h2 className="card__title">{recipe.title}</h2>
        {recipe.region && <p className="card__region">{recipe.region}</p>}
        {recipe.macros && (
          <p className="card__macros">
            <span className="card__protein">{`${recipe.macros.protein} g de protéines`}</span>
            <span className="card__kcal">{`${recipe.macros.kcal} kcal`}</span>
          </p>
        )}
      </div>
    </Link>
  )
}
