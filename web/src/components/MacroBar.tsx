import { macroSplit } from '../lib/macros'
import type { Macros } from '../types'

const pct = (share: number) => Math.round(share * 100)

export function MacroBar({ macros }: { macros: Macros }) {
  const split = macroSplit(macros)
  if (!split) return null
  const label =
    `Répartition des calories : ${pct(split.protein)} % protéines, ` +
    `${pct(split.carbs)} % glucides, ${pct(split.fat)} % lipides`
  return (
    <div className="macrobar" role="img" aria-label={label}>
      <span className="macrobar__seg macrobar__seg--protein" style={{ flexGrow: split.protein }} />
      <span className="macrobar__seg macrobar__seg--carbs" style={{ flexGrow: split.carbs }} />
      <span className="macrobar__seg macrobar__seg--fat" style={{ flexGrow: split.fat }} />
    </div>
  )
}
