const VARIANTS = {
  primary: 'bg-accent text-white hover:bg-accent-hover shadow-xs active:scale-[0.99]',
  secondary: 'bg-surface text-primary border border-line hover:bg-surface-hover hover:border-line-strong active:scale-[0.99]',
  ghost: 'bg-transparent text-secondary hover:bg-surface-hover hover:text-primary active:scale-[0.99]',
  danger: 'bg-down text-white hover:opacity-90 shadow-xs active:scale-[0.99]',
  emerald: 'bg-emerald-green text-white hover:bg-emerald-700 shadow-xs active:scale-[0.99]',
}

const SIZES = {
  compact: 'h-7 px-2.5 text-xs rounded-control',
  default: 'h-8 px-3.5 text-sm rounded-control',
  submit: 'h-9 px-4 text-sm rounded-control font-semibold',
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
      className={`inline-flex items-center justify-center gap-1.5 font-medium
        transition-all duration-120 ease-out disabled:opacity-50 disabled:cursor-not-allowed
        ${VARIANTS[variant] || VARIANTS.primary} ${SIZES[size] || SIZES.default} ${className}`}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}
