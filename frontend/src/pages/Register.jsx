import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'
import { Input, Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'

function strength(pw) {
  let s = 0
  if (pw.length >= 10) s++
  if (/[A-Za-z]/.test(pw) && /\d/.test(pw)) s++
  return s // 0..2
}

const STRENGTH_CLASS = ['bg-down', 'bg-warn', 'bg-up']
const STRENGTH_TEXT_CLASS = ['text-down', 'text-warn', 'text-up']

export default function Register() {
  const { register, verifyOtp, toast } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [busy, setBusy] = useState(false)

  const s = strength(password)
  const strengthLabel = ['Too weak', 'Weak', 'Strong'][s]

  const submitStep1 = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await register(email, password, name)
      toast('OTP verification code sent to your email', 'success')
      setStep(2)
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const submitStep2 = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await verifyOtp(email, otp)
      toast('Account created successfully!', 'success')
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

        {step === 1 ? (
          <form onSubmit={submitStep1} className="ss-card space-y-4 p-6">
            <h1 className="text-section font-semibold text-primary">Create your account</h1>
            <div>
              <Label>Full name</Label>
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
              />
            </div>
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
              {password && (
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-1 flex-1 rounded bg-surface-hover">
                    <div
                      className={`h-1 rounded transition-colors duration-120 ease-out ${STRENGTH_CLASS[s]}`}
                      style={{ width: `${(s / 2) * 100}%` }}
                    />
                  </div>
                  <span className={`text-[10px] font-semibold ${STRENGTH_TEXT_CLASS[s]}`}>{strengthLabel}</span>
                </div>
              )}
            </div>
            <Button type="submit" size="submit" className="w-full" disabled={busy}>
              {busy ? 'Sending OTP…' : 'Continue'}
            </Button>
            <div className="text-center text-xs pt-1">
              <Link to="/login" className="text-secondary hover:text-primary transition-colors duration-120 ease-out">
                Already have an account? <span className="text-accent font-semibold hover:underline">Sign in</span>
              </Link>
            </div>
          </form>
        ) : (
          <form onSubmit={submitStep2} className="ss-card space-y-4 p-6">
            <h1 className="text-section font-semibold text-primary">Verify your email</h1>
            <p className="text-body text-secondary leading-relaxed">
              We sent a 6-digit verification code to <span className="text-primary font-semibold">{email}</span>. Please enter it below.
            </p>
            <Input
              className="text-center text-lg tracking-[0.3em] font-semibold font-mono"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              required
            />
            <Button type="submit" size="submit" className="w-full" disabled={busy}>
              {busy ? 'Verifying…' : 'Verify & create account'}
            </Button>
            <button
              type="button"
              className="w-full text-center text-xs text-secondary hover:text-primary transition-colors duration-120 ease-out font-medium"
              onClick={() => setStep(1)}
            >
              Back to registration
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
