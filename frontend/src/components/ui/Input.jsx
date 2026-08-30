export function Input({ className = '', numeric = false, ...rest }) {
  return (
    <input
      className={`w-full h-8 rounded bg-bg border border-line-strong px-3 text-sm text-primary
        placeholder:text-tertiary outline-none focus:border-accent transition-colors duration-120 ease-out
        ${numeric ? 'font-mono tabular-nums' : ''} ${className}`}
      {...rest}
    />
  )
}

export function Label({ className = '', children, ...rest }) {
  return (
    <label className={`block text-xs font-medium text-secondary mb-1.5 ${className}`} {...rest}>
      {children}
    </label>
  )
}
