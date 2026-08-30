/** Formatting helpers used across charts and tables. No inline toFixed(2) elsewhere. */

const compactFormatter = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 })

export function formatCompactNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return compactFormatter.format(value)
}

export function formatCurrency(value, { compact = false } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (compact) return `$${formatCompactNumber(value)}`
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatPercent(value, { sign = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const prefix = sign && value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}%`
}

export function formatDate(value, opts = { dateStyle: 'short' }) {
  if (!value) return '—'
  // toLocaleDateString doesn't accept timeStyle — toLocaleString does, and
  // covers the dateStyle-only case too, so it's the one safe method to call.
  return new Date(value).toLocaleString(undefined, opts)
}
