import { useEffect, useRef } from 'react'

export function Dialog({ open, onClose, title, children, footer }) {
  const panelRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panelRef.current) return
      const focusable = panelRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    panelRef.current?.querySelector('button, input, select, textarea')?.focus()
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-overlay" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative bg-surface border border-line rounded-panel shadow-elevated w-full max-w-md"
      >
        {title && (
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold text-primary">{title}</h3>
          </div>
        )}
        <div className="p-4">{children}</div>
        {footer && <div className="border-t border-line px-4 py-3 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}
