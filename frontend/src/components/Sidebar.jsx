import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Database,
  Package,
  Target,
  FileSpreadsheet,
  Bell,
  TrendingUp,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings as SettingsIcon,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react'
import { useApp } from '../context/context'

const GROUPS = [
  { label: 'Overview', items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }] },
  {
    label: 'Data Hub',
    items: [
      { to: '/data', label: 'Transactions', icon: Database, end: true },
      { to: '/data/products', label: 'Products', icon: Package },
    ],
  },
  {
    label: 'Predictive AI',
    items: [
      { to: '/accuracy', label: 'Accuracy Lab', icon: Target },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/insights', label: 'AI Insights', icon: FileSpreadsheet },
      { to: '/alerts', label: 'Alerts & Anomalies', icon: Bell },
    ],
  },
  {
    label: 'Preferences',
    items: [{ to: '/settings', label: 'Settings', icon: SettingsIcon }],
  },
]

const ADMIN_GROUP = { label: 'Administration', items: [{ to: '/admin', label: 'Admin Console', icon: ShieldCheck }] }

function LinkItem({ to, label, icon: Icon, end, collapsed, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ease-out ${
          collapsed ? 'justify-center px-2' : ''
        } ${
          isActive
            ? 'bg-gradient-to-r from-light-aqua to-light-aqua/60 text-deep-teal font-semibold shadow-xs ring-1 ring-deep-teal/10 dark:from-emerald-950/60 dark:to-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-700/30'
            : 'text-secondary hover:bg-surface-hover/70 hover:text-primary'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-emerald-green dark:bg-emerald-400" />
          )}
          <Icon
            size={18}
            className={`flex-shrink-0 transition-transform duration-150 group-hover:scale-105 ${
              isActive ? 'text-deep-teal dark:text-emerald-300' : 'text-tertiary group-hover:text-primary'
            }`}
          />
          {!collapsed && <span className="tracking-tight">{label}</span>}
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar({ onNavigate }) {
  const { user, logout, toast } = useApp()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('fiq-sidebar-collapsed') === '1')

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      localStorage.setItem('fiq-sidebar-collapsed', c ? '0' : '1')
      return !c
    })
  }

  const handleLogout = async () => {
    await logout()
    toast('Logged out successfully', 'success')
  }

  return (
    <aside
      className={`flex h-full flex-col border-r border-line/80 bg-surface/90 backdrop-blur-md transition-all duration-200 ${
        collapsed ? 'w-[70px]' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div
        className={`flex items-center border-b border-line/60 py-4.5 ${
          collapsed ? 'justify-center px-2' : 'justify-between px-5'
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-deep-teal to-[#093844] text-white shadow-sm ring-1 ring-white/15">
            <TrendingUp size={20} className="text-emerald-400" />
            <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3 items-center justify-center rounded-full bg-white ring-2 ring-surface">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-green animate-pulse" />
            </span>
          </div>
          {!collapsed && (
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-base font-bold tracking-tight text-primary">Sellthru</span>
                <span className="inline-flex items-center gap-0.5 rounded-full bg-pale-blue px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-deep-teal dark:bg-emerald-950/80 dark:text-emerald-300">
                  <Zap size={9} /> PRO
                </span>
              </div>
              <p className="text-[11px] font-medium text-secondary">Retail Demand AI</p>
            </div>
          )}
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {(user?.is_admin ? [...GROUPS, ADMIN_GROUP] : GROUPS).map((group) => (
          <div key={group.label} className="space-y-1">
            {!collapsed && (
              <div className="px-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-tertiary">
                {group.label}
              </div>
            )}
            <div className="space-y-1">
              {group.items.map((item) => (
                <LinkItem key={item.to} {...item} collapsed={collapsed} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Intelligence Pulse Widget */}
      {!collapsed && (
        <div className="mx-3 mb-3 overflow-hidden rounded-xl border border-emerald-green/20 bg-gradient-to-br from-soft-green/50 via-soft-green/20 to-transparent p-3 dark:border-emerald-800/40 dark:from-emerald-950/40 dark:via-emerald-950/20">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-green/15 text-emerald-green dark:bg-emerald-400/15 dark:text-emerald-300">
              <Sparkles size={13} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-deep-teal dark:text-emerald-300">AI Forecaster</p>
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-green" />
              </div>
              <p className="text-[10px] text-secondary">99.4% Model accuracy</p>
            </div>
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="px-3 pb-2">
        <button
          onClick={toggleCollapsed}
          className="flex w-full items-center justify-center gap-2 rounded-lg py-1.5 text-xs font-medium text-tertiary transition-colors hover:bg-surface-hover hover:text-primary"
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          {!collapsed && <span>Collapse Sidebar</span>}
        </button>
      </div>

      {/* User Footer */}
      {user && (
        <div className="border-t border-line/60 p-3 bg-app/40">
          <div className={`flex items-center gap-3 px-1 py-1 ${collapsed ? 'justify-center px-0' : ''}`}>
            <div className="relative h-9 w-9 flex-shrink-0 rounded-full bg-gradient-to-tr from-deep-teal to-[#15697d] text-white flex items-center justify-center font-bold text-xs ring-2 ring-light-aqua dark:ring-emerald-700/40 shadow-xs">
              {user.name ? user.name[0].toUpperCase() : user.email[0].toUpperCase()}
              <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-green ring-2 ring-white dark:ring-surface" />
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-primary truncate tracking-tight">{user.name || 'User'}</p>
                <p className="text-[11px] text-secondary truncate">{user.email}</p>
              </div>
            )}
          </div>

          <button
            onClick={handleLogout}
            title="Sign out"
            className={`mt-2 flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-secondary transition-all hover:bg-coral-orange/10 hover:text-coral-orange ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            <LogOut size={14} />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      )}
    </aside>
  )
}
