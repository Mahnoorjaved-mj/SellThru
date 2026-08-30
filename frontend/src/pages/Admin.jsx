import { useEffect, useState, useCallback } from 'react'
import { ShieldCheck } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Table, Th, Td } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import { Select } from '../components/ui/Select'
import { Button } from '../components/ui/Button'
import { Tabs } from '../components/ui/Tabs'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { formatDate } from '../lib/format'

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'users', label: 'Users' },
  { value: 'jobs', label: 'Jobs' },
  { value: 'audit', label: 'Audit log' },
]

function Overview({ data }) {
  if (!data) return null
  const { stats } = data
  return (
    <div className="space-y-6">
      <Panel className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x divide-line">
        {[
          ['Users', stats.users],
          ['Stores', stats.stores],
          ['Products', stats.products],
          ['Transactions', stats.transactions],
          ['Models trained', stats.models_trained],
          ['Active model', stats.active_model_version || '—'],
        ].map(([label, value]) => (
          <div key={label} className="p-4">
            <p className="ss-eyebrow">{label}</p>
            <p className="text-section font-semibold text-primary font-mono tabular-nums mt-1 truncate">{value}</p>
          </div>
        ))}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel>
          <PanelHeader title="Recent imports" />
          {data.recent_imports.length === 0 ? (
            <div className="p-4"><EmptyState title="No imports yet" /></div>
          ) : (
            <Table>
              <thead><tr><Th>File</Th><Th numeric>Imported</Th><Th>Status</Th></tr></thead>
              <tbody>
                {data.recent_imports.map((i) => (
                  <tr key={i.id}>
                    <Td className="font-medium">{i.filename}</Td>
                    <Td numeric>{i.rows_imported}</Td>
                    <Td><Badge variant={i.status === 'undone' ? 'neutral' : 'positive'}>{i.status}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Panel>

        <Panel>
          <PanelHeader title="Recent model versions" />
          {data.recent_models.length === 0 ? (
            <div className="p-4"><EmptyState title="No models trained yet" /></div>
          ) : (
            <Table>
              <thead><tr><Th>Version</Th><Th numeric>WAPE</Th><Th>Status</Th></tr></thead>
              <tbody>
                {data.recent_models.map((m) => (
                  <tr key={m.id}>
                    <Td className="font-mono font-medium">{m.version}</Td>
                    <Td numeric>{m.metrics?.wape ?? '—'}%</Td>
                    <Td><Badge variant={m.status === 'active' ? 'positive' : m.status === 'candidate' ? 'warning' : 'neutral'}>{m.status}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Panel>
      </div>
    </div>
  )
}

function Users({ users, onRoleChange, onSuspend, onReactivate }) {
  return (
    <Panel>
      <PanelHeader title="Users" description="Everyone in your organization." />
      {users.length === 0 ? (
        <div className="p-4"><EmptyState title="No users" /></div>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Role</Th>
              <Th>Status</Th>
              <Th>Last login</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <Td className="font-medium">{u.name || '—'}</Td>
                <Td>{u.email}</Td>
                <Td>
                  <Select value={u.role || 'user'} onChange={(e) => onRoleChange(u.id, e.target.value)} className="w-28 h-7 text-xs">
                    <option value="user">User</option>
                    <option value="analyst">Analyst</option>
                    <option value="manager">Manager</option>
                    <option value="admin">Admin</option>
                  </Select>
                </Td>
                <Td>
                  <Badge variant={u.is_suspended ? 'negative' : 'positive'}>{u.is_suspended ? 'Suspended' : 'Active'}</Badge>
                </Td>
                <Td className="text-secondary">{u.last_login_at ? formatDate(u.last_login_at, { dateStyle: 'short' }) : 'Never'}</Td>
                <Td>
                  {u.is_suspended ? (
                    <Button variant="ghost" size="compact" onClick={() => onReactivate(u.id)}>Reactivate</Button>
                  ) : (
                    <Button variant="ghost" size="compact" onClick={() => onSuspend(u.id)}>Suspend</Button>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  )
}

function Jobs({ jobs }) {
  return (
    <Panel>
      <PanelHeader title="Jobs" description="CSV imports and model training runs." />
      {jobs.length === 0 ? (
        <div className="p-4"><EmptyState title="No jobs yet" /></div>
      ) : (
        <Table>
          <thead><tr><Th>Type</Th><Th>Label</Th><Th>Detail</Th><Th>Status</Th><Th>When</Th></tr></thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={`${j.type}-${j.id}`}>
                <Td><Badge variant="accent">{j.type === 'import' ? 'Import' : 'Training'}</Badge></Td>
                <Td className="font-mono font-medium">{j.label}</Td>
                <Td className="text-secondary">{j.detail}</Td>
                <Td>{j.status}</Td>
                <Td className="whitespace-nowrap">{j.created_at ? formatDate(j.created_at, { dateStyle: 'short', timeStyle: 'short' }) : '—'}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  )
}

function AuditLog({ events }) {
  return (
    <Panel>
      <PanelHeader title="Audit log" description="Append-only record of security-relevant actions." />
      {events.length === 0 ? (
        <div className="p-4"><EmptyState title="No audit events yet" /></div>
      ) : (
        <Table>
          <thead><tr><Th>Action</Th><Th>User</Th><Th>IP</Th><Th>When</Th></tr></thead>
          <tbody>
            {events.map((e, idx) => (
              <tr key={idx}>
                <Td className="font-mono font-medium">{e.action}</Td>
                <Td className="text-secondary">{e.user_id || '—'}</Td>
                <Td className="text-secondary">{e.ip || '—'}</Td>
                <Td className="whitespace-nowrap">{formatDate(e.occurred_at, { dateStyle: 'short', timeStyle: 'short' })}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  )
}

export default function Admin() {
  const { getAdminOverview, getAdminUsers, changeUserRole, suspendUser, reactivateUser, getJobs, getAuditLog, toast } = useApp()
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState(null)
  const [users, setUsers] = useState([])
  const [jobs, setJobs] = useState([])
  const [events, setEvents] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ov, us, jb, al] = await Promise.all([getAdminOverview(), getAdminUsers(), getJobs(), getAuditLog()])
      setOverview(ov)
      setUsers(us.users || [])
      setJobs(jb.jobs || [])
      setEvents(al.events || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getAdminOverview, getAdminUsers, getJobs, getAuditLog, toast])

  useEffect(() => { load() }, [load])

  const handleRoleChange = async (userId, role) => {
    try {
      await changeUserRole(userId, role)
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role, is_admin: role === 'admin' } : u)))
      toast('Role updated', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleSuspend = async (userId) => {
    try {
      await suspendUser(userId)
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_suspended: true } : u)))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleReactivate = async (userId) => {
    try {
      await reactivateUser(userId)
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_suspended: false } : u)))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  if (loading) return <SkeletonPanel rows={6} />

  return (
    <div className="space-y-4">
      <h1 className="text-page font-semibold text-primary flex items-center gap-2">
        <ShieldCheck className="text-accent" size={20} />
        Admin
      </h1>
      <Tabs items={TABS} value={tab} onChange={setTab} />
      {tab === 'overview' && <Overview data={overview} />}
      {tab === 'users' && <Users users={users} onRoleChange={handleRoleChange} onSuspend={handleSuspend} onReactivate={handleReactivate} />}
      {tab === 'jobs' && <Jobs jobs={jobs} />}
      {tab === 'audit' && <AuditLog events={events} />}
    </div>
  )
}
