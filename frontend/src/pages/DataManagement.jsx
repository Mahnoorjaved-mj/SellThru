import { useEffect, useState, useCallback } from 'react'
import { Upload, Database, Search, ChevronLeft, ChevronRight, X, AlertCircle, RotateCcw } from 'lucide-react'
import { useApp } from '../context/context'
import { Panel, PanelHeader, PanelBody } from '../components/ui/Panel'
import { Select } from '../components/ui/Select'
import { Input, Label } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Table, Th, Td } from '../components/ui/Table'
import { EmptyState } from '../components/ui/EmptyState'
import { SkeletonPanel } from '../components/ui/Skeleton'

export default function DataManagement() {
  const { getSalesHistory, uploadSalesCsv, getImportHistory, undoImport, toast } = useApp()

  // Import history state
  const [importHistory, setImportHistory] = useState([])
  const [loadingImports, setLoadingImports] = useState(true)
  const [undoingId, setUndoingId] = useState(null)

  // Transactions State
  const [salesList, setSalesList] = useState([])
  const [filters, setFilters] = useState({ stores: [], products: [], categories: [] })
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [limit] = useState(15)

  // Selected Filters State
  const [selectedStore, setSelectedStore] = useState('')
  const [selectedProduct, setSelectedProduct] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // Uploading State
  const [dragActive, setDragActive] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [loadingList, setLoadingList] = useState(false)

  const fetchHistory = useCallback(async () => {
    setLoadingList(true)
    try {
      const res = await getSalesHistory({
        page,
        limit,
        store_id: selectedStore,
        product_id: selectedProduct,
        category: selectedCategory,
        start_date: startDate,
        end_date: endDate
      })
      setSalesList(res.sales || [])
      setTotal(res.total || 0)
      setFilters(res.filters || { stores: [], products: [], categories: [] })
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoadingList(false)
    }
  }, [getSalesHistory, page, limit, selectedStore, selectedProduct, selectedCategory, startDate, endDate, toast])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const fetchImports = useCallback(async () => {
    setLoadingImports(true)
    try {
      const res = await getImportHistory()
      setImportHistory(res.imports || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoadingImports(false)
    }
  }, [getImportHistory, toast])

  useEffect(() => {
    fetchImports()
  }, [fetchImports])

  const handleUndo = async (importId) => {
    setUndoingId(importId)
    try {
      const res = await undoImport(importId)
      toast(res.message, 'success')
      await Promise.all([fetchImports(), fetchHistory()])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setUndoingId(null)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchHistory()
  }

  const handleClearFilters = () => {
    setSelectedStore('')
    setSelectedProduct('')
    setSelectedCategory('')
    setStartDate('')
    setEndDate('')
    setPage(1)
  }

  // Drag-and-Drop Handlers
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.name.endsWith('.csv')) {
        setUploadFile(file)
      } else {
        toast('Please upload only CSV files', 'error')
      }
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0])
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!uploadFile) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', uploadFile)

    try {
      toast('Uploading CSV sheet...', 'info')
      const res = await uploadSalesCsv(formData)
      toast(res.message, res.rows_failed > 0 ? 'warn' : 'success')
      setUploadFile(null)
      setPage(1)
      fetchHistory()
      fetchImports()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setUploading(false)
    }
  }

  const totalPages = Math.ceil(total / limit)
  const hasActiveFilters = selectedStore || selectedProduct || selectedCategory || startDate || endDate

  return (
    <div className="space-y-6">
      {/* Upper Grid: Upload Box + Documentation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel className="lg:col-span-2 flex flex-col justify-between">
          <PanelHeader title="CSV sales uploader" description="Add new retail transactions to the analytical database using a structured CSV file." />
          <PanelBody>
            <form
              onSubmit={handleUpload}
              onDragEnter={handleDrag}
              className="flex flex-col items-center justify-center border-2 border-dashed border-line rounded p-6 hover:border-accent/50 transition-colors duration-120 ease-out bg-bg relative min-h-[160px]"
            >
              {dragActive && (
                <div
                  className="absolute inset-0 z-10 w-full h-full bg-accent-soft rounded border-2 border-accent border-dashed"
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                />
              )}

              <input
                type="file"
                id="csv-file-input"
                className="hidden"
                accept=".csv"
                onChange={handleFileChange}
              />

              {!uploadFile ? (
                <label htmlFor="csv-file-input" className="flex flex-col items-center cursor-pointer text-center">
                  <Upload size={32} className="text-secondary mb-3" />
                  <span className="text-sm font-semibold text-primary mb-1">Drag and drop file here</span>
                  <span className="text-xs text-secondary">or click to browse from folder</span>
                </label>
              ) : (
                <div className="flex flex-col items-center w-full max-w-sm text-center">
                  <div className="flex items-center gap-2 bg-surface px-4 py-2 border border-line rounded mb-4 w-full">
                    <Database size={15} className="text-accent flex-shrink-0" />
                    <span className="text-xs font-semibold text-primary truncate flex-1 text-left">
                      {uploadFile.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => setUploadFile(null)}
                      className="text-tertiary hover:text-primary transition-colors duration-120 ease-out"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <Button type="submit" size="submit" className="w-full font-semibold" disabled={uploading}>
                    {uploading ? 'Processing spreadsheet…' : 'Upload & commit transactions'}
                  </Button>
                </div>
              )}
            </form>
          </PanelBody>
        </Panel>

        {/* Requirements Help Sheet */}
        <Panel className="flex flex-col justify-between">
          <PanelBody>
            <h3 className="text-sm font-semibold text-primary flex items-center gap-2 mb-2">
              <AlertCircle size={15} className="text-accent" />
              <span>CSV format guidelines</span>
            </h3>
            <p className="text-body text-secondary leading-relaxed mb-4">
              To guarantee successful parsing, the CSV sheet must include the following headers (case-insensitive):
            </p>
            <ul className="space-y-1.5 text-xs text-primary font-mono bg-bg p-3 border border-line rounded mb-4">
              <li>• <span className="font-semibold">date</span>: YYYY-MM-DD</li>
              <li>• <span className="font-semibold">store_id</span>: string code</li>
              <li>• <span className="font-semibold">product_id</span>: string code</li>
              <li>• <span className="font-semibold">category</span>: item category</li>
              <li>• <span className="font-semibold">quantity</span>: positive integer</li>
              <li>• <span className="font-semibold">revenue</span>: positive float</li>
            </ul>
            <div className="text-[11px] text-tertiary font-medium">
              Optional flags: <span className="font-mono font-semibold">is_holiday</span> and <span className="font-mono font-semibold">is_promo</span> (true/false) are supported.
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Import History */}
      <Panel>
        <PanelHeader title="Import history" description="Every CSV upload, with duplicate/failure counts and one-click undo." />
        {loadingImports ? (
          <PanelBody><SkeletonPanel rows={3} /></PanelBody>
        ) : importHistory.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>File</Th>
                <Th>Uploaded</Th>
                <Th numeric>Imported</Th>
                <Th numeric>Skipped (dup)</Th>
                <Th numeric>Failed</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {importHistory.map((imp) => (
                <tr key={imp.id}>
                  <Td className="font-medium">{imp.filename}</Td>
                  <Td className="whitespace-nowrap">{new Date(imp.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}</Td>
                  <Td numeric className="font-semibold">{imp.rows_imported}</Td>
                  <Td numeric className="text-secondary">{imp.rows_skipped_duplicate || 0}</Td>
                  <Td numeric className={imp.rows_failed > 0 ? 'text-down font-semibold' : 'text-secondary'}>{imp.rows_failed || 0}</Td>
                  <Td>
                    {imp.status === 'undone' ? (
                      <Badge variant="neutral">Undone</Badge>
                    ) : (
                      <Badge variant="positive">Completed</Badge>
                    )}
                  </Td>
                  <Td>
                    {imp.status !== 'undone' && imp.rows_imported > 0 && (
                      <Button
                        variant="ghost"
                        size="compact"
                        onClick={() => handleUndo(imp.id)}
                        disabled={undoingId === imp.id}
                      >
                        <RotateCcw size={12} />
                        <span>{undoingId === imp.id ? 'Undoing…' : 'Undo'}</span>
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <PanelBody><EmptyState title="No imports yet" description="Upload a CSV above to see its history here." /></PanelBody>
        )}
      </Panel>

      {/* Lower Block: Paginated Sales Ledger */}
      <Panel>
        <PanelHeader title="Sales history ledger" />
        <PanelBody>
          {/* Filter Toolbar */}
          <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <div>
              <Label>Store</Label>
              <Select value={selectedStore} onChange={(e) => setSelectedStore(e.target.value)}>
                <option value="">All stores</option>
                {filters.stores.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
            </div>

            <div>
              <Label>Product</Label>
              <Select value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}>
                <option value="">All products</option>
                {filters.products.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </Select>
            </div>

            <div>
              <Label>Category</Label>
              <Select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}>
                <option value="">All categories</option>
                {filters.categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </div>

            <div>
              <Label>Start date</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>

            <div>
              <Label>End date</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>

            <div className="flex items-end gap-2">
              <Button type="submit" size="default" className="flex-1 font-semibold">
                <Search size={13} />
                <span>Search</span>
              </Button>
              {hasActiveFilters && (
                <Button type="button" variant="ghost" size="default" onClick={handleClearFilters} title="Clear filters">
                  Clear
                </Button>
              )}
            </div>
          </form>

          {loadingList ? (
            <SkeletonPanel rows={5} />
          ) : salesList.length > 0 ? (
            <>
              <Table>
                <thead>
                  <tr>
                    <Th>Date</Th>
                    <Th>Store</Th>
                    <Th>Product</Th>
                    <Th>Category</Th>
                    <Th numeric>Qty sold</Th>
                    <Th numeric>Daily revenue</Th>
                    <Th>Holiday?</Th>
                    <Th>Promo?</Th>
                  </tr>
                </thead>
                <tbody>
                  {salesList.map((t) => (
                    <tr key={t.id}>
                      <Td className="whitespace-nowrap font-medium">
                        {new Date(t.date).toLocaleDateString(undefined, { dateStyle: 'medium' })}
                      </Td>
                      <Td>{t.store_id}</Td>
                      <Td className="font-semibold text-accent">{t.product_id}</Td>
                      <Td>{t.category}</Td>
                      <Td numeric>{t.quantity}</Td>
                      <Td numeric className="font-semibold">${t.revenue.toLocaleString()}</Td>
                      <Td>{t.is_holiday ? <Badge variant="positive">Yes</Badge> : <span className="text-tertiary text-[11px]">—</span>}</Td>
                      <Td>{t.is_promo ? <Badge variant="warning">Yes</Badge> : <span className="text-tertiary text-[11px]">—</span>}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              {totalPages > 1 && (
                <div className="flex justify-between items-center mt-4 pt-4 border-t border-line">
                  <span className="text-xs text-secondary">
                    Showing page <span className="font-semibold text-primary font-mono">{page}</span> of{' '}
                    <span className="font-semibold text-primary font-mono">{totalPages}</span> ({total} entries)
                  </span>

                  <div className="flex gap-2">
                    <Button variant="ghost" size="compact" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                      <ChevronLeft size={14} />
                      <span>Prev</span>
                    </Button>
                    <Button variant="ghost" size="compact" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                      <span>Next</span>
                      <ChevronRight size={14} />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState title="No historical records match the active search criteria" />
          )}
        </PanelBody>
      </Panel>
    </div>
  )
}
