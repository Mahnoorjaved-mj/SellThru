const VARIANTS = {
  neutral: 'bg-surface-hover text-secondary',
  positive: 'bg-up-soft text-up',
  negative: 'bg-down-soft text-down',
  warning: 'bg-warn-soft text-warn',
  accent: 'bg-accent-soft text-accent',
}

export function Badge({ variant = 'neutral', className = '', children }) {
  return <span className={`ss-badge ${VARIANTS[variant]} ${className}`}>{children}</span>
}
