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
      { to: '/accuracy', label: 'Forecast Accuracy', icon: Target },
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
    items: [{ to: '/settings', label: 'Profile & Security', icon: SettingsIcon }],
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
        `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-120 ease-out ${
          collapsed ? 'justify-center px-2' : ''
        } ${
          isActive
            ? 'bg-light-aqua text-deep-teal font-semibold shadow-sm border-l-[3px] border-emerald-green dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-400'
            : 'text-secondary hover:bg-surface-hover hover:text-primary'
        }`
      }
    >
      <Icon size={18} className="flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
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
    <aside className={`flex h-full flex-col border-r border-line bg-surface transition-all duration-200 ${collapsed ? 'w-16' : 'w-64'}`}>
      {/* Brand Header */}
      <div className={`flex items-center border-b border-line py-4 ${collapsed ? 'justify-center px-2' : 'justify-between px-4'}`}>
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-deep-teal text-white flex items-center justify-center shadow-sm flex-shrink-0">
            <TrendingUp size={20} className="text-emerald-400" />
          </div>
          {!collapsed && (
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-base font-bold text-primary tracking-tight">Sellthru</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-pale-blue text-deep-teal dark:bg-emerald-950 dark:text-emerald-300">
                  AI
                </span>
              </div>
              <p className="text-[11px] text-secondary font-medium">Retail Demand Intelligence</p>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {(user?.is_admin ? [...GROUPS, ADMIN_GROUP] : GROUPS).map((group) => (
          <div key={group.label} className="space-y-1">
            {!collapsed && (
              <div className="text-[10px] font-bold uppercase tracking-wider text-tertiary px-3 pb-1">
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <LinkItem key={item.to} {...item} collapsed={collapsed} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* AI Pulse Status Widget */}
      {!collapsed && (
        <div className="mx-3 mb-2 p-2.5 rounded-lg bg-soft-green/40 border border-soft-green flex items-center gap-2.5 dark:bg-emerald-950/20 dark:border-emerald-800">
          <span className="relative flex h-2 w-2 flex-shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-green"></span>
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1">
              <Sparkles size={11} className="text-emerald-green" />
              <p className="text-[11px] font-semibold text-deep-teal dark:text-emerald-300 leading-none">Forecast Engine</p>
            </div>
            <p className="text-[10px] text-secondary leading-tight mt-0.5 truncate">Continuous models active</p>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={toggleCollapsed}
        className="hidden md:flex items-center gap-2 px-3 py-2 mx-3 mb-2 rounded-md text-xs font-medium text-secondary hover:bg-surface-hover hover:text-primary transition-colors duration-120 ease-out"
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        {!collapsed && <span>Collapse Sidebar</span>}
      </button>

      {/* User footer */}
      {user && (
        <div className="border-t border-line p-3 bg-app/50">
          <div className={`flex items-center gap-2.5 px-1 py-1 ${collapsed ? 'justify-center px-0' : ''}`}>
            <div className="h-8 w-8 flex-shrink-0 rounded-full bg-deep-teal text-white flex items-center justify-center font-bold text-xs ring-2 ring-light-aqua dark:ring-emerald-800">
              {user.name ? user.name[0].toUpperCase() : user.email[0].toUpperCase()}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-primary truncate">{user.name || 'User'}</p>
                <p className="text-[11px] text-secondary truncate">{user.email}</p>
              </div>
            )}
          </div>

          <button
            onClick={handleLogout}
            title="Log out"
            className={`mt-2 flex w-full items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-secondary hover:bg-coral-orange/10 hover:text-coral-orange transition-colors duration-120 ease-out ${
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
