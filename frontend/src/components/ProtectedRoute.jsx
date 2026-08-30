import { Navigate, useLocation } from 'react-router-dom'
import { useApp } from '../context/context'

export default function ProtectedRoute({ children, admin = false }) {
  const { user, loadingAuth } = useApp()
  const location = useLocation()

  if (loadingAuth) {
    return (
      <div className="flex h-screen items-center justify-center text-secondary font-medium">Loading auth state...</div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (admin && !user.is_admin) {
    return <Navigate to="/" replace />
  }
  return children
}
