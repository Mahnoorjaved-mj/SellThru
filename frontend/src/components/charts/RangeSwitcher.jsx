const PRESETS = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: '1Y', days: 365 },
]

/** Segmented control range switcher. Controlled by `days` (number), calls onChange(days). */
export function RangeSwitcher({ days, onChange }) {
  return (
    <div className="inline-flex items-center rounded-xl border border-line/80 bg-app p-1 shadow-xs">
      {PRESETS.map((p) => {
        const active = p.days === days
        return (
          <button
            key={p.days}
            onClick={() => onChange(p.days)}
            className={`h-6.5 px-3 rounded-lg text-xs font-semibold transition-all duration-150 ease-out ${
              active
                ? 'bg-surface text-deep-teal shadow-sm ring-1 ring-black/5 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-700/40'
                : 'text-secondary hover:text-primary hover:bg-surface/50'
            }`}
          >
            {p.label}
          </button>
        )
      })}
    </div>
  )
}
