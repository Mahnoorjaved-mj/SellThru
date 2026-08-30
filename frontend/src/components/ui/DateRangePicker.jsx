import { Input } from './Input'
import { Select } from './Select'

const PRESETS = [
  { value: '', label: 'All time' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'custom', label: 'Custom range' },
]

function presetToRange(preset) {
  if (!preset || preset === 'custom') return { start: '', end: '' }
  const days = { '7d': 7, '30d': 30, '90d': 90 }[preset]
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days)
  const fmt = (d) => d.toISOString().slice(0, 10)
  return { start: fmt(start), end: fmt(end) }
}

/** Preset dropdown (Today/7D/30D/90D/Custom) + native date inputs when Custom is chosen. */
export function DateRangePicker({ preset, startDate, endDate, onChange }) {
  const handlePreset = (value) => {
    if (value === 'custom') {
      onChange({ preset: value, startDate, endDate })
      return
    }
    const range = presetToRange(value)
    onChange({ preset: value, startDate: range.start, endDate: range.end })
  }

  return (
    <div className="flex items-end gap-2">
      <div>
        <label className="ss-label">Range</label>
        <Select value={preset} onChange={(e) => handlePreset(e.target.value)}>
          {PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </Select>
      </div>
      {preset === 'custom' && (
        <>
          <div>
            <label className="ss-label">Start</label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => onChange({ preset, startDate: e.target.value, endDate })}
            />
          </div>
          <div>
            <label className="ss-label">End</label>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => onChange({ preset, startDate, endDate: e.target.value })}
            />
          </div>
        </>
      )}
    </div>
  )
}
