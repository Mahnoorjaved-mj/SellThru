/** Custom legend: small line swatches (dashed for forecast series), clicking toggles a series. */
export function ChartLegend({ series, hidden, onToggle }) {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-2">
      {series.map((s) => {
        const isHidden = hidden?.has(s.label)
        return (
          <button
            key={s.label}
            onClick={() => onToggle?.(s.label)}
            className={`flex items-center gap-1.5 text-[11px] font-medium transition-colors duration-120 ease-out ${
              isHidden ? 'text-tertiary' : 'text-secondary hover:text-primary'
            }`}
          >
            <svg width="10" height="2" className="flex-shrink-0">
              <line
                x1="0" y1="1" x2="10" y2="1"
                stroke={s.color}
                strokeWidth="2"
                strokeDasharray={s.dashed ? '3,2' : undefined}
                opacity={isHidden ? 0.35 : 1}
              />
            </svg>
            {s.label}
          </button>
        )
      })}
    </div>
  )
}
