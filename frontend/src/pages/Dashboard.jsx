import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Database,
  ArrowUpRight,
  ArrowDownRight,
  ShoppingBag,
  Store,
  Sparkles
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
import {
  useChartTheme,
  baseChartOptions,
  lineSeriesStyle
} from '../lib/chartTheme'
import { formatCurrency } from '../lib/format'

/* =========================================================
   DASHBOARD CACHE
   ========================================================= */

const DASHBOARD_CACHE_VERSION = 'v4'
const DASHBOARD_CACHE_TTL = 2 * 60 * 1000

const ACTUAL_COLOR = '#475569'
const FORECAST_COLOR = '#94A3B8'

function getDashboardCacheKey(user, days) {
  const scope =
    user?._id ||
    user?.id ||
    user?.email ||
    'anonymous'

  return `sellthru:dashboard:${DASHBOARD_CACHE_VERSION}:${scope}:${days}`
}

function readDashboardCache(user, days) {
  try {
    const raw = localStorage.getItem(
      getDashboardCacheKey(user, days)
    )

    if (!raw) {
      return null
    }

    const cached = JSON.parse(raw)

    if (!cached?.data) {
      return null
    }

    return {
      ...cached,
      isFresh:
        Date.now() - cached.savedAt <
        DASHBOARD_CACHE_TTL
    }
  } catch {
    return null
  }
}

function writeDashboardCache(user, days, data) {
  try {
    localStorage.setItem(
      getDashboardCacheKey(user, days),
      JSON.stringify({
        data,
        savedAt: Date.now()
      })
    )
  } catch {
    // Cache is optional.
    // Never break dashboard if localStorage is unavailable.
  }
}

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
)

export default function Dashboard() {
  const {
    user,
    getDashboardSummary,
    seedSalesData,
    toast
  } = useApp()

  /*
   * Read cached 30-day dashboard immediately.
   * This prevents the dashboard from showing a long
   * loading skeleton on every visit.
   */
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
    async (
      rangeDays,
      { background = false } = {}
    ) => {
      const cached =
        readDashboardCache(
          user,
          rangeDays
        )

      /*
       * If cached data exists,
       * display it immediately.
       */
      if (cached?.data) {
        setData(cached.data)
        setLoading(false)
      } else if (!background) {
        setLoading(true)
      }

      try {
        /*
         * Existing backend API.
         * No API contract has been changed.
         */
        const res =
          await getDashboardSummary(
            rangeDays
          )

        /*
         * Replace cached data with
         * fresh backend data.
         */
        setData(res)
        setLoading(false)

        writeDashboardCache(
          user,
          rangeDays,
          res
        )
      } catch (err) {
        setLoading(false)

        /*
         * If cached data exists, keep
         * showing it instead of blanking
         * the dashboard.
         */
        if (!cached?.data) {
          toast(
            err?.message ||
              'Unable to load dashboard data.',
            'error'
          )
        }
      }
    },
    [
      getDashboardSummary,
      toast,
      user
    ]
  )

  /*
   * Load cached data first and then
   * refresh it in the background.
   */
  useEffect(() => {
    const cached =
      readDashboardCache(
        user,
        days
      )

    if (cached?.data) {
      setData(cached.data)
      setLoading(false)
    }

    loadData(days, {
      background:
        Boolean(cached?.data)
    })
  }, [
    loadData,
    days,
    user
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

      const res =
        await seedSalesData()

      toast(
        res.message,
        'success'
      )

      await loadData(days)
    } catch (err) {
      toast(
        err?.message ||
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
    setHiddenSeries((prev) => {
      const next =
        new Set(prev)

      if (next.has(label)) {
        next.delete(label)
      } else {
        next.add(label)
      }

      return next
    })
  }

  /* =========================================================
     CHART LEGEND
     ========================================================= */

  const seriesMeta = useMemo(
    () => [
      {
        label: 'Actual Sales',
        color: ACTUAL_COLOR,
        dashed: false
      },
      {
        label: 'AI Forecast',
        color: FORECAST_COLOR,
        dashed: true
      }
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
                compact: true
              }
            )
        }),
      []
    )

  /* =========================================================
     INITIAL LOADING
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
          length: 3
        }).map((_, i) => (
          <SkeletonPanel
            key={i}
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
     EMPTY DATA
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
              Upload your historical transactions
              via a CSV sheet, or seed demo data
              to preview the analytics dashboard
              and AI predictions.
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
                Go to data manager
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
    recent_transactions
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

        hidden:
          hiddenSeries.has(
            'Actual Sales'
          ),

        ...lineSeriesStyle(
          ACTUAL_COLOR
        )
      },

      {
        label: 'AI Forecast',

        data: forecastValues,

        hidden:
          hiddenSeries.has(
            'AI Forecast'
          ),

        ...lineSeriesStyle(
          FORECAST_COLOR,
          {
            dashed: true
          }
        )
      }
    ]
  }

  const historyOptions =
    baseChartOptions(
      tokens,
      {
        extend: {
          plugins: {
            legend: {
              display: false
            },

            tooltip: {
              enabled: false,
              external:
                externalTooltip
            },

            crosshair: {
              color:
                tokens.border
            }
          }
        }
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
          item.forecast ?? ''
      })
    )

  /* =========================================================
     DASHBOARD UI
     ========================================================= */

  return (
    <div className="space-y-6">

      {/* =====================================================
          KPI STRIP
          ===================================================== */}

      <Panel
        className="
          grid
          grid-cols-1
          sm:grid-cols-2
          lg:grid-cols-5
          divide-y
          sm:divide-y-0
          sm:divide-x
          divide-line
        "
      >

        {/* NET SALES */}

        <div className="p-4">

          <p className="ss-eyebrow">
            Net sales ({days}d)
          </p>

          <h3
            className="
              text-kpi
              font-semibold
              text-primary
              font-mono
              tabular-nums
              mt-1
            "
          >
            {formatCurrency(
              kpis.total_sales
            )}
          </h3>

          <div
            className="
              flex
              items-center
              justify-between
              mt-1.5
            "
          >
            <span
              className="
                text-[11px]
                text-secondary
                font-mono
                tabular-nums
              "
            >
              Avg daily:{' '}
              {formatCurrency(
                kpis.avg_daily_sales
              )}
            </span>

            <Sparkline
              data={netSalesSpark}
              color={ACTUAL_COLOR}
            />
          </div>

        </div>

        {/* AI FORECAST */}

        <div className="p-4">

          <p className="ss-eyebrow">
            AI forecast (next {days}d)
          </p>

          <h3
            className="
              text-kpi
              font-semibold
              text-primary
              font-mono
              tabular-nums
              mt-1
            "
          >
            {formatCurrency(
              kpis.forecast_sales_30d
            )}
          </h3>

          <div
            className="
              flex
              items-center
              justify-between
              mt-1.5
            "
          >

            <span
              className={`
                inline-flex
                items-center
                gap-0.5
                font-mono
                tabular-nums
                text-[11px]
                font-semibold
                ${
                  kpis.variance_pct >= 0
                    ? 'text-up'
                    : 'text-down'
                }
              `}
            >

              {kpis.variance_pct >= 0 ? (
                <ArrowUpRight
                  size={12}
                />
              ) : (
                <ArrowDownRight
                  size={12}
                />
              )}

              {Math.abs(
                kpis.variance_pct
              ).toFixed(1)}
              %

            </span>

            <Sparkline
              data={forecastSpark}
              color={
                FORECAST_COLOR
              }
            />

          </div>

        </div>

        {/* ACTIVE STORES */}

        <div
          className="
            p-4
            flex
            flex-col
            justify-between
          "
        >

          <p
            className="
              ss-eyebrow
              flex
              items-center
              gap-1.5
            "
          >
            <Store size={13} />

            Active stores
          </p>

          <h4
            className="
              text-section
              font-semibold
              text-primary
              font-mono
              tabular-nums
              mt-2
            "
          >
            {kpis.active_stores}
          </h4>

        </div>

        {/* ACTIVE PRODUCTS */}

        <div
          className="
            p-4
            flex
            flex-col
            justify-between
          "
        >

          <p
            className="
              ss-eyebrow
              flex
              items-center
              gap-1.5
            "
          >
            <ShoppingBag
              size={13}
            />

            Active products
          </p>

          <h4
            className="
              text-section
              font-semibold
              text-primary
              font-mono
              tabular-nums
              mt-2
            "
          >
            {kpis.active_products}
          </h4>

        </div>

        {/* PREDICTIONS */}

        <div
          className="
            p-4
            flex
            items-center
          "
        >

          <Link
            to="/predictions"
            className="
              text-xs
              text-slate-700
              hover:text-slate-900
              hover:underline
              font-semibold
            "
          >
            Detailed AI predictions →
          </Link>

        </div>

      </Panel>

      {/* =====================================================
          SALES OVERVIEW
          ===================================================== */}

      <Panel>

        <PanelHeader
          title="Sales overview"
          description="Actual sales vs. AI forecast"

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
                      tokens.textTertiary
                  }
                )
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
            description={`Sales share by product group (last ${days}d)`}
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

        {/* TRANSACTIONS */}

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
                <Th>Date</Th>
                <Th>Store</Th>
                <Th>Product</Th>
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
                            'short'
                        }
                      )}
                    </Td>

                    <Td>
                      {
                        transaction.store_id
                      }
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