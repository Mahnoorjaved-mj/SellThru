/** 60x20px trend line for KPI cards / table rows. No axes, no grid. Plain SVG — no Chart.js overhead for this size. */
export function Sparkline({ data, color = 'currentColor', width = 60, height = 20 }) {
  const values = (data || []).filter((v) => typeof v === 'number' && !Number.isNaN(v))
  if (values.length < 2) return <svg width={width} height={height} />

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = width / (values.length - 1)

  const points = values
    .map((v, i) => {
      const x = i * stepX
      const y = height - ((v - min) / range) * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
