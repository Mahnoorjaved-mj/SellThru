/** Vertical crosshair line at the active tooltip position. Registered per-chart via `plugins: [crosshairPlugin]`. */
export const crosshairPlugin = {
  id: 'crosshair',
  afterDraw(chart) {
    const active = chart.tooltip?.getActiveElements?.() || []
    if (!active.length) return

    const { ctx, chartArea } = chart
    const x = active[0].element.x

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(x, chartArea.top)
    ctx.lineTo(x, chartArea.bottom)
    ctx.lineWidth = 1
    ctx.strokeStyle = chart.options.plugins?.crosshair?.color || 'rgba(128,128,128,0.35)'
    ctx.setLineDash([])
    ctx.stroke()
    ctx.restore()
  },
}
