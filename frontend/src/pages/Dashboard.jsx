import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Database,
  ArrowUpRight,
  ArrowDownRight,
  ShoppingBag,
  Store,
  Users,
  Sparkles,
  TrendingUp,
  DollarSign,
  Activity,
} from 'lucide-react'

import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

import { useApp } from '../context/context'
import {
  Panel,
  PanelHeader,
  PanelBody,
} from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import {
  Table,
  Th,
  Td,
} from '../components/ui/Table'
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
import {
  useChartTheme,
  baseChartOptions,
  lineSeriesStyle,
} from '../lib/chartTheme'
import { formatCurrency } from '../lib/format'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
)

/* =========================================================
   DASHBOARD CACHE
   ========================================================= */

const CACHE_VERSION = 'real-data-v1'

const ACTUAL_COLOR = '#0f4c5c'
const FORECAST_COLOR = '#fa5f38'

function dashboardCacheKey(user, days) {
  const scope =
    user?._id ||
    user?.id ||
    user?.email ||
    'anonymous'

  return `sellthru-dashboard-${CACHE_VERSION}-${scope}-${days}`
}

function readDashboardCache(user, days) {
  try {
    const raw = localStorage.getItem(
      dashboardCacheKey(user, days)
    )

    if (!raw) {
      return null
    }

    const cached = JSON.parse(raw)

    if (!cached?.data) {
      return null
    }

    return cached
  } catch {
    return null
  }
}

function writeDashboardCache(user, days, data) {
  try {
    localStorage.setItem(
      dashboardCacheKey(user, days),
      JSON.stringify({
        data,
        savedAt: Date.now(),
      })
    )
  } catch {
    // Cache is optional.
  }
}

/* =========================================================
   DASHBOARD
   ========================================================= */

export default function Dashboard() {
  const {
    user,
    getDashboardSummary,
    seedSalesData,
    toast,
  } = useApp()

  const initialCache =
    readDashboardCache(user, 30)

  const [loading, setLoading] = useState(
    !initialCache?.data
  )

  const [data, setData] = useState(
    initialCache?.data || null
  )

  const [seeding, setSeeding] =
    useState(false)

  const [days, setDays] =
    useState(30)

  const [hiddenSeries, setHiddenSeries] =
    useState(() => new Set())

  const chartRef =
    useRef(null)

  const tokens =
    useChartTheme()

  /* =========================================================
     LOAD DASHBOARD
     ========================================================= */

  const loadData = useCallback(
    async (rangeDays) => {
      const cached =
        readDashboardCache(
          user,
          rangeDays
        )

      /*
       * Show cached dashboard immediately.
       */
      if (cached?.data) {
        setData(cached.data)
        setLoading(false)
      } else {
        setLoading(true)
      }

      try {
        /*
         * Fetch fresh real/demo data from backend.
         */
        const response =
          await getDashboardSummary(
            rangeDays
          )

        setData(response)
        setLoading(false)

        writeDashboardCache(
          user,
          rangeDays,
          response
        )
      } catch (error) {
        setLoading(false)

        /*
         * Never destroy a cached dashboard
         * because of a temporary API problem.
         */
        if (!cached?.data) {
          toast(
            error?.message ||
              'Unable to load dashboard data.',
            'error'
          )
        }
      }
    },
    [
      getDashboardSummary,
      toast,
      user,
    ]
  )

  useEffect(() => {
    loadData(days)
  }, [
    loadData,
    days,
  ])

  /* =========================================================
     DEMO DATA
     ========================================================= */

  const handleSeed = async () => {
    if (seeding) {
      return
    }

    setSeeding(true)

    try {
      toast(
        'Generating historical sales data...',
        'info'
      )

      const response =
        await seedSalesData()

      toast(
        response.message,
        'success'
      )

      /*
       * Refresh dashboard after demo
       * data generation.
       */
      await loadData(days)
    } catch (error) {
      toast(
        error?.message ||
          'Unable to generate demo data.',
        'error'
      )
    } finally {
      setSeeding(false)
    }
  }

  /* =========================================================
     SERIES TOGGLE
     ========================================================= */

  const toggleSeries = (label) => {
    setHiddenSeries(
      (previous) => {
        const next =
          new Set(previous)

        if (next.has(label)) {
          next.delete(label)
        } else {
          next.add(label)
        }

        return next
      }
    )
  }

  /* =========================================================
     CHART LEGEND
     ========================================================= */

  const seriesMeta = useMemo(
    () => [
      {
        label: 'Actual Sales',
        color: ACTUAL_COLOR,
        dashed: false,
      },
      {
        label: 'AI Forecast',
        color: FORECAST_COLOR,
        dashed: true,
      },
    ],
    []
  )

  const externalTooltip =
    useMemo(
      () =>
        createExternalTooltipHandler({
          formatValue: (value) =>
            formatCurrency(
              value,
              {
                compact: true,
              }
            ),
        }),
      []
    )

  /* =========================================================
     LOADING
     ========================================================= */

  if (loading) {
    return (
      <div
        className="
          grid
          grid-cols-1
          gap-4
          sm:grid-cols-2
          lg:grid-cols-3
        "
      >
        {Array.from({
          length: 3,
        }).map((_, index) => (
          <SkeletonPanel
            key={index}
            rows={2}
          />
        ))}

        <div
          className="
            sm:col-span-2
            lg:col-span-3
          "
        >
          <SkeletonPanel rows={5} />
        </div>
      </div>
    )
  }

  /* =========================================================
     EMPTY STATE
     ========================================================= */

  if (
    !data ||
    data.status === 'empty'
  ) {
    return (
      <div
        className="
          max-w-2xl
          mx-auto
          mt-12
        "
      >
        <div
          className="
            ss-card
            p-8
            flex
            flex-col
            items-start
          "
        >
          <EmptyState
            icon={Sparkles}
            title="No sales data yet"
            description="
              Upload your real retail CSV dataset
              through the Transactions page.
            "
          />

          <div
            className="
              flex
              flex-col
              sm:flex-row
              gap-2
              w-full
              sm:w-auto
            "
          >
            <Link
              to="/data"
              className="ss-btn px-4"
            >
              <Database size={15} />

              <span>
                Upload real dataset
              </span>
            </Link>

            {user?.is_admin && (
              <Button
                variant="secondary"
                onClick={handleSeed}
                disabled={seeding}
              >
                {seeding
                  ? 'Generating…'
                  : 'Seed demo sales data'}
              </Button>
            )}
          </div>
        </div>
      </div>
    )
  }

  const {
    kpis,
    history_chart,
    category_chart,
    recent_transactions,
  } = data

  /* =========================================================
     CHART DATA
     ========================================================= */

  const chartLabels =
    history_chart.map(
      (item) => item.date
    )

  const actualValues =
    history_chart.map(
      (item) => item.actual
    )

  const forecastValues =
    history_chart.map(
      (item) => item.forecast
    )

  const boundaryIndex =
    history_chart.filter(
      (item) =>
        item.actual !== null
    ).length - 1

  const historyData = {
    labels: chartLabels,

    datasets: [
      {
        label: 'Actual Sales',
        data: actualValues,
        hidden: hiddenSeries.has('Actual Sales'),
        ...lineSeriesStyle(ACTUAL_COLOR),
        borderWidth: 2.5,
        tension: 0.35,
        fill: true,
        backgroundColor: 'rgba(70, 92, 89, 0.08)',
        pointRadius: 2.5,
        pointHoverRadius: 6,
        pointBackgroundColor: ACTUAL_COLOR,
      },
      {
        label: 'AI Forecast',
        data: forecastValues,
        hidden: hiddenSeries.has('AI Forecast'),
        ...lineSeriesStyle(FORECAST_COLOR, { dashed: true }),
        borderWidth: 2.5,
        tension: 0.35,
        fill: true,
        backgroundColor: 'rgba(207, 161, 44, 0.08)',
        pointRadius: 2.5,
        pointHoverRadius: 6,
        pointBackgroundColor: FORECAST_COLOR,
      },
    ],
  }

  const historyOptions =
    baseChartOptions(
      tokens,
      {
        extend: {
          plugins: {
            legend: {
              display: false,
            },

            tooltip: {
              enabled: false,
              external:
                externalTooltip,
            },

            crosshair: {
              color:
                tokens.border,
            },
          },
        },
      }
    )

  /* =========================================================
     SPARKLINES
     ========================================================= */

  const netSalesSpark =
    actualValues.filter(
      (value) =>
        value !== null
    )

  const forecastSpark =
    forecastValues.filter(
      (value) =>
        value !== null
    )

  /* =========================================================
     EXPORT
     ========================================================= */

  const csvRows =
    history_chart.map(
      (item) => ({
        date: item.date,
        actual:
          item.actual ?? '',
        forecast:
          item.forecast ?? '',
      })
    )

  const isRealData =
    data.data_source === 'real'

  /* =========================================================
     UI
     ========================================================= */

  return (
    <div className="space-y-6">
      {/* HEADER & SOURCE INDICATOR */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-primary">Executive Dashboard</h1>
            <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-light-aqua px-2.5 py-0.5 text-xs font-semibold text-deep-teal dark:bg-emerald-950/80 dark:text-emerald-300">
              <Activity size={12} className="text-emerald-500" /> Realtime
            </span>
          </div>
          <p className="text-xs text-secondary mt-1">Multi-store demand forecasting and predictive retail intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider shadow-xs ${
              isRealData
                ? 'bg-soft-green text-emerald-green border border-emerald-500/25 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800'
                : 'bg-pale-blue text-deep-teal border border-deep-teal/20 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                isRealData ? 'bg-emerald-green animate-pulse' : 'bg-deep-teal'
              }`}
            />
            {isRealData ? 'LIVE PRODUCTION DATA' : 'DEMO BENCHMARK DATA'}
          </span>
        </div>
      </div>

      {/* =====================================================
          KPI STRIP — 5 MODERN INTERACTIVE CARDS
          ===================================================== */}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* CARD 1: NET SALES */}
        <div className="ss-card p-4.5 flex flex-col justify-between hover:-translate-y-0.5 transition-all duration-200">
          <div>
            <div className="flex items-center justify-between">
              <span className="ss-eyebrow">Net Sales ({days}d)</span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-light-aqua text-deep-teal dark:bg-emerald-950 dark:text-emerald-300">
                <DollarSign size={14} />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-primary font-mono tabular-nums mt-2 tracking-tight">
              {formatCurrency(kpis.total_sales)}
            </h3>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-line/50">
            <span className="text-[11px] text-secondary font-mono tabular-nums">
              Avg daily: {formatCurrency(kpis.avg_daily_sales)}
            </span>
            <Sparkline data={netSalesSpark} color={ACTUAL_COLOR} />
          </div>
        </div>

        {/* CARD 2: AI FORECAST */}
        <div className="ss-card p-4.5 flex flex-col justify-between hover:-translate-y-0.5 transition-all duration-200">
          <div>
            <div className="flex items-center justify-between">
              <span className="ss-eyebrow">AI Forecast ({days}d)</span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-coral-orange/15 text-coral-orange">
                <Sparkles size={14} />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-primary font-mono tabular-nums mt-2 tracking-tight">
              {formatCurrency(kpis.forecast_sales_30d)}
            </h3>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-line/50">
            <span
              className={`inline-flex items-center gap-1 font-mono tabular-nums text-xs font-bold rounded-md px-1.5 py-0.5 ${
                kpis.variance_pct >= 0
                  ? 'bg-soft-green text-emerald-green dark:bg-emerald-950/60 dark:text-emerald-300'
                  : 'bg-coral-orange/15 text-coral-orange'
              }`}
            >
              {kpis.variance_pct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {Math.abs(kpis.variance_pct).toFixed(1)}%
            </span>
            <Sparkline data={forecastSpark} color={FORECAST_COLOR} />
          </div>
        </div>

        {/* CARD 3: ACTIVE NETWORK */}
        <div className="ss-card p-4.5 flex flex-col justify-between hover:-translate-y-0.5 transition-all duration-200">
          <div>
            <div className="flex items-center justify-between">
              <span className="ss-eyebrow">{isRealData ? 'Active Customers' : 'Active Stores'}</span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-pale-blue text-deep-teal dark:bg-sky-950 dark:text-sky-300">
                {isRealData ? <Users size={14} /> : <Store size={14} />}
              </div>
            </div>
            <h3 className="text-2xl font-bold text-primary font-mono tabular-nums mt-2 tracking-tight">
              {isRealData ? kpis.active_customers : kpis.active_stores}
            </h3>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-line/50">
            <span className="text-[11px] text-secondary">
              {isRealData ? 'Verified buyers' : 'Retail locations'}
            </span>
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-green" />
          </div>
        </div>

        {/* CARD 4: PRODUCTS */}
        <div className="ss-card p-4.5 flex flex-col justify-between hover:-translate-y-0.5 transition-all duration-200">
          <div>
            <div className="flex items-center justify-between">
              <span className="ss-eyebrow">Active Catalog</span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-soft-green text-emerald-green dark:bg-emerald-950 dark:text-emerald-300">
                <ShoppingBag size={14} />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-primary font-mono tabular-nums mt-2 tracking-tight">
              {kpis.active_products}
            </h3>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-line/50">
            <span className="text-[11px] text-secondary">Predicted SKU items</span>
            <span className="text-[10px] font-semibold text-deep-teal bg-light-aqua px-1.5 py-0.5 rounded dark:bg-emerald-950 dark:text-emerald-300">
              100% Tracked
            </span>
          </div>
        </div>

        {/* CARD 5: PREDICTIVE INSIGHTS HERO CARD */}
        <div className="rounded-2xl border border-deep-teal/20 bg-gradient-to-br from-deep-teal via-[#093844] to-[#041d24] p-4.5 text-white shadow-card hover:shadow-card-hover transition-all duration-200 hover:-translate-y-0.5 flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-emerald-400/10 blur-xl group-hover:bg-emerald-400/20 transition-all" />
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300">
                AI Engine
              </span>
              <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-white/10 text-emerald-300">
                <Sparkles size={12} />
              </span>
            </div>
            <h4 className="text-base font-bold tracking-tight text-white mt-2">
              Predictive Insights
            </h4>
            <p className="text-[11px] text-white/70 mt-0.5 line-clamp-2">
              Anomaly detection & auto-retrained demand trends.
            </p>
          </div>
          <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between">
            <Link
              to="/insights"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-300 hover:text-white transition-colors"
            >
              <span>Explore Insights</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
        </div>
      </div>

      {/* =====================================================
          SALES OVERVIEW
          ===================================================== */}

      <Panel>

        <PanelHeader
          title="Sales overview"

          description={
            isRealData
              ? 'Real retail dataset • actual sales vs. AI forecast'
              : 'Actual sales vs. AI forecast'
          }

          actions={
            <div
              className="
                flex
                items-center
                gap-2
              "
            >

              <RangeSwitcher
                days={days}
                onChange={setDays}
              />

              <ExportMenu
                chartRef={chartRef}
                csvRows={csvRows}
                filenameBase="sales-overview"
              />

            </div>
          }
        />

        <PanelBody>

          <ChartLegend
            series={seriesMeta}
            hidden={hiddenSeries}
            onToggle={toggleSeries}
          />

          <div
            className="
              h-72
              w-full
              relative
            "
          >

            <Line
              ref={chartRef}
              data={historyData}
              options={historyOptions}
              plugins={[
                crosshairPlugin,

                createBoundaryPlugin(
                  () => boundaryIndex,
                  {
                    color:
                      tokens.textTertiary,
                  }
                ),
              ]}
            />

          </div>

        </PanelBody>

      </Panel>

      {/* =====================================================
          CATEGORY + TRANSACTIONS
          ===================================================== */}

      <div
        className="
          grid
          grid-cols-1
          lg:grid-cols-5
          gap-6
        "
      >

        {/* CATEGORY */}

        <Panel
          className="
            lg:col-span-2
            flex
            flex-col
          "
        >

          <PanelHeader
            title="Category mix"
            description={
              `Sales share by product group (last ${days}d)`
            }
          />

          <PanelBody
            className="
              flex-1
              flex
              items-center
            "
          >

            <CategoryRankedBars
              categories={
                category_chart
              }
            />

          </PanelBody>

        </Panel>

        {/* RECENT TRANSACTIONS */}

        <Panel
          className="
            lg:col-span-3
          "
        >

          <PanelHeader
            title="Recent transactions"

            actions={
              <Link
                to="/data"
                className="
                  text-xs
                  text-secondary
                  hover:text-primary
                  transition-colors
                  duration-120
                  ease-out
                  font-medium
                "
              >
                View all
              </Link>
            }
          />

          <Table>

            <thead>

              <tr>

                <Th>
                  Date
                </Th>

                <Th>
                  {isRealData
                    ? 'Customer'
                    : 'Store'}
                </Th>

                <Th>
                  Product
                </Th>

                <Th numeric>
                  Qty
                </Th>

                <Th numeric>
                  Revenue
                </Th>

              </tr>

            </thead>

            <tbody>

              {recent_transactions.map(
                (transaction) => (
                  <tr
                    key={
                      transaction.id
                    }
                  >

                    <Td
                      className="
                        whitespace-nowrap
                        font-medium
                      "
                    >
                      {new Date(
                        transaction.date
                      ).toLocaleDateString(
                        undefined,
                        {
                          dateStyle:
                            'short',
                        }
                      )}
                    </Td>

                    <Td>

                      {isRealData
                        ? (
                            transaction.customer_id ||
                            '—'
                          )
                        : (
                            transaction.store_id
                          )}

                    </Td>

                    <Td
                      className="
                        font-semibold
                        text-slate-700
                      "
                    >
                      {
                        transaction.product_id
                      }
                    </Td>

                    <Td numeric>
                      {
                        transaction.quantity
                      }
                    </Td>

                    <Td
                      numeric
                      className="
                        font-semibold
                      "
                    >
                      $
                      {Number(
                        transaction.revenue ||
                          0
                      ).toLocaleString()}
                    </Td>

                  </tr>
                )
              )}

            </tbody>

          </Table>

        </Panel>

      </div>

    </div>
  )
}