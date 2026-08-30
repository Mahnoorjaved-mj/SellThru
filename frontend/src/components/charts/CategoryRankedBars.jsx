import { useChartTheme } from '../../lib/chartTheme'
import { formatCurrency, formatPercent } from '../../lib/format'

/** Ranked horizontal bars for category mix — replaces the doughnut per Section 3.7. */
export function CategoryRankedBars({ categories }) {
  const tokens = useChartTheme()

  if (!categories || categories.length === 0) {
    return <p className="text-sm text-secondary">No categories found</p>
  }

  return (
    <div className="space-y-3 w-full">
      {categories.map((c, i) => {
        const color = tokens.series[i % tokens.series.length]
        return (
          <div key={c.name}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="font-medium text-primary">{c.name}</span>
              <span className="flex items-center gap-2 font-mono tabular-nums">
                <span className="text-secondary">{formatCurrency(c.value, { compact: true })}</span>
                <span className="text-primary font-semibold w-10 text-right">{c.share_pct}%</span>
                {c.delta_pct !== null && c.delta_pct !== undefined && (
                  <span className={`w-14 text-right ${c.delta_pct >= 0 ? 'text-up' : 'text-down'}`}>
                    {formatPercent(c.delta_pct)}
                  </span>
                )}
              </span>
            </div>
            <div className="h-1.5 w-full rounded bg-surface-hover overflow-hidden">
              <div
                className="h-full rounded"
                style={{ width: `${Math.max(2, c.share_pct)}%`, backgroundColor: color }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
