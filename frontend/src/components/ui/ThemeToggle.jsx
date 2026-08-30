import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '../../app/ThemeProvider'

const OPTIONS = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'dark', icon: Moon, label: 'Dark' },
  { value: 'system', icon: Monitor, label: 'System' },
]

export function ThemeToggle() {
  const { mode, setMode } = useTheme()

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="inline-flex items-center rounded border border-line bg-bg p-0.5"
    >
      {OPTIONS.map((opt) => {
        const active = mode === opt.value
        const Icon = opt.icon
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            title={opt.label}
            onClick={() => setMode(opt.value)}
            className={`flex items-center justify-center h-6 w-6 rounded-sm transition-colors duration-120 ease-out
              ${active ? 'bg-accent-soft text-accent' : 'text-tertiary hover:text-primary'}`}
          >
            <Icon size={14} />
          </button>
        )
      })}
    </div>
  )
}
