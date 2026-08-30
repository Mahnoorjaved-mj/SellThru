import { useEffect, useState } from 'react'
import { useTheme } from '../app/ThemeProvider'
import { formatCompactNumber } from './format'

function readTokens() {
  const styles = getComputedStyle(document.documentElement)
  const get = (name) => styles.getPropertyValue(name).trim()
  return {
    border: get('--color-border'),
    textTertiary: get('--color-text-tertiary'),
    textSecondary: get('--color-text-secondary'),
    text: get('--color-text'),
    surface: get('--color-surface'),
    accent: get('--color-accent'),
    positive: get('--color-positive'),
    negative: get('--color-negative'),
    warning: get('--color-warning'),
    series: [1, 2, 3, 4, 5].map((i) => get(`--chart-series-${i}`)),
  }
}

/** Re-reads CSS tokens whenever the resolved theme changes, so charts re-render on toggle. */
export function useChartTheme() {
  const { resolvedTheme } = useTheme()
  const [tokens, setTokens] = useState(readTokens)

  useEffect(() => {
    setTokens(readTokens())
  }, [resolvedTheme])

  return tokens
}

function hexToRgba(hex, alpha) {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function seriesAlpha(hexOrRgb, alpha) {
  if (hexOrRgb.startsWith('#')) return hexToRgba(hexOrRgb, alpha)
  return hexOrRgb
}

/**
 * Single options factory used by every line/bar chart in the app.
 * Grid: horizontal only. Ticks: mono, tertiary, compact numbers, max 6 y-ticks.
 * Lines/points/tooltip config is left to callers via `extend`, but the
 * grid/tick/axis skeleton here must not be duplicated per chart.
 */
export function baseChartOptions(tokens, { extend = {} } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 150 },
    interaction: { mode: 'index', intersect: false },
    // Legend and tooltip are always custom (see components/charts/) — callers
    // supply `plugins.tooltip.external` and render their own <ChartLegend>.
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
    },
    scales: {
      x: {
        border: { display: true, color: tokens.border },
        grid: { display: false },
        ticks: {
          color: tokens.textTertiary,
          font: { family: '"IBM Plex Mono", monospace', size: 11 },
          autoSkip: true,
          maxTicksLimit: 12,
        },
      },
      y: {
        border: { display: false },
        grid: { color: tokens.border, drawTicks: false },
        ticks: {
          color: tokens.textTertiary,
          font: { family: '"IBM Plex Mono", monospace', size: 11 },
          maxTicksLimit: 6,
          callback: (value) => formatCompactNumber(value),
        },
      },
    },
    ...extend,
  }
}

/** Standard line-series look: 1.5px, nearly-straight, no points except on hover. */
export function lineSeriesStyle(color, { dashed = false } = {}) {
  return {
    borderColor: color,
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderDash: dashed ? [4, 3] : undefined,
    tension: 0.15,
    pointRadius: 0,
    pointHoverRadius: 3,
    pointBackgroundColor: color,
    pointBorderWidth: 0,
    borderCapStyle: 'round',
    spanGaps: true,
  }
}

/** Confidence-band fill: 8-10% alpha of the series colour, no border. */
export function bandFillStyle(color, alpha = 0.09) {
  return {
    borderWidth: 0,
    backgroundColor: seriesAlpha(color, alpha),
    pointRadius: 0,
    tension: 0.15,
    spanGaps: true,
  }
}
