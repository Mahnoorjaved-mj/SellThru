import { useNavigate } from 'react-router-dom'
import { Menu, Database, LogIn, Search, Command } from 'lucide-react'
import { useApp } from '../context/context'
import { ThemeToggle } from './ui/ThemeToggle'
import { Button } from './ui/Button'

export default function Header({ onMenuClick, isDbEmpty, onSeedSuccess }) {
  const { user, toast, seedSalesData } = useApp()
  const navigate = useNavigate()

  const handleSeedData = async () => {
    try {
      toast('Seeding database...', 'info')
      const res = await seedSalesData()
      toast(res.message, 'success')
      if (onSeedSuccess) onSeedSuccess()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line/70 bg-surface/85 backdrop-blur-md px-4 md:px-6">
      <div className="flex items-center gap-4 flex-1 max-w-xl">
        <button
          className="md:hidden p-1.5 rounded-lg text-secondary hover:bg-surface-hover hover:text-primary transition-colors duration-150 ease-out"
          onClick={onMenuClick}
        >
          <Menu size={20} />
        </button>

        {/* Quick Search Bar */}
        <div className="hidden sm:flex items-center gap-2 flex-1 max-w-sm rounded-lg bg-app/80 border border-line/70 px-3 py-1.5 text-xs text-secondary hover:border-line-strong transition-colors cursor-pointer shadow-xs">
          <Search size={14} className="text-tertiary flex-shrink-0" />
          <span className="flex-1 truncate">Search metrics, forecasts, products...</span>
          <span className="flex items-center gap-0.5 rounded border border-line/70 bg-surface px-1.5 py-0.5 text-[10px] font-medium text-tertiary shadow-2xs">
            <Command size={10} /> K
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Live Status Pill */}
        <div className="hidden lg:flex items-center gap-2 rounded-full border border-emerald-500/25 bg-soft-green/50 px-3 py-1 text-xs font-semibold text-emerald-green dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-green"></span>
          </span>
          <span>Live Sync</span>
        </div>

        {isDbEmpty && user?.is_admin && (
          <Button
            variant="emerald"
            size="compact"
            onClick={handleSeedData}
            className="font-semibold shadow-xs"
          >
            <Database size={13} />
            <span>Seed Demo Data</span>
          </Button>
        )}

        <ThemeToggle />

        {!user && (
          <Button variant="ghost" size="compact" onClick={() => navigate('/login')}>
            <LogIn size={14} />
            <span>Sign in</span>
          </Button>
        )}
      </div>
    </header>
  )
}
