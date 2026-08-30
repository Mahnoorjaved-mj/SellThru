import { ChevronDown } from 'lucide-react'

export function Select({ className = '', children, ...rest }) {
  return (
    <div className="relative">
      <select
        className={`w-full h-8 appearance-none rounded bg-bg border border-line-strong pl-3 pr-8 text-sm
          text-primary outline-none focus:border-accent transition-colors duration-120 ease-out ${className}`}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-tertiary"
      />
    </div>
  )
}
