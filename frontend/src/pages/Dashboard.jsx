import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Database, ArrowUpRight, ArrowDownRight, ShoppingBag, Store, Sparkles } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { Table, Th, Td } from '../components/ui/Table'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { Sparkline } from '../components/charts/Sparkline'
import { RangeSwitcher } from '../components/charts/RangeSwitcher'
import { ExportMenu } from '../components/charts/ExportMenu'
import { ChartLegend } from '../components/charts/ChartLegend'
import { CategoryRankedBars } from '../components/charts/CategoryRankedBars'
import { crosshairPlugin } from '../components/charts/crosshairPlugin'
import { createBoundaryPlugin } from '../components/charts/boundaryPlugin'
import { createExternalTooltipHandler } from '../components/charts/tooltip'
import { useChartTheme, baseChartOptions, lineSeriesStyle } from '../lib/chartTheme'
import { formatCurrency } from '../lib/format'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

export default function Dashboard() {
  const { user, getDashboardSummary, seedSalesData, toast } = useApp()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [seeding, setSeeding] = useState(false)
  const [days, setDays] = useState(30)
  const [hiddenSeries, setHiddenSeries] = useState(() => new Set())
  const chartRef = useRef(null)
  const tokens = useChartTheme()

  const loadData = useCallback(async (rangeDays) => {
    setLoading(true)
    try {
      const res = await getDashboardSummary(rangeDays)
      setData(res)
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getDashboardSummary, toast])

  useEffect(() => {
    loadData(days)
  }, [loadData, days])

  const handleSeed = async () => {
    if (seeding) return
    setSeeding(true)
    try {
      toast('Generating historical sales data...', 'info')
      const res = await seedSalesData()
      toast(res.message, 'success')
      await loadData(days)
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setSeeding(false)
    }
  }

  const toggleSeries = (label) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev)
      next.has(label) ? next.delete(label) : next.add(label)
      return next
    })
  }

  const seriesMeta = useMemo(
    () => [
      { label: 'Actual Sales', color: tokens.accent, dashed: false },
      { label: 'AI Forecast', color: tokens.accent, dashed: true },
    ],
    [tokens]
  )

  const externalTooltip = useMemo(
    () =>
      createExternalTooltipHandler({
        formatValue: (v) => formatCurrency(v, { compact: true }),
      }),
    []
  )

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonPanel key={i} rows={2} />
        ))}
        <div className="sm:col-span-2 lg:col-span-3">
          <SkeletonPanel rows={5} />
        </div>
      </div>
    )
  }

  // Cold Start UI (Database is empty)
  if (!data || data.status === 'empty') {
    return (
      <div className="max-w-2xl mx-auto mt-12">
        <div className="ss-card p-8 flex flex-col items-start">
          <EmptyState
            icon={Sparkles}
            title="No sales data yet"
            description="Upload your historical transactions via a CSV sheet, or seed demo data to preview the analytics dashboard and AI predictions."
          />
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            <Link to="/data" className="ss-btn px-4">
              <Database size={15} />
              <span>Go to data manager</span>
            </Link>
            {user?.is_admin && (
              <Button variant="secondary" onClick={handleSeed} disabled={seeding}>
                {seeding ? 'Generating…' : 'Seed demo sales data'}
              </Button>
            )}
          </div>
        </div>
      </div>
    )
  }

  const { kpis, history_chart, category_chart, recent_transactions } = data

  const chartLabels = history_chart.map((h) => h.date)
  const actualValues = history_chart.map((h) => h.actual)
  const forecastValues = history_chart.map((h) => h.forecast)
  const boundaryIndex = history_chart.filter((h) => h.actual !== null).length - 1

  const historyData = {
    labels: chartLabels,
    datasets: [
      {
        label: 'Actual Sales',
        data: actualValues,
        hidden: hiddenSeries.has('Actual Sales'),
        ...lineSeriesStyle(tokens.accent),
      },
      {
        label: 'AI Forecast',
        data: forecastValues,
        hidden: hiddenSeries.has('AI Forecast'),
        ...lineSeriesStyle(tokens.accent, { dashed: true }),
      },
    ],
  }

  const historyOptions = baseChartOptions(tokens, {
    extend: {
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false, external: externalTooltip },
        crosshair: { color: tokens.border },
      },
    },
  })

  const netSalesSpark = actualValues.filter((v) => v !== null)
  const forecastSpark = forecastValues.filter((v) => v !== null)

  const csvRows = history_chart.map((h) => ({
    date: h.date,
    actual: h.actual ?? '',
    forecast: h.forecast ?? '',
  }))

  return (
    <div className="space-y-6">
      {/* KPI strip: one bordered row split by hairlines, not floating cards */}
      <Panel className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-line">
        <div className="p-4">
          <p className="ss-eyebrow">Net sales ({days}d)</p>
          <h3 className="text-kpi font-semibold text-primary font-mono tabular-nums mt-1">
            {formatCurrency(kpis.total_sales)}
          </h3>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[11px] text-secondary font-mono tabular-nums">
              Avg daily: {formatCurrency(kpis.avg_daily_sales)}
            </span>
            <Sparkline data={netSalesSpark} color={tokens.accent} />
          </div>
        </div>

        <div className="p-4">
          <p className="ss-eyebrow">AI forecast (next {days}d)</p>
          <h3 className="text-kpi font-semibold text-primary font-mono tabular-nums mt-1">
            {formatCurrency(kpis.forecast_sales_30d)}
          </h3>
          <div className="flex items-center justify-between mt-1.5">
            <span className={`inline-flex items-center gap-0.5 font-mono tabular-nums text-[11px] font-semibold ${
              kpis.variance_pct >= 0 ? 'text-up' : 'text-down'
            }`}>
              {kpis.variance_pct >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
              {Math.abs(kpis.variance_pct).toFixed(1)}%
            </span>
            <Sparkline data={forecastSpark} color={tokens.accent} />
          </div>
        </div>

        <div className="p-4 flex flex-col justify-between">
          <p className="ss-eyebrow flex items-center gap-1.5"><Store size={13} /> Active stores</p>
          <h4 className="text-section font-semibold text-primary font-mono tabular-nums mt-2">{kpis.active_stores}</h4>
        </div>
        <div className="p-4 flex flex-col justify-between">
          <p className="ss-eyebrow flex items-center gap-1.5"><ShoppingBag size={13} /> Active products</p>
          <h4 className="text-section font-semibold text-primary font-mono tabular-nums mt-2">{kpis.active_products}</h4>
        </div>
        <div className="p-4 flex items-center">
          <Link to="/predictions" className="text-xs text-accent hover:underline font-semibold">
            Detailed AI predictions →
          </Link>
        </div>
      </Panel>

      {/* Main Timeline Chart */}
      <Panel>
        <PanelHeader
          title="Sales overview"
          description="Actual sales vs. AI forecast"
          actions={
            <div className="flex items-center gap-2">
              <RangeSwitcher days={days} onChange={setDays} />
              <ExportMenu chartRef={chartRef} csvRows={csvRows} filenameBase="sales-overview" />
            </div>
          }
        />
        <PanelBody>
          <ChartLegend series={seriesMeta} hidden={hiddenSeries} onToggle={toggleSeries} />
          <div className="h-72 w-full relative">
            <Line
              ref={chartRef}
              data={historyData}
              options={historyOptions}
              plugins={[crosshairPlugin, createBoundaryPlugin(() => boundaryIndex, { color: tokens.textTertiary })]}
            />
          </div>
        </PanelBody>
      </Panel>

      {/* Category Breakdown and Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <Panel className="lg:col-span-2 flex flex-col">
          <PanelHeader title="Category mix" description={`Sales share by product group (last ${days}d)`} />
          <PanelBody className="flex-1 flex items-center">
            <CategoryRankedBars categories={category_chart} />
          </PanelBody>
        </Panel>

        <Panel className="lg:col-span-3">
          <PanelHeader
            title="Recent transactions"
            actions={<Link to="/data" className="text-xs text-secondary hover:text-primary transition-colors duration-120 ease-out font-medium">View all</Link>}
          />
          <Table>
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Store</Th>
                <Th>Product</Th>
                <Th numeric>Qty</Th>
                <Th numeric>Revenue</Th>
              </tr>
            </thead>
            <tbody>
              {recent_transactions.map((t) => (
                <tr key={t.id}>
                  <Td className="whitespace-nowrap font-medium">
                    {new Date(t.date).toLocaleDateString(undefined, { dateStyle: 'short' })}
                  </Td>
                  <Td>{t.store_id}</Td>
                  <Td className="font-semibold text-accent">{t.product_id}</Td>
                  <Td numeric>{t.quantity}</Td>
                  <Td numeric className="font-semibold">${t.revenue.toLocaleString()}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      </div>
    </div>
  )
}
