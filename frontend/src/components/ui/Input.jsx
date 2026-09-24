export function Input({ className = '', numeric = false, ...rest }) {
  return (
    <input
      className={`w-full h-9 rounded-control bg-bg border border-line-strong px-3 text-sm text-primary
        placeholder:text-tertiary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all duration-120 ease-out
        ${numeric ? 'font-mono tabular-nums' : ''} ${className}`}
      {...rest}
    />
  )
}

export function Label({ className = '', children, ...rest }) {
  return (
    <label className={`block text-xs font-semibold text-secondary mb-1.5 ${className}`} {...rest}>
      {children}
    </label>
  )
}
