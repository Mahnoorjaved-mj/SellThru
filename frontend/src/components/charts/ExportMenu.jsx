import { Download, Image as ImageIcon } from 'lucide-react'

const FORMULA_PREFIX_RE = /^[=+\-@]/

function sanitizeCell(value) {
  const s = value === null || value === undefined ? '' : String(value)
  const safe = FORMULA_PREFIX_RE.test(s) ? `'${s}` : s
  if (/[",\n]/.test(safe)) return `"${safe.replace(/"/g, '""')}"`
  return safe
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function exportCsv(rows, filename) {
  if (!rows || rows.length === 0) return
  const headers = Object.keys(rows[0])
  const lines = [headers.join(',')]
  for (const row of rows) {
    lines.push(headers.map((h) => sanitizeCell(row[h])).join(','))
  }
  downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }), filename)
}

function exportPng(chartRef, filename) {
  const chart = chartRef?.current
  if (!chart) return
  const url = chart.toBase64Image('image/png', 1)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}

/** Two compact export actions: PNG of the chart canvas, CSV of the underlying series data. */
export function ExportMenu({ chartRef, csvRows, filenameBase = 'chart' }) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => exportPng(chartRef, `${filenameBase}.png`)}
        title="Export PNG"
        className="flex items-center justify-center h-6 w-6 rounded text-tertiary hover:text-primary hover:bg-surface-hover transition-colors duration-120 ease-out"
      >
        <ImageIcon size={13} />
      </button>
      <button
        onClick={() => exportCsv(csvRows, `${filenameBase}.csv`)}
        title="Export CSV"
        className="flex items-center justify-center h-6 w-6 rounded text-tertiary hover:text-primary hover:bg-surface-hover transition-colors duration-120 ease-out"
      >
        <Download size={13} />
      </button>
    </div>
  )
}
