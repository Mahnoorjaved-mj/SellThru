import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'

const ICONS = { success: CheckCircle, error: AlertCircle, warn: AlertTriangle, info: Info }
const COLOR_CLASS = {
  success: 'text-up',
  error: 'text-down',
  warn: 'text-warn',
  info: 'text-accent',
}

/** Flat bordered toast stack, top-right. Only surface here allowed a shadow. */
export function ToastViewport({ toasts, onDismiss }) {
  return (
    <div
      className="fixed top-4 right-4 z-[100] flex flex-col gap-2"
      role="region"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((t) => {
        const Icon = ICONS[t.type] || Info
        return (
          <div
            key={t.id}
            className="ss-card flex items-center gap-3 px-4 py-3 shadow-elevated min-w-[280px] max-w-sm bg-surface"
            style={{ animation: 'ss-toast-in 0.12s ease-out' }}
          >
            <Icon size={16} className={`${COLOR_CLASS[t.type] || 'text-accent'} flex-shrink-0`} />
            <span className="text-body text-primary flex-1 font-medium">{t.message}</span>
            <button
              onClick={() => onDismiss(t.id)}
              className="text-tertiary hover:text-primary transition-colors duration-120 ease-out"
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
