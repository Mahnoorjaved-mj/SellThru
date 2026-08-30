export function Tabs({ items, value, onChange }) {
  return (
    <div role="tablist" className="flex items-center gap-1 border-b border-line">
      {items.map((item) => {
        const active = item.value === value
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-120 ease-out
              ${active ? 'border-accent text-primary' : 'border-transparent text-secondary hover:text-primary'}`}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
