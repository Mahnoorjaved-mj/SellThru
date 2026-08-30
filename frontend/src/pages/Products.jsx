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

export default function Products() {
  const { getProducts, updateProduct, deleteProduct, toast } = useApp()
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getProducts()
      setProducts(res.products || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getProducts, toast])

  useEffect(() => {
    load()
  }, [load])

  const handlePriceBlur = async (oid, value) => {
    const unit_price = parseFloat(value)
    if (Number.isNaN(unit_price)) return
    try {
      await updateProduct(oid, { unit_price })
      toast('Product updated', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleToggleActive = async (oid, is_active) => {
    try {
      await updateProduct(oid, { is_active: !is_active })
      setProducts((prev) => prev.map((p) => (p.id === oid ? { ...p, is_active: !is_active } : p)))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleDelete = async (oid) => {
    try {
      await deleteProduct(oid)
      setProducts((prev) => prev.filter((p) => p.id !== oid))
      toast('Product deleted', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader
          title="Products"
          description="Master list of product SKUs, auto-registered from CSV imports. Edit price and category, or deactivate a discontinued SKU."
        />
        {loading ? (
          <div className="p-4"><SkeletonPanel rows={5} /></div>
        ) : products.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>SKU</Th>
                <Th>Category</Th>
                <Th numeric>Unit price</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <Td className="font-semibold text-accent">{p.product_id}</Td>
                  <Td>{p.category || '—'}</Td>
                  <Td numeric>
                    <Input
                      type="number"
                      numeric
                      defaultValue={p.unit_price ?? ''}
                      placeholder="—"
                      className="w-24 h-7 text-right"
                      onBlur={(e) => handlePriceBlur(p.id, e.target.value)}
                    />
                  </Td>
                  <Td>
                    <button onClick={() => handleToggleActive(p.id, p.is_active)}>
                      <Badge variant={p.is_active ? 'positive' : 'neutral'}>
                        {p.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </button>
                  </Td>
                  <Td>
                    <Button variant="ghost" size="compact" onClick={() => handleDelete(p.id)}>
                      <Trash2 size={12} />
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <div className="p-4">
            <EmptyState title="No products yet" description="Products are auto-registered the first time they appear in an uploaded CSV." />
          </div>
        )}
      </Panel>
    </div>
  )
}
