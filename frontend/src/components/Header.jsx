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
    <header className="flex h-12 items-center justify-between border-b border-line bg-surface px-4 md:px-6">
      <div className="flex items-center gap-3">
        <button className="md:hidden text-secondary hover:text-primary transition-colors duration-120 ease-out" onClick={onMenuClick}>
          <Menu size={20} />
        </button>
        <span className="hidden md:inline ss-badge bg-surface-hover text-secondary">
          v1.0
        </span>
      </div>

      <div className="flex items-center gap-3">
        {isDbEmpty && user?.is_admin && (
          <Button variant="secondary" size="compact" onClick={handleSeedData}>
            <Database size={13} />
            <span>Seed demo data</span>
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
