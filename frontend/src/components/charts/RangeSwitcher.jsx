const PRESETS = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: '1Y', days: 365 },
]

/** Pill range switcher. Controlled by `days` (number), calls onChange(days). */
export function RangeSwitcher({ days, onChange }) {
  return (
    <div className="inline-flex items-center rounded border border-line bg-bg p-0.5">
      {PRESETS.map((p) => {
        const active = p.days === days
        return (
          <button
            key={p.days}
            onClick={() => onChange(p.days)}
            className={`h-6 px-2 rounded-sm text-[11px] font-semibold transition-colors duration-120 ease-out ${
              active ? 'bg-accent-soft text-accent' : 'text-tertiary hover:text-primary'
            }`}
          >
            {p.label}
          </button>
        )
      })}
    </div>
  )
}
