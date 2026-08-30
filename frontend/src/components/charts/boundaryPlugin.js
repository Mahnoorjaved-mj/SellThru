/** Static vertical divider + eyebrow label marking where actuals end and the forecast begins. */
export function createBoundaryPlugin(getIndex, { color = 'rgba(128,128,128,0.4)', label = 'Forecast' } = {}) {
  return {
    id: 'boundary',
    afterDraw(chart) {
      const idx = getIndex()
      if (idx == null || idx < 0) return
      const xScale = chart.scales.x
      const { top, bottom } = chart.chartArea
      const x = xScale.getPixelForValue(idx)
      const { ctx } = chart

      ctx.save()
      ctx.beginPath()
      ctx.moveTo(x, top)
      ctx.lineTo(x, bottom)
      ctx.strokeStyle = color
      ctx.setLineDash([2, 2])
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.font = "500 10px Inter, sans-serif"
      ctx.fillStyle = color
      ctx.textAlign = 'left'
      ctx.fillText(label.toUpperCase(), x + 4, top + 10)
      ctx.restore()
    },
  }
}
