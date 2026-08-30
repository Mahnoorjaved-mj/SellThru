import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from 'react'
import { ToastViewport } from '../components/ui/Toast'

const AppContext = createContext(null)
export const useApp = () => useContext(AppContext)

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'sf_token'
const REFRESH_KEY = 'sf_refresh_token'
const NO_REFRESH_PATHS = new Set(['/auth/login', '/auth/register', '/auth/verify-otp', '/auth/refresh'])

function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}
function setTokens(token, refreshToken) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
  else localStorage.removeItem(REFRESH_KEY)
}

// Concurrent 401s should trigger only one refresh call, not one per request.
let refreshInFlight = null

async function trySilentRefresh() {
  const rt = getRefreshToken()
  if (!rt) return false
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
      .then(async (res) => {
        if (!res.ok) return false
        const data = await res.json()
        setTokens(data.token, data.refresh_token)
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

// ---- Low-level request helper ----
async function request(method, path, body, { raw = false, _retried = false } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const opts = { method, headers }
  if (body !== undefined) {
    if (body instanceof FormData) {
      opts.body = body
      // Browser will set Content-Type with multipart boundaries
    } else {
      headers['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    }
  }

  const res = await fetch(`${API_BASE}${path}`, opts)

  if (res.status === 401) {
    const canRetry = !_retried && !NO_REFRESH_PATHS.has(path)
    if (canRetry && (await trySilentRefresh())) {
      return request(method, path, body, { raw, _retried: true })
    }
    setTokens(null, null)
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }
  if (raw) return res

  let data = null
  const ct = res.headers.get('content-type') || ''
  data = ct.includes('application/json') ? await res.json() : await res.text()

  if (!res.ok) {
    // New envelope: { error: { code, message, details, request_id } }. Legacy: { detail }.
    const msg =
      (data && data.error && typeof data.error === 'object' ? data.error.message : null) ||
      (data && (data.detail || data.message || data.error)) ||
      `Request failed (${res.status})`
    const err = new Error(typeof msg === 'string' ? msg : 'Request failed')
    err.code = data && data.error && typeof data.error === 'object' ? data.error.code : undefined
    err.requestId = data && data.error && typeof data.error === 'object' ? data.error.request_id : undefined
    throw err
  }
  return data
}

let toastSeq = 0

export function AppProvider({ children }) {
  // ---- Toasts ----
  const [toasts, setToasts] = useState([])
  const dismissToast = useCallback((id) => setToasts((l) => l.filter((t) => t.id !== id)), [])
  const toast = useCallback(
    (message, type = 'info') => {
      const id = ++toastSeq
      setToasts((l) => [...l, { id, message, type }])
      setTimeout(() => dismissToast(id), 3500)
    },
    [dismissToast]
  )

  // ---- Auth State ----
  const [user, setUser] = useState(null)
  const [loadingAuth, setLoadingAuth] = useState(true)

  useEffect(() => {
    let active = true
    async function hydrate() {
      if (!getToken()) {
        setLoadingAuth(false)
        return
      }
      try {
        const res = await request('GET', '/auth/me')
        if (active) setUser(res.user)
      } catch {
        setTokens(null, null)
        if (active) setUser(null)
      } finally {
        if (active) setLoadingAuth(false)
      }
    }
    hydrate()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const onUnauth = () => setUser(null)
    window.addEventListener('auth:unauthorized', onUnauth)
    return () => window.removeEventListener('auth:unauthorized', onUnauth)
  }, [])

  // ---- API endpoints wrapper ----
  const api = useMemo(() => {
    const applyToken = (res) => {
      setTokens(res.token, res.refresh_token)
      setUser(res.user)
      return res.user
    }
    return {
      // Auth
      login: async (email, password) => applyToken(await request('POST', '/auth/login', { email, password })),
      register: (email, password, name) => request('POST', '/auth/register', { email, password, name }),
      verifyOtp: async (email, otp) => applyToken(await request('POST', '/auth/verify-otp', { email, otp })),
      forgotPassword: (email) => request('POST', '/auth/forgot-password', { email }),
      resetPassword: (token, password) => request('POST', '/auth/reset-password', { token, password }),
      logout: async () => {
        try {
          await request('POST', '/auth/logout', {})
        } catch { /* ignore */ }
        setTokens(null, null)
        setUser(null)
      },
      refreshMe: async () => {
        const res = await request('GET', '/auth/me')
        setUser(res.user)
        return res.user
      },
      // 2FA
      twoFaSetup: () => request('POST', '/auth/2fa/setup', {}),
      twoFaVerify: (code) => request('POST', '/auth/2fa/verify', { code }),
      twoFaDisable: () => request('POST', '/auth/2fa/disable', {}),
      twoFaRecovery: (code) => request('POST', '/auth/2fa/recovery', { code }),
      changePassword: (old_password, new_password) => request('POST', '/auth/change-password', { old_password, new_password }),
      updateProfile: (fields) => request('PATCH', '/auth/profile', fields),

      // Sessions
      getSessions: () => request('GET', '/auth/sessions'),
      revokeSession: (id) => request('POST', `/auth/sessions/${id}/revoke`, {}),
      logoutAllSessions: async () => {
        await request('POST', '/auth/logout-all', {})
        setTokens(null, null)
        setUser(null)
      },

      // Sales Data
      getDashboardSummary: (days) => request('GET', `/api/sales/summary${days ? `?days=${days}` : ''}`),
      getSalesHistory: (params = {}) => {
        const q = new URLSearchParams()
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== '') q.append(k, v)
        })
        return request('GET', `/api/sales/history?${q.toString()}`)
      },
      uploadSalesCsv: (formData) => request('POST', '/api/sales/upload', formData),
      seedSalesData: () => request('POST', '/api/sales/seed', {}),
      getImportHistory: () => request('GET', '/api/sales/imports'),
      undoImport: (importId) => request('POST', `/api/sales/imports/${importId}/undo`, {}),

      // Catalog (products/stores)
      getProducts: () => request('GET', '/api/catalog/products'),
      updateProduct: (oid, fields) => request('PATCH', `/api/catalog/products/${oid}`, fields),
      deleteProduct: (oid) => request('DELETE', `/api/catalog/products/${oid}`),
      getStores: () => request('GET', '/api/catalog/stores'),
      updateStore: (oid, fields) => request('PATCH', `/api/catalog/stores/${oid}`, fields),
      deleteStore: (oid) => request('DELETE', `/api/catalog/stores/${oid}`),

      // AI Forecasting
      getPredictions: (params = {}) => {
        const q = new URLSearchParams()
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== '') q.append(k, v)
        })
        return request('GET', `/api/forecast/predictions?${q.toString()}`)
      },
      trainModel: () => request('POST', '/api/forecast/train', {}),
      getModels: () => request('GET', '/api/forecast/models'),
      promoteModel: (modelId) => request('POST', `/api/forecast/models/${modelId}/promote`, {}),

      // AI Insights
      getAnomalies: (sensitivity = 'medium') => request('GET', `/api/insights/anomalies?sensitivity=${sensitivity}`),
      acknowledgeAnomaly: (store_id, product_id, date) => request('POST', '/api/insights/anomalies/acknowledge', { store_id, product_id, date }),
      getTrends: () => request('GET', '/api/insights/trends'),

      // Alerts
      getAlertRules: () => request('GET', '/api/alerts/rules'),
      createAlertRule: (rule) => request('POST', '/api/alerts/rules', rule),
      enableAlertRule: (id) => request('POST', `/api/alerts/rules/${id}/enable`, {}),
      disableAlertRule: (id) => request('POST', `/api/alerts/rules/${id}/disable`, {}),
      deleteAlertRule: (id) => request('DELETE', `/api/alerts/rules/${id}`),
      evaluateAlertRules: () => request('POST', '/api/alerts/evaluate', {}),
      getNotifications: () => request('GET', '/api/alerts/notifications'),
      markNotificationRead: (id) => request('POST', `/api/alerts/notifications/${id}/read`, {}),
      markAllNotificationsRead: () => request('POST', '/api/alerts/notifications/read-all', {}),

      // Admin
      getAdminOverview: () => request('GET', '/api/admin/overview'),
      getAdminUsers: () => request('GET', '/api/admin/users'),
      changeUserRole: (userId, role) => request('POST', `/api/admin/users/${userId}/role`, { role }),
      suspendUser: (userId) => request('POST', `/api/admin/users/${userId}/suspend`, {}),
      reactivateUser: (userId) => request('POST', `/api/admin/users/${userId}/reactivate`, {}),
      getAuditLog: () => request('GET', '/api/admin/audit-log'),
      getJobs: () => request('GET', '/api/admin/jobs')
    }
  }, [])

  const value = {
    user,
    loadingAuth,
    isAuthed: !!user,
    toast,
    ...api,
  }

  return (
    <AppContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </AppContext.Provider>
  )
}
