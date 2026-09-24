const VARIANTS = {
  neutral: 'bg-light-gray text-secondary border border-line',
  positive: 'bg-soft-green text-emerald-green border border-emerald-500/20 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800',
  negative: 'bg-coral-orange/10 text-coral-orange border border-coral-orange/20',
  warning: 'bg-coral-orange/15 text-coral-orange border border-coral-orange/25',
  accent: 'bg-light-aqua text-deep-teal border border-deep-teal/20 dark:bg-teal-950 dark:text-teal-300',
  info: 'bg-pale-blue text-deep-teal border border-sky-200 dark:bg-sky-950 dark:text-sky-300',
}

export function Badge({ variant = 'neutral', className = '', children }) {
  return <span className={`ss-badge ${VARIANTS[variant] || VARIANTS.neutral} ${className}`}>{children}</span>
}
