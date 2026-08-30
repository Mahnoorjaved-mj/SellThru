const VARIANTS = {
  primary: 'bg-accent text-white hover:bg-accent-hover',
  secondary: 'bg-surface text-primary border border-line hover:bg-surface-hover',
  ghost: 'bg-transparent text-secondary hover:bg-surface-hover hover:text-primary',
  danger: 'bg-down text-white hover:opacity-90',
}

const SIZES = {
  compact: 'h-7 px-2.5 text-xs',
  default: 'h-8 px-3.5 text-sm',
  submit: 'h-9 px-4 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'default',
  className = '',
  disabled,
  children,
  ...rest
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded font-medium
        transition-colors duration-120 ease-out disabled:opacity-50 disabled:cursor-not-allowed
        ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}
