import type { Recipe } from '../types'
import { RecipeCard } from './RecipeCard'

export function RecipeGrid({ recipes }: { recipes: Recipe[] }) {
  return (
    <ul className="grid">
      {recipes.map((r) => (
        <li key={r.id}>
          <RecipeCard recipe={r} />
        </li>
      ))}
    </ul>
  )
}
