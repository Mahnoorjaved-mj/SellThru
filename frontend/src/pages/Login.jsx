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
        <div className="mb-6 flex items-center justify-center gap-2">
          <TrendingUp className="text-accent" size={24} />
          <span className="text-page font-semibold text-primary tracking-tight">Sellthru</span>
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
