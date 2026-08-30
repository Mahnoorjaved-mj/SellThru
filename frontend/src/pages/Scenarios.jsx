import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { FlaskConical } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Select } from '../components/ui/Select'
import { Input, Label } from '../components/ui/Input'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { ChartLegend } from '../components/charts/ChartLegend'
import { crosshairPlugin } from '../components/charts/crosshairPlugin'
import { createExternalTooltipHandler } from '../components/charts/tooltip'
import { useChartTheme, baseChartOptions, lineSeriesStyle } from '../lib/chartTheme'
import { formatCurrency } from '../lib/format'

const DEFAULT_PROMO_UPLIFT_PCT = 15 // used only if no promo trend card is available for this org

/**
 * What-if scenarios are applied as transparent multipliers on top of the
 * real forecast already returned by the model — this page does not retrain
 * or invent a second model. Price/promo/growth are simple, explainable
 * adjustments so the "why" of every number stays visible.
 */
export default function Scenarios() {
  const { getPredictions, getSalesHistory, getTrends, toast } = useApp()

  const [storeOptions, setStoreOptions] = useState([])
  const [productOptions, setProductOptions] = useState([])
  const [storeId, setStoreId] = useState('')
  const [productId, setProductId] = useState('')
  const [predictions, setPredictions] = useState([])
  const [promoUpliftPct, setPromoUpliftPct] = useState(DEFAULT_PROMO_UPLIFT_PCT)
  const [loading, setLoading] = useState(true)

  const [priceChangePct, setPriceChangePct] = useState('0')
  const [promoOn, setPromoOn] = useState(false)
  const [monthlyGrowthPct, setMonthlyGrowthPct] = useState('0')

  const tokens = useChartTheme()
  const chartRef = useRef(null)

  const loadOptions = useCallback(async () => {
    try {
      const [historyRes, trendsRes] = await Promise.all([
        getSalesHistory({ page: 1, limit: 1 }),
        getTrends(),
      ])
      if (historyRes.filters) {
        setStoreOptions(historyRes.filters.stores || [])
        setProductOptions(historyRes.filters.products || [])
        if (historyRes.filters.stores?.length) setStoreId(historyRes.filters.stores[0])
        if (historyRes.filters.products?.length) setProductId(historyRes.filters.products[0])
      }
      const promoTrend = (trendsRes.trends || []).find((t) => t.type === 'promo')
      if (promoTrend) {
        const match = promoTrend.description.match(/([\d.]+)%/)
        if (match) setPromoUpliftPct(parseFloat(match[1]))
      }
    } catch (err) {
      toast(err.message, 'error')
    }
  }, [getSalesHistory, getTrends, toast])

  const loadForecast = useCallback(async () => {
    if (!storeId || !productId) return
    setLoading(true)
    try {
      const res = await getPredictions({ store_id: storeId, product_id: productId, horizon_days: 30 })
      setPredictions(res.predictions || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getPredictions, storeId, productId, toast])

  useEffect(() => { loadOptions() }, [loadOptions])
  useEffect(() => { loadForecast() }, [loadForecast])

  const { baseline, scenario, revenueDelta } = useMemo(() => {
    const priceMult = 1 + (parseFloat(priceChangePct) || 0) / 100
    const promoMult = promoOn ? 1 + promoUpliftPct / 100 : 1
    const monthlyGrowth = (parseFloat(monthlyGrowthPct) || 0) / 100

    let baselineTotal = 0
    let scenarioTotal = 0
    const baselineSeries = []
    const scenarioSeries = []

    predictions.forEach((p, idx) => {
      const growthMult = 1 + monthlyGrowth * (idx / 30)
      const baseRevenue = p.revenue
      const adjRevenue = p.revenue * priceMult * promoMult * growthMult

      baselineTotal += baseRevenue
      scenarioTotal += adjRevenue
      baselineSeries.push(baseRevenue)
      scenarioSeries.push(adjRevenue)
    })

    return {
      baseline: baselineSeries,
      scenario: scenarioSeries,
      revenueDelta: scenarioTotal - baselineTotal,
    }
  }, [predictions, priceChangePct, promoOn, promoUpliftPct, monthlyGrowthPct])

  const externalTooltip = useMemo(
    () => createExternalTooltipHandler({ formatValue: (v) => formatCurrency(v, { compact: true }) }),
    []
  )

  const chartData = {
    labels: predictions.map((p) => p.date),
    datasets: [
      { label: 'Baseline forecast', data: baseline, ...lineSeriesStyle(tokens.textTertiary) },
      { label: 'Scenario', data: scenario, ...lineSeriesStyle(tokens.accent) },
    ],
  }

  const chartOptions = baseChartOptions(tokens, {
    extend: {
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false, external: externalTooltip },
        crosshair: { color: tokens.border },
      },
    },
  })

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader title="Scenario inputs" description="Adjustments apply as multipliers on top of the real forecast — nothing here retrains the model." />
        <PanelBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div>
              <Label>Store</Label>
              <Select value={storeId} onChange={(e) => setStoreId(e.target.value)}>
                {storeOptions.map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
            </div>
            <div>
              <Label>Product</Label>
              <Select value={productId} onChange={(e) => setProductId(e.target.value)}>
                {productOptions.map((p) => <option key={p} value={p}>{p}</option>)}
              </Select>
            </div>
            <div>
              <Label>Price change (%)</Label>
              <Input type="number" numeric value={priceChangePct} onChange={(e) => setPriceChangePct(e.target.value)} />
            </div>
            <div>
              <Label>Monthly growth assumption (%)</Label>
              <Input type="number" numeric value={monthlyGrowthPct} onChange={(e) => setMonthlyGrowthPct(e.target.value)} />
            </div>
            <div>
              <Label>Promotion</Label>
              <Select value={promoOn ? 'on' : 'off'} onChange={(e) => setPromoOn(e.target.value === 'on')}>
                <option value="off">Off</option>
                <option value="on">{`On (+${promoUpliftPct.toFixed(1)}% observed uplift)`}</option>
              </Select>
            </div>
          </div>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          title="Revenue: baseline vs. scenario"
          description={
            predictions.length > 0
              ? `30-day projected impact: ${revenueDelta >= 0 ? '+' : ''}${formatCurrency(revenueDelta, { compact: true })}`
              : undefined
          }
        />
        <PanelBody>
          {loading ? (
            <SkeletonPanel rows={4} />
          ) : predictions.length > 0 ? (
            <>
              <ChartLegend series={[
                { label: 'Baseline forecast', color: tokens.textTertiary },
                { label: 'Scenario', color: tokens.accent },
              ]} />
              <div className="h-80 w-full relative">
                <Line ref={chartRef} data={chartData} options={chartOptions} plugins={[crosshairPlugin]} />
              </div>
            </>
          ) : (
            <EmptyState icon={FlaskConical} title="No forecast available" description="Seed or upload sales data, then train a model on the AI Predictions page." />
          )}
        </PanelBody>
      </Panel>
    </div>
  )
}
