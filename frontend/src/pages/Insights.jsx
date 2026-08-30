import { useEffect, useState, useCallback } from 'react'
import {
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Percent,
  Store,
  Info,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Check
} from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Table, Th, Td } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import { Select } from '../components/ui/Select'
import { Button } from '../components/ui/Button'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'

export default function Insights() {
  const { getAnomalies, acknowledgeAnomaly, getTrends, toast } = useApp()
  const [anomalies, setAnomalies] = useState([])
  const [trends, setTrends] = useState([])
  const [sensitivity, setSensitivity] = useState('medium')
  const [loading, setLoading] = useState(true)
  const [ackingKey, setAckingKey] = useState(null)

  const loadInsights = useCallback(async () => {
    setLoading(true)
    try {
      const anomaliesRes = await getAnomalies(sensitivity)
      const trendsRes = await getTrends()
      setAnomalies(anomaliesRes.anomalies || [])
      setTrends(trendsRes.trends || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getAnomalies, getTrends, sensitivity, toast])

  useEffect(() => {
    loadInsights()
  }, [loadInsights])

  const handleAcknowledge = async (a) => {
    const key = `${a.store_id}|${a.product_id}|${a.date}`
    setAckingKey(key)
    try {
      await acknowledgeAnomaly(a.store_id, a.product_id, a.date)
      setAnomalies((prev) => prev.filter((x) => `${x.store_id}|${x.product_id}|${x.date}` !== key))
      toast('Marked as expected', 'success')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setAckingKey(null)
    }
  }

  const getTrendIcon = (type) => {
    switch (type) {
      case 'trend':
        return <TrendingUp className="text-accent" size={16} />
      case 'promo':
        return <Percent className="text-up" size={16} />
      case 'store':
        return <Store className="text-accent" size={16} />
      case 'alert':
        return <AlertTriangle className="text-warn" size={16} />
      default:
        return <Info className="text-secondary" size={16} />
    }
  }

  const getTrendBg = (type) => {
    switch (type) {
      case 'trend':
      case 'store':
        return 'bg-accent-soft'
      case 'promo':
        return 'bg-up-soft'
      case 'alert':
        return 'bg-warn-soft'
      default:
        return 'bg-surface-hover'
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonPanel key={i} rows={2} />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Upper Grid: Actionable BI Trends */}
      <div>
        <div className="mb-4">
          <h2 className="text-section font-semibold text-primary flex items-center gap-1.5">
            <Sparkles className="text-accent" size={16} />
            <span>AI trend discoveries</span>
          </h2>
          <p className="text-body text-secondary">Actionable observations derived from weekly and monthly sales analysis</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {trends.map((t, idx) => (
            <div key={idx} className="ss-card p-4 flex gap-3 items-start">
              <div className={`p-2 rounded flex-shrink-0 ${getTrendBg(t.type)}`}>
                {getTrendIcon(t.type)}
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-primary">{t.title}</h4>
                <p className="text-body text-secondary leading-relaxed">{t.description}</p>
              </div>
            </div>
          ))}
          {trends.length === 0 && (
            <div className="col-span-2">
              <EmptyState
                title="No trend cards calculated yet"
                description="Ensure historical sales data is seeded or uploaded."
              />
            </div>
          )}
        </div>
      </div>

      {/* Lower Block: Outlier Anomaly Detection Feed */}
      <Panel>
        <PanelHeader
          title="Anomaly alert log"
          description="Z-score + rolling median/MAD outlier detection vs. historical rolling average"
          actions={
            <Select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)} className="w-32">
              <option value="low">Low sensitivity</option>
              <option value="medium">Medium sensitivity</option>
              <option value="high">High sensitivity</option>
            </Select>
          }
        />

        {anomalies.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>Occurrence</Th>
                <Th>Location</Th>
                <Th>Product SKU</Th>
                <Th>Category</Th>
                <Th numeric>Recorded qty</Th>
                <Th numeric>Expected</Th>
                <Th numeric>Score</Th>
                <Th>Method</Th>
                <Th>Severity</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((a, idx) => {
                const key = `${a.store_id}|${a.product_id}|${a.date}`
                return (
                  <tr key={idx}>
                    <Td className="whitespace-nowrap font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        <Calendar size={12} className="text-tertiary" />
                        {a.date}
                      </span>
                    </Td>
                    <Td>{a.store_id}</Td>
                    <Td className="font-semibold text-accent">{a.product_id}</Td>
                    <Td>{a.category}</Td>
                    <Td numeric className="font-semibold">{a.quantity} units</Td>
                    <Td numeric className="text-secondary">{a.expected_mean ?? '—'} units</Td>
                    <Td numeric>{a.z_score}</Td>
                    <Td><Badge variant="neutral">{a.method === 'mad' ? 'MAD' : 'Z-score'}</Badge></Td>
                    <Td>
                      {a.type === 'spike' ? (
                        <Badge variant="positive"><ArrowUpRight size={10} />Spike</Badge>
                      ) : (
                        <Badge variant="negative"><ArrowDownRight size={10} />Drop</Badge>
                      )}
                    </Td>
                    <Td>
                      <Button variant="ghost" size="compact" onClick={() => handleAcknowledge(a)} disabled={ackingKey === key}>
                        <Check size={12} />
                        <span>Expected</span>
                      </Button>
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
        ) : (
          <div className="px-4">
            <EmptyState title="No outlier transactions detected" description="Nothing in this monitoring interval crossed the anomaly threshold." />
          </div>
        )}
      </Panel>
    </div>
  )
}
