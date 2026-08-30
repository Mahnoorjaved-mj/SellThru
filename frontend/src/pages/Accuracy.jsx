import { useEffect, useState, useCallback } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Table, Th, Td } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { formatDate } from '../lib/format'

const STATUS_VARIANT = { active: 'positive', candidate: 'warning', archived: 'neutral' }

export default function Accuracy() {
  const { getModels, promoteModel, toast } = useApp()
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [promotingId, setPromotingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getModels()
      setModels(res.models || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getModels, toast])

  useEffect(() => {
    load()
  }, [load])

  const handlePromote = async (id) => {
    setPromotingId(id)
    try {
      const res = await promoteModel(id)
      toast(res.message, 'success')
      await load()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setPromotingId(null)
    }
  }

  if (loading) {
    return <SkeletonPanel rows={6} />
  }

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader
          title="Model accuracy & version history"
          description="Every trained version, its rolling-origin backtest vs. seasonal-naive baseline, and promotion status."
        />
        {models.length === 0 ? (
          <div className="p-4">
            <EmptyState title="No models trained yet" description="Train a model from the AI Predictions page to see backtest results here." />
          </div>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Version</Th>
                <Th>Trained</Th>
                <Th numeric>Rows</Th>
                <Th numeric>WAPE</Th>
                <Th numeric>MAPE</Th>
                <Th numeric>Bias</Th>
                <Th numeric>vs. baseline</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id}>
                  <Td className="font-mono font-semibold">{m.version}</Td>
                  <Td>{formatDate(m.trained_at, { dateStyle: 'short', timeStyle: 'short' })}</Td>
                  <Td numeric>{m.training_rows ?? '—'}</Td>
                  <Td numeric className="font-semibold">{m.metrics?.wape ?? '—'}%</Td>
                  <Td numeric>{m.metrics?.mape ?? '—'}%</Td>
                  <Td numeric className={m.metrics?.bias > 0 ? 'text-warn' : 'text-secondary'}>{m.metrics?.bias ?? '—'}</Td>
                  <Td numeric>
                    {m.beats_seasonal_naive_baseline ? (
                      <span className="inline-flex items-center gap-1 text-up font-semibold">
                        <CheckCircle2 size={12} /> Beats
                      </span>
                    ) : (
                      <span className="text-down font-semibold">Below</span>
                    )}
                  </Td>
                  <Td>
                    <Badge variant={STATUS_VARIANT[m.status] || 'neutral'}>{m.status}</Badge>
                  </Td>
                  <Td>
                    {m.status !== 'active' && (
                      <Button variant="ghost" size="compact" onClick={() => handlePromote(m.id)} disabled={promotingId === m.id}>
                        {promotingId === m.id ? 'Promoting…' : 'Promote'}
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Panel>

      {models[0]?.backtest && (
        <Panel>
          <PanelHeader
            title="Latest backtest — WAPE by method"
            description={`${models[0].backtest.folds}-fold rolling-origin validation on the most recent training run`}
          />
          <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              ['Random Forest', models[0].backtest.rf_wape],
              ['Naive (last value)', models[0].backtest.naive_wape],
              ['Seasonal naive (-7d)', models[0].backtest.seasonal_naive_wape],
              ['Moving average', models[0].backtest.moving_avg_wape],
            ].map(([label, value]) => (
              <div key={label} className="ss-card p-3">
                <p className="ss-eyebrow">{label}</p>
                <p className="text-section font-semibold text-primary font-mono tabular-nums mt-1">
                  {value !== null && value !== undefined ? `${value}%` : '—'}
                </p>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  )
}
