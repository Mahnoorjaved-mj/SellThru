import { useEffect, useState, useCallback } from 'react'
import { Bell, Plus, Trash2, RefreshCw } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Select } from '../components/ui/Select'
import { Input, Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { formatDate } from '../lib/format'

const SEVERITY_VARIANT = { negative: 'negative', warning: 'warning', info: 'accent' }

export default function Alerts() {
  const {
    getAlertRules, createAlertRule, enableAlertRule, disableAlertRule, deleteAlertRule,
    evaluateAlertRules, getNotifications, markAllNotificationsRead, toast,
  } = useApp()

  const [rules, setRules] = useState([])
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(false)

  const [ruleType, setRuleType] = useState('forecast_drop')
  const [storeId, setStoreId] = useState('')
  const [productId, setProductId] = useState('')
  const [thresholdPct, setThresholdPct] = useState('20')
  const [minAbsZ, setMinAbsZ] = useState('3')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rulesRes, notifsRes] = await Promise.all([getAlertRules(), getNotifications()])
      setRules(rulesRes.rules || [])
      setNotifications(notifsRes.notifications || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getAlertRules, getNotifications, toast])

  useEffect(() => {
    load()
  }, [load])

  const handleCreateRule = async (e) => {
    e.preventDefault()
    try {
      const rule = { type: ruleType }
      if (ruleType === 'forecast_drop') {
        rule.store_id = storeId || undefined
        rule.product_id = productId || undefined
        rule.threshold_pct = Number(thresholdPct)
      } else {
        rule.min_abs_z = Number(minAbsZ)
      }
      await createAlertRule(rule)
      toast('Alert rule created', 'success')
      await load()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleToggle = async (rule) => {
    try {
      if (rule.enabled) await disableAlertRule(rule.id)
      else await enableAlertRule(rule.id)
      await load()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteAlertRule(id)
      setRules((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleEvaluate = async () => {
    setEvaluating(true)
    try {
      const res = await evaluateAlertRules()
      toast(`Checked ${res.rules_checked} rule(s), ${res.notifications_created} new alert(s)`, 'success')
      await load()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setEvaluating(false)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  if (loading) return <SkeletonPanel rows={6} />

  const unreadCount = notifications.filter((n) => !n.read).length

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rule creation */}
        <Panel className="lg:col-span-1">
          <PanelHeader title="New alert rule" />
          <PanelBody>
            <form onSubmit={handleCreateRule} className="space-y-3">
              <div>
                <Label>Trigger type</Label>
                <Select value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                  <option value="forecast_drop">Forecast drop</option>
                  <option value="anomaly_high">High-severity anomaly</option>
                </Select>
              </div>

              {ruleType === 'forecast_drop' ? (
                <>
                  <div>
                    <Label>Store (optional)</Label>
                    <Input value={storeId} onChange={(e) => setStoreId(e.target.value)} placeholder="e.g. Store-101" />
                  </div>
                  <div>
                    <Label>Product (optional)</Label>
                    <Input value={productId} onChange={(e) => setProductId(e.target.value)} placeholder="e.g. PROD-A" />
                  </div>
                  <div>
                    <Label>Drop threshold (%)</Label>
                    <Input type="number" numeric value={thresholdPct} onChange={(e) => setThresholdPct(e.target.value)} />
                  </div>
                </>
              ) : (
                <div>
                  <Label>Minimum |z-score|</Label>
                  <Input type="number" numeric value={minAbsZ} onChange={(e) => setMinAbsZ(e.target.value)} />
                </div>
              )}

              <Button type="submit" size="submit" className="w-full font-semibold">
                <Plus size={14} />
                <span>Create rule</span>
              </Button>
            </form>
          </PanelBody>
        </Panel>

        {/* Active rules */}
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Active rules"
            actions={
              <Button variant="secondary" size="compact" onClick={handleEvaluate} disabled={evaluating}>
                <RefreshCw size={12} className={evaluating ? 'animate-spin' : ''} />
                <span>{evaluating ? 'Checking…' : 'Check now'}</span>
              </Button>
            }
          />
          {rules.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No alert rules yet" description="Create one on the left. Rules are also checked automatically once a day." />
            </div>
          ) : (
            <div className="divide-y divide-line">
              {rules.map((r) => (
                <div key={r.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-primary">
                      {r.type === 'forecast_drop' ? 'Forecast drop' : 'High-severity anomaly'}
                    </p>
                    <p className="text-xs text-secondary">
                      {r.type === 'forecast_drop'
                        ? `${r.params?.product_id || 'Any product'} at ${r.params?.store_id || 'any store'} — threshold ${r.params?.threshold_pct ?? 20}%`
                        : `|z-score| ≥ ${r.params?.min_abs_z ?? 3}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleToggle(r)}>
                      <Badge variant={r.enabled ? 'positive' : 'neutral'}>{r.enabled ? 'Enabled' : 'Disabled'}</Badge>
                    </button>
                    <Button variant="ghost" size="compact" onClick={() => handleDelete(r.id)}>
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Notification feed */}
      <Panel>
        <PanelHeader
          title="Notifications"
          description={unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          actions={
            unreadCount > 0 && (
              <Button variant="ghost" size="compact" onClick={handleMarkAllRead}>
                Mark all read
              </Button>
            )
          }
        />
        {notifications.length === 0 ? (
          <div className="p-4">
            <EmptyState icon={Bell} title="No notifications yet" description="Triggered alerts will show up here." />
          </div>
        ) : (
          <div className="divide-y divide-line">
            {notifications.map((n) => (
              <div key={n.id} className={`flex items-start gap-3 px-4 py-3 ${!n.read ? 'bg-accent-soft/40' : ''}`}>
                <Badge variant={SEVERITY_VARIANT[n.severity] || 'neutral'}>{n.severity}</Badge>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-primary">{n.title}</p>
                  <p className="text-xs text-secondary">{n.message}</p>
                </div>
                <span className="text-[11px] text-tertiary font-mono whitespace-nowrap">
                  {formatDate(n.created_at, { dateStyle: 'short', timeStyle: 'short' })}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}
