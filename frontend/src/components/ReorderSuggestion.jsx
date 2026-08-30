import { useMemo, useState } from 'react'
import { PackageSearch } from 'lucide-react'
import { Panel, PanelHeader, PanelBody } from './ui/Panel'
import { Input, Label } from './ui/Input'
import { Select } from './ui/Select'

const SERVICE_LEVEL_Z = { 90: 1.28, 95: 1.65, 99: 2.33 }

/**
 * Reorder point/quantity computed from the already-loaded forecast series
 * plus two numbers the user enters (current stock, supplier lead time).
 * Nothing here is persisted — it's a transparent calculation, not a stock
 * ledger, so it never claims to know inventory it hasn't been told.
 */
export function ReorderSuggestion({ predictions }) {
  const [currentStock, setCurrentStock] = useState('')
  const [leadTimeDays, setLeadTimeDays] = useState('7')
  const [serviceLevel, setServiceLevel] = useState('95')

  const stats = useMemo(() => {
    if (!predictions || predictions.length === 0) return null
    const qtys = predictions.map((p) => p.quantity)
    const avgDaily = qtys.reduce((a, b) => a + b, 0) / qtys.length
    const variance = qtys.reduce((a, b) => a + (b - avgDaily) ** 2, 0) / qtys.length
    const stdDev = Math.sqrt(variance)
    return { avgDaily, stdDev }
  }, [predictions])

  if (!stats) return null

  const lead = parseFloat(leadTimeDays) || 0
  const stock = parseFloat(currentStock)
  const z = SERVICE_LEVEL_Z[serviceLevel] ?? 1.65

  const safetyStock = z * stats.stdDev * Math.sqrt(Math.max(0, lead))
  const reorderPoint = stats.avgDaily * lead + safetyStock
  const suggestedOrderQty = Number.isFinite(stock) ? Math.max(0, Math.ceil(reorderPoint - stock)) : null

  return (
    <Panel>
      <PanelHeader
        title="Reorder suggestion"
        description="Reorder point = forecast demand over lead time + safety stock. Enter your current stock to see a suggested order quantity."
      />
      <PanelBody>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div>
            <Label>Current stock on hand</Label>
            <Input
              type="number"
              numeric
              value={currentStock}
              onChange={(e) => setCurrentStock(e.target.value)}
              placeholder="e.g. 40"
            />
          </div>
          <div>
            <Label>Supplier lead time (days)</Label>
            <Input type="number" numeric value={leadTimeDays} onChange={(e) => setLeadTimeDays(e.target.value)} />
          </div>
          <div>
            <Label>Service level</Label>
            <Select value={serviceLevel} onChange={(e) => setServiceLevel(e.target.value)}>
              <option value="90">90%</option>
              <option value="95">95%</option>
              <option value="99">99%</option>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="ss-card p-3">
            <p className="ss-eyebrow">Avg daily demand</p>
            <p className="text-section font-semibold text-primary font-mono tabular-nums mt-1">
              {stats.avgDaily.toFixed(1)}
            </p>
          </div>
          <div className="ss-card p-3">
            <p className="ss-eyebrow">Reorder point</p>
            <p className="text-section font-semibold text-primary font-mono tabular-nums mt-1">
              {reorderPoint.toFixed(0)} units
            </p>
          </div>
          <div className="ss-card p-3 border-accent/40">
            <p className="ss-eyebrow flex items-center gap-1"><PackageSearch size={11} /> Suggested order</p>
            <p className="text-section font-semibold text-accent font-mono tabular-nums mt-1">
              {suggestedOrderQty !== null ? `${suggestedOrderQty} units` : 'Enter stock'}
            </p>
          </div>
        </div>
      </PanelBody>
    </Panel>
  )
}
