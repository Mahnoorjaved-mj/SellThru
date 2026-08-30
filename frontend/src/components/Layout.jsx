import { useEffect, useState, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import { useApp } from '../context/context'

export default function Layout() {
  const { isAuthed, getDashboardSummary } = useApp()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isDbEmpty, setIsDbEmpty] = useState(false)

  const checkDbStatus = useCallback(async () => {
    if (!isAuthed) return
    try {
      const res = await getDashboardSummary()
      setIsDbEmpty(res.status === 'empty')
    } catch {
      setIsDbEmpty(false)
    }
  }, [isAuthed, getDashboardSummary])

  useEffect(() => {
    checkDbStatus()
  }, [checkDbStatus])

  const handleSeedSuccess = () => {
    setIsDbEmpty(false)
    // Reload dashboard or child pages
    window.location.reload()
  }

  return (
    <div className="flex h-screen overflow-hidden bg-app">
      {/* Desktop Sidebar */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Mobile Sidebar Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-overlay" onClick={() => setDrawerOpen(false)} />
          <div className="relative h-full w-60">
            <Sidebar onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          onMenuClick={() => setDrawerOpen(true)}
          isDbEmpty={isDbEmpty}
          onSeedSuccess={handleSeedSuccess}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
