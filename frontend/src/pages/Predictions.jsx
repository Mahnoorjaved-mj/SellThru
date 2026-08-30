import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { Play, HelpCircle, Activity, Calendar } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Select } from '../components/ui/Select'
import { Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { ChartLegend } from '../components/charts/ChartLegend'
import { ExportMenu } from '../components/charts/ExportMenu'
import { crosshairPlugin } from '../components/charts/crosshairPlugin'
import { createExternalTooltipHandler } from '../components/charts/tooltip'
import { useChartTheme, baseChartOptions, lineSeriesStyle, bandFillStyle } from '../lib/chartTheme'
import { formatCompactNumber } from '../lib/format'
import { ReorderSuggestion } from '../components/ReorderSuggestion'

export default function Predictions() {
  const { getPredictions, trainModel, getSalesHistory, toast } = useApp()

  // Prediction Parameters
  const [storeOptions, setStoreOptions] = useState([])
  const [productOptions, setProductOptions] = useState([])
  const [storeId, setStoreId] = useState('')
  const [productId, setProductId] = useState('')
  const [horizon, setHorizon] = useState(30)

  // Data States
  const [predictions, setPredictions] = useState([])
  const [modelMeta, setModelMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)

  // Fetch Dropdown options from sales history filters
  const loadDropdownOptions = useCallback(async () => {
    try {
      const res = await getSalesHistory({ page: 1, limit: 1 })
      if (res.filters) {
        setStoreOptions(res.filters.stores || [])
        setProductOptions(res.filters.products || [])

        // Auto-select first options if available
        if (res.filters.stores?.length > 0) setStoreId(res.filters.stores[0])
        if (res.filters.products?.length > 0) setProductId(res.filters.products[0])
      }
    } catch (err) {
      toast(err.message, 'error')
    }
  }, [getSalesHistory, toast])

  const fetchForecast = useCallback(async () => {
    if (!storeId || !productId) return
    setLoading(true)
    try {
      const res = await getPredictions({
        store_id: storeId,
        product_id: productId,
        horizon_days: horizon
      })
      setPredictions(res.predictions || [])
      setModelMeta(res.model)
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getPredictions, storeId, productId, horizon, toast])

  useEffect(() => {
    loadDropdownOptions()
  }, [loadDropdownOptions])

  useEffect(() => {
    fetchForecast()
  }, [fetchForecast])

  const handleRetrain = async () => {
    if (training) return
    setTraining(true)
    try {
      toast('Retraining Random Forest regressors...', 'info')
      const res = await trainModel()
      toast(res.message, 'success')
      await fetchForecast()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setTraining(false)
    }
  }

  // Chart Setup with Confidence Intervals Ribbon
  const chartLabels = predictions.map((p) => p.date)
  const upperData = predictions.map((p) => p.confidence_upper)
  const lowerData = predictions.map((p) => p.confidence_lower)
  const forecastData = predictions.map((p) => p.quantity)

  const tokens = useChartTheme()
  const chartRef = useRef(null)

  const lineData = {
    labels: chartLabels,
    datasets: [
      {
        label: 'Upper Bound',
        data: upperData,
        borderWidth: 0,
        pointRadius: 0,
        fill: false,
        spanGaps: true
      },
      {
        label: 'Lower Bound',
        data: lowerData,
        fill: 0, // fills to Upper Bound (index 0)
        ...bandFillStyle(tokens.accent),
      },
      {
        label: 'Forecast Qty',
        data: forecastData,
        ...lineSeriesStyle(tokens.accent),
      }
    ]
  }

  const lineOptions = baseChartOptions(tokens, {
    extend: {
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: false,
          external: createExternalTooltipHandler({ formatValue: (v) => `${formatCompactNumber(v)} units` }),
        },
        crosshair: { color: tokens.border },
      },
    },
  })

  const csvRows = predictions.map((p) => ({
    date: p.date,
    quantity: p.quantity,
    confidence_lower: p.confidence_lower,
    confidence_upper: p.confidence_upper,
  }))

  return (
    <div className="space-y-6">
      {/* Top Selector Panel */}
      <Panel>
        <PanelBody className="flex flex-col md:flex-row items-end gap-4">
          <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label>Store location</Label>
              <Select value={storeId} onChange={(e) => setStoreId(e.target.value)}>
                {storeOptions.length === 0 && <option value="">No stores found</option>}
                {storeOptions.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
            </div>

            <div>
              <Label>Product SKU</Label>
              <Select value={productId} onChange={(e) => setProductId(e.target.value)}>
                {productOptions.length === 0 && <option value="">No products found</option>}
                {productOptions.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </Select>
            </div>

            <div>
              <Label>Forecast horizon</Label>
              <Select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
                <option value={7}>7 days ahead</option>
                <option value={14}>14 days ahead</option>
                <option value={30}>30 days ahead</option>
                <option value={60}>60 days ahead</option>
              </Select>
            </div>
          </div>
        </PanelBody>
      </Panel>

      {/* Main Grid: Forecast Chart + AI Model details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Forecast Chart (2/3 width) */}
        <Panel className="lg:col-span-2 flex flex-col justify-between">
          <PanelHeader
            title="Sales quantity forecast"
            description={<>Daily predictions with 90% confidence band for store <span className="text-primary font-semibold">{storeId}</span> and product <span className="text-primary font-semibold">{productId}</span>.</>}
            actions={predictions.length > 0 && <ExportMenu chartRef={chartRef} csvRows={csvRows} filenameBase="forecast" />}
          />
          <PanelBody>
            {loading ? (
              <SkeletonPanel rows={4} />
            ) : predictions.length > 0 ? (
              <>
                <ChartLegend series={[{ label: 'Forecast Qty', color: tokens.accent }]} />
                <div className="h-80 w-full relative">
                  <Line ref={chartRef} data={lineData} options={lineOptions} plugins={[crosshairPlugin]} />
                </div>
              </>
            ) : (
              <EmptyState
                title="No predictions available"
                description="Ensure you have seeded or uploaded transactions for this store and product."
              />
            )}
          </PanelBody>
        </Panel>

        {/* Model Meta info & Training Card (1/3 width) */}
        <Panel className="flex flex-col justify-between">
          <PanelBody>
            <h3 className="text-section font-semibold text-primary flex items-center gap-1.5 mb-3">
              <Activity className="text-accent" size={18} />
              <span>Active model engine</span>
            </h3>

            {modelMeta ? (
              <div className="space-y-4">
                <div className="p-3 bg-bg border border-line rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar size={15} className="text-secondary" />
                    <span className="text-xs font-semibold text-secondary">Trained date</span>
                  </div>
                  <span className="text-xs font-semibold text-primary font-mono tabular-nums">
                    {new Date(modelMeta.trained_at).toLocaleDateString(undefined, { dateStyle: 'short' })}
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="ss-eyebrow mb-1">Quality scores</div>
                  <div className="flex items-center justify-between text-xs py-1 border-b border-line">
                    <span className="text-secondary">R-squared (R²) score</span>
                    <span className="font-semibold text-primary font-mono tabular-nums">{modelMeta.metrics.r2.toFixed(4)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs py-1 border-b border-line">
                    <span className="text-secondary">RMSE error</span>
                    <span className="font-semibold text-primary font-mono tabular-nums">{modelMeta.metrics.rmse.toFixed(2)} units</span>
                  </div>
                  <div className="flex items-center justify-between text-xs py-1">
                    <span className="text-secondary">MAE error</span>
                    <span className="font-semibold text-primary font-mono tabular-nums">{modelMeta.metrics.mae.toFixed(2)} units</span>
                  </div>
                </div>

                <div>
                  <div className="ss-eyebrow mb-1.5">Engine status</div>
                  <Badge variant="positive">ML pipeline active (Random Forest)</Badge>
                </div>
              </div>
            ) : (
              <div className="text-xs text-secondary leading-relaxed bg-bg border border-line rounded p-4 flex gap-2">
                <HelpCircle size={16} className="text-accent flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-primary mb-1">Running baseline stats</p>
                  <p>
                    No ML model has been trained yet. You are currently viewing seasonal projection baselines. Train the Random Forest model below.
                  </p>
                </div>
              </div>
            )}
          </PanelBody>

          <div className="p-4 pt-0">
            <Button size="submit" className="w-full font-semibold" onClick={handleRetrain} disabled={training}>
              <Play size={14} className="fill-current" />
              <span>{training ? 'Training AI model…' : 'Retrain forecasting model'}</span>
            </Button>
            <p className="text-[10px] text-center text-tertiary mt-2">
              Requires a minimum of 30 sales rows in the database to train.
            </p>
          </div>
        </Panel>
      </div>

      {predictions.length > 0 && <ReorderSuggestion predictions={predictions} />}
    </div>
  )
}
