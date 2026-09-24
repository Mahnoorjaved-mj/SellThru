import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'
import { Input, Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'

export default function Login() {
  const { login, toast } = useApp()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await login(email, password)
      toast('Welcome back!', 'success')
      navigate('/')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center justify-center gap-2">
          <div className="h-11 w-11 rounded-xl bg-deep-teal text-white flex items-center justify-center shadow-sm">
            <TrendingUp size={24} className="text-emerald-400" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xl font-bold text-primary tracking-tight">Sellthru</span>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-pale-blue text-deep-teal">
              AI
            </span>
          </div>
          <p className="text-xs text-secondary font-medium">Predictive Retail Intelligence</p>
        </div>
        <form onSubmit={submit} className="ss-card space-y-4 p-6">
          <h1 className="text-section font-semibold text-primary">Sign in</h1>
          <div>
            <Label>Email address</Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>
          <Button type="submit" size="submit" className="w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
          <div className="flex justify-between text-xs pt-1">
            <span className="text-secondary">Don't have an account?</span>
            <Link to="/register" className="text-accent font-semibold hover:underline">
              Create account
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
