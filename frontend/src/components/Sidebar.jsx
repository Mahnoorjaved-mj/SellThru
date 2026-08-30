import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Database,
  Package,
  Store as StoreIcon,
  BrainCircuit,
  Target,
  FlaskConical,
  FileSpreadsheet,
  Bell,
  TrendingUp,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings as SettingsIcon,
  ShieldCheck,
} from 'lucide-react'
import { useApp } from '../context/context'

const GROUPS = [
  { label: 'Overview', items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }] },
  {
    label: 'Data',
    items: [
      { to: '/data', label: 'Transactions', icon: Database, end: true },
      { to: '/data/products', label: 'Products', icon: Package },
      { to: '/data/stores', label: 'Stores', icon: StoreIcon },
    ],
  },
  {
    label: 'Forecasting',
    items: [
      { to: '/predictions', label: 'AI Predictions', icon: BrainCircuit },
      { to: '/scenarios', label: 'Scenarios', icon: FlaskConical },
      { to: '/accuracy', label: 'Accuracy', icon: Target },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/insights', label: 'AI Insights', icon: FileSpreadsheet },
      { to: '/alerts', label: 'Alerts', icon: Bell },
    ],
  },
  {
    label: 'Settings',
    items: [{ to: '/settings', label: 'Profile & security', icon: SettingsIcon }],
  },
]

const ADMIN_GROUP = { label: 'Admin', items: [{ to: '/admin', label: 'Admin panel', icon: ShieldCheck }] }

function LinkItem({ to, label, icon: Icon, end, collapsed, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium transition-colors duration-120 ease-out ${
          collapsed ? 'justify-center px-2' : ''
        } ${
          isActive
            ? 'bg-accent-soft text-accent'
            : 'text-secondary hover:bg-surface-hover hover:text-primary'
        }`
      }
    >
      <Icon size={18} className="flex-shrink-0" />
      {!collapsed && label}
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
    <aside className={`flex h-full flex-col border-r border-line bg-surface ${collapsed ? 'w-14' : 'w-60'}`}>
      {/* Brand */}
      <div className={`flex items-center gap-2 border-b border-line py-5 ${collapsed ? 'justify-center px-2' : 'px-5'}`}>
        <TrendingUp className="text-accent flex-shrink-0" size={22} />
        {!collapsed && <span className="text-base font-semibold text-primary tracking-tight">Sellthru</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {(user?.is_admin ? [...GROUPS, ADMIN_GROUP] : GROUPS).map((group) => (
          <div key={group.label}>
            {!collapsed && <div className="ss-eyebrow px-3 pb-2">{group.label}</div>}
            <div className="space-y-1">
              {group.items.map((item) => (
                <LinkItem key={item.to} {...item} collapsed={collapsed} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={toggleCollapsed}
        className="hidden md:flex items-center gap-2 px-3 py-2 mx-2 mb-1 rounded text-xs font-medium text-tertiary hover:bg-surface-hover hover:text-primary transition-colors duration-120 ease-out"
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        {!collapsed && 'Collapse'}
      </button>

      {/* User footer */}
      {user && (
        <div className="border-t border-line p-3 flex flex-col gap-2 bg-bg-muted">
          <div className={`flex items-center gap-3 px-2 py-1.5 ${collapsed ? 'justify-center px-0' : ''}`}>
            <div className="h-8 w-8 flex-shrink-0 rounded-full bg-accent-soft text-accent flex items-center justify-center font-semibold text-sm">
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
            className={`flex items-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium text-secondary hover:bg-surface-hover hover:text-primary transition-colors duration-120 ease-out ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            <LogOut size={15} />
            {!collapsed && <span>Log out</span>}
          </button>
        </div>
      )}
    </aside>
  )
}
