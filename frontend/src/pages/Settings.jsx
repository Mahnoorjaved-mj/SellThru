import { useEffect, useState, useCallback } from 'react'
import { User, Lock, ShieldCheck, Monitor, Copy } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Input, Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { formatDate } from '../lib/format'

export default function Settings() {
  const {
    user, refreshMe, updateProfile, changePassword,
    twoFaSetup, twoFaVerify, twoFaDisable,
    getSessions, revokeSession, logoutAllSessions, toast,
  } = useApp()

  const [name, setName] = useState(user?.name || '')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [twoFa, setTwoFa] = useState(null) // { secret, otpauth, recovery_codes }
  const [twoFaCode, setTwoFaCode] = useState('')
  const [sessions, setSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(true)

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true)
    try {
      const res = await getSessions()
      setSessions(res.sessions || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoadingSessions(false)
    }
  }, [getSessions, toast])

  useEffect(() => { loadSessions() }, [loadSessions])

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    try {
      await updateProfile({ name })
      await refreshMe()
      toast('Profile updated', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    try {
      const res = await changePassword(oldPassword, newPassword)
      toast(res.message, 'success')
      setOldPassword('')
      setNewPassword('')
      await loadSessions()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleStart2FA = async () => {
    try {
      const res = await twoFaSetup()
      setTwoFa(res)
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleVerify2FA = async (e) => {
    e.preventDefault()
    try {
      await twoFaVerify(twoFaCode)
      toast('2FA enabled', 'success')
      setTwoFaCode('')
      await refreshMe()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleDisable2FA = async () => {
    try {
      await twoFaDisable()
      toast('2FA disabled', 'success')
      setTwoFa(null)
      await refreshMe()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleRevokeSession = async (id) => {
    try {
      await revokeSession(id)
      setSessions((prev) => prev.filter((s) => s.id !== id))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleLogoutAll = async () => {
    try {
      await logoutAllSessions()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <Panel>
        <PanelHeader title="Profile" description={<><User size={12} className="inline mr-1" />{user?.email}</>} />
        <PanelBody>
          <form onSubmit={handleSaveProfile} className="flex items-end gap-3">
            <div className="flex-1">
              <Label>Full name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <Button type="submit" size="submit">Save</Button>
          </form>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader title="Password" description={<><Lock size={12} className="inline mr-1" />Changing your password signs out every other session.</>} />
        <PanelBody>
          <form onSubmit={handleChangePassword} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <div>
              <Label>Current password</Label>
              <Input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required />
            </div>
            <div>
              <Label>New password</Label>
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            </div>
            <Button type="submit" size="submit">Change password</Button>
          </form>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader title="Two-factor authentication" description={<><ShieldCheck size={12} className="inline mr-1" />Adds a TOTP code requirement at login.</>} />
        <PanelBody>
          {!twoFa ? (
            <Button variant="secondary" onClick={handleStart2FA}>Set up 2FA</Button>
          ) : (
            <div className="space-y-3">
              <div className="p-3 bg-bg border border-line rounded">
                <p className="text-xs text-secondary mb-1">Add this secret to your authenticator app (Google Authenticator, Authy, etc.):</p>
                <p className="font-mono text-sm font-semibold text-primary break-all">{twoFa.secret}</p>
              </div>
              {twoFa.recovery_codes && (
                <div className="p-3 bg-warn-soft border border-warn/30 rounded">
                  <p className="text-xs font-semibold text-warn mb-2">Save these recovery codes now — shown only once:</p>
                  <div className="grid grid-cols-2 gap-1 font-mono text-xs text-primary">
                    {twoFa.recovery_codes.map((c) => <span key={c}>{c}</span>)}
                  </div>
                </div>
              )}
              <form onSubmit={handleVerify2FA} className="flex items-end gap-3">
                <div>
                  <Label>Enter code from your app to confirm</Label>
                  <Input value={twoFaCode} onChange={(e) => setTwoFaCode(e.target.value.replace(/\D/g, ''))} maxLength={6} className="w-32 font-mono" />
                </div>
                <Button type="submit" size="submit">Confirm & enable</Button>
              </form>
            </div>
          )}
          {user?.is_2fa_enabled && (
            <Button variant="danger" size="compact" className="mt-3" onClick={handleDisable2FA}>Disable 2FA</Button>
          )}
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          title="Active sessions"
          description={<><Monitor size={12} className="inline mr-1" />Devices currently signed in via refresh token.</>}
          actions={sessions.length > 1 && <Button variant="ghost" size="compact" onClick={handleLogoutAll}>Sign out all</Button>}
        />
        {loadingSessions ? (
          <PanelBody><SkeletonPanel rows={2} /></PanelBody>
        ) : (
          <div className="divide-y divide-line">
            {sessions.map((s) => (
              <div key={s.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">{s.user_agent || 'Unknown device'}</p>
                  <p className="text-xs text-secondary">{s.ip || 'Unknown IP'} · signed in {formatDate(s.created_at, { dateStyle: 'short', timeStyle: 'short' })}</p>
                </div>
                <Button variant="ghost" size="compact" onClick={() => handleRevokeSession(s.id)}>Revoke</Button>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}
