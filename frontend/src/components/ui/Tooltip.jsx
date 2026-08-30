import { useState, useId } from 'react'

export function Tooltip({ label, children }) {
  const [open, setOpen] = useState(false)
  const id = useId()

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children({ 'aria-describedby': id })}
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-50 whitespace-nowrap
            rounded bg-surface border border-line px-2 py-1 text-xs text-primary shadow-elevated"
        >
          {label}
        </span>
      )}
    </span>
  )
}
