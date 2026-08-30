import { useEffect, useState, useCallback } from 'react'
import { Trash2 } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Table, Th, Td } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'

export default function Stores() {
  const { getStores, updateStore, deleteStore, toast } = useApp()
  const [stores, setStores] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getStores()
      setStores(res.stores || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getStores, toast])

  useEffect(() => {
    load()
  }, [load])

  const handleRegionBlur = async (oid, value) => {
    try {
      await updateStore(oid, { region: value })
      toast('Store updated', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleToggleActive = async (oid, is_active) => {
    try {
      await updateStore(oid, { is_active: !is_active })
      setStores((prev) => prev.map((s) => (s.id === oid ? { ...s, is_active: !is_active } : s)))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleDelete = async (oid) => {
    try {
      await deleteStore(oid)
      setStores((prev) => prev.filter((s) => s.id !== oid))
      toast('Store deleted', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader
          title="Stores"
          description="Master list of store locations, auto-registered from CSV imports."
        />
        {loading ? (
          <div className="p-4"><SkeletonPanel rows={5} /></div>
        ) : stores.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>Store code</Th>
                <Th>Region</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {stores.map((s) => (
                <tr key={s.id}>
                  <Td className="font-semibold text-accent">{s.store_id}</Td>
                  <Td>
                    <Input
                      defaultValue={s.region ?? ''}
                      placeholder="—"
                      className="w-32 h-7"
                      onBlur={(e) => handleRegionBlur(s.id, e.target.value)}
                    />
                  </Td>
                  <Td>
                    <button onClick={() => handleToggleActive(s.id, s.is_active)}>
                      <Badge variant={s.is_active ? 'positive' : 'neutral'}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </button>
                  </Td>
                  <Td>
                    <Button variant="ghost" size="compact" onClick={() => handleDelete(s.id)}>
                      <Trash2 size={12} />
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <div className="p-4">
            <EmptyState title="No stores yet" description="Stores are auto-registered the first time they appear in an uploaded CSV." />
          </div>
        )}
      </Panel>
    </div>
  )
}
