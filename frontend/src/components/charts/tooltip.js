/**
 * Custom HTML tooltip for Chart.js (`plugins.tooltip.external`). Flat panel,
 * bordered, mono numbers, shows every series value at the hovered point plus
 * its delta vs the previous point in that series.
 */
export function createExternalTooltipHandler({ formatValue = (v) => v, formatTitle = (t) => t } = {}) {
  return (context) => {
    const { chart, tooltip } = context
    const parent = chart.canvas.parentNode
    let el = parent.querySelector('.ss-chart-tooltip')
    if (!el) {
      el = document.createElement('div')
      el.className =
        'ss-chart-tooltip absolute pointer-events-none z-20 rounded-panel border border-line bg-surface ' +
        'px-3 py-2 text-xs shadow-elevated transition-opacity duration-120 ease-out min-w-[160px]'
      parent.style.position = parent.style.position || 'relative'
      parent.appendChild(el)
    }

    if (!tooltip || tooltip.opacity === 0) {
      el.style.opacity = '0'
      return
    }

    const dataPoints = tooltip.dataPoints || []
    const title = dataPoints[0] ? formatTitle(dataPoints[0].label) : ''

    const rows = dataPoints
      .filter((dp) => dp.raw !== null && dp.raw !== undefined)
      .map((dp) => {
        const ds = dp.dataset
        const idx = dp.dataIndex
        const prevVal = idx > 0 ? ds.data[idx - 1] : null
        const curVal = dp.raw
        let deltaHtml = ''
        if (typeof prevVal === 'number' && typeof curVal === 'number' && prevVal !== 0) {
          const deltaPct = ((curVal - prevVal) / Math.abs(prevVal)) * 100
          const sign = deltaPct >= 0 ? '+' : ''
          const colorClass = deltaPct >= 0 ? 'text-up' : 'text-down'
          deltaHtml = `<span class="${colorClass} ml-1.5">${sign}${deltaPct.toFixed(1)}%</span>`
        }
        const dashed = Array.isArray(ds.borderDash) && ds.borderDash.length > 0
        const swatch = dashed
          ? `border-top:2px dashed ${ds.borderColor};width:10px;display:inline-block;margin-right:6px;`
          : `border-top:2px solid ${ds.borderColor};width:10px;display:inline-block;margin-right:6px;`
        return `<div class="flex items-center justify-between gap-4">
            <span class="flex items-center text-secondary"><span style="${swatch}"></span>${ds.label}</span>
            <span class="font-mono font-semibold text-primary">${formatValue(curVal)}${deltaHtml}</span>
          </div>`
      })
      .join('')

    el.innerHTML = `<div class="text-tertiary mb-1.5 text-[11px] font-medium">${title}</div>${rows}`

    el.style.opacity = '1'
    el.style.left = `${tooltip.caretX + 14}px`
    el.style.top = `${Math.max(0, tooltip.caretY - 8)}px`
  }
}
