import { useNavigate } from 'react-router-dom'
import { Menu, Database, LogIn } from 'lucide-react'
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
    <header className="flex h-14 items-center justify-between border-b border-line bg-surface px-4 md:px-6 shadow-xs">
      <div className="flex items-center gap-3">
        <button
          className="md:hidden p-1.5 rounded-md text-secondary hover:bg-surface-hover hover:text-primary transition-colors duration-120 ease-out"
          onClick={onMenuClick}
        >
          <Menu size={20} />
        </button>

        <div className="hidden sm:flex items-center gap-2.5">
          <span className="text-xs font-semibold text-primary">Sellthru Platform</span>
          <span className="text-tertiary">/</span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-soft-green text-emerald-green border border-emerald-green/20 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-green animate-pulse" />
            Live Analytics
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {isDbEmpty && user?.is_admin && (
          <Button
            variant="primary"
            size="compact"
            onClick={handleSeedData}
            className="bg-emerald-green hover:bg-emerald-700 text-white font-medium"
          >
            <Database size={13} />
            <span>Seed Demo Data</span>
          </Button>
        )}

        <ThemeToggle />

        {!user && (
          <Button variant="ghost" size="compact" onClick={() => navigate('/login')}>
            <LogIn size={14} />
            <span>Login</span>
          </Button>
        )}
      </div>
    </header>
  )
}
