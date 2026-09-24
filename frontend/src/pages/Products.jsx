import { useEffect, useState, useCallback } from 'react'
import { Trash2, Search, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Table, Th, Td } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { SkeletonPanel } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'

export default function Products() {
  const { getProducts, updateProduct, deleteProduct, toast } = useApp()
  const [products, setProducts] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [limit] = useState(50)
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getProducts({ page, limit, search: searchQuery || undefined })
      setProducts(res.products || [])
      setTotal(res.total ?? (res.products?.length || 0))
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [getProducts, page, limit, searchQuery, toast])

  useEffect(() => {
    load()
  }, [load])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    setSearchQuery(searchInput.trim())
  }

  const handleClearSearch = () => {
    setSearchInput('')
    setSearchQuery('')
    setPage(1)
  }

  const totalPages = Math.ceil(total / limit)

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
          title="Products Catalog"
          description="Master list of product SKUs. Search by SKU or category across the inventory."
          actions={
            <span className="text-xs text-secondary font-mono">
              Total: <strong className="text-primary">{total.toLocaleString()}</strong> SKUs
            </span>
          }
        />

        <div className="p-4 border-b border-line bg-surface">
          <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-md">
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by SKU code or category..."
              className="h-8 text-xs"
            />
            <Button type="submit" size="compact" className="font-semibold">
              <Search size={13} />
              <span>Search</span>
            </Button>
            {searchQuery && (
              <Button type="button" variant="ghost" size="compact" onClick={handleClearSearch}>
                <X size={13} />
                <span>Clear</span>
              </Button>
            )}
          </form>
        </div>

        {loading ? (
          <div className="p-4"><SkeletonPanel rows={5} /></div>
        ) : products.length > 0 ? (
          <>
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
                    <Td className="font-semibold text-accent font-mono text-xs">{p.product_id}</Td>
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

            {totalPages > 1 && (
              <div className="flex justify-between items-center p-4 border-t border-line">
                <span className="text-xs text-secondary">
                  Showing page <span className="font-semibold text-primary font-mono">{page}</span> of{' '}
                  <span className="font-semibold text-primary font-mono">{totalPages}</span> ({total.toLocaleString()} products)
                </span>

                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="compact"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft size={14} />
                    <span>Prev</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="compact"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <span>Next</span>
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="p-4">
            <EmptyState
              title={searchQuery ? 'No matching products found' : 'No products yet'}
              description={searchQuery ? `No SKU or category matched "${searchQuery}".` : 'Products are auto-registered the first time they appear in an uploaded CSV.'}
            />
          </div>
        )}
      </Panel>
    </div>
  )
}
