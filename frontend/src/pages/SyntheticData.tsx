import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Table2, Search, ChevronLeft, ChevronRight,
  ChevronUp, ChevronDown, Download, FileSpreadsheet
} from 'lucide-react'
import { getPreview, getCsvUrl, getXlsxUrl, extractError } from '../services/api'
import { useStore } from '../store'
import type { PreviewResponse } from '../types'

export default function SyntheticData() {
  const navigate = useNavigate()
  const { generation } = useStore()

  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [sortCol, setSortCol] = useState<string | undefined>()
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [visibleCols, setVisibleCols] = useState<Set<string>>(new Set())
  const [showColPicker, setShowColPicker] = useState(false)

  const load = useCallback(async () => {
    if (!generation || generation.status !== 'done') return
    setLoading(true)
    try {
      const data = await getPreview(generation.id, page, pageSize, search || undefined, sortCol, sortDir)
      setPreview(data)
      if (visibleCols.size === 0) {
        setVisibleCols(new Set(data.columns))
      }
    } catch (e) {
      toast.error(extractError(e))
    } finally {
      setLoading(false)
    }
  }, [generation?.id, page, pageSize, search, sortCol, sortDir]) // eslint-disable-line

  useEffect(() => { load() }, [load])

  function handleSort(col: string) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
    setPage(1)
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  if (!generation || generation.status !== 'done') {
    return (
      <div className="max-w-xl mx-auto text-center py-24">
        <Table2 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
        <p className="text-slate-500 mb-6">Generate synthetic data first.</p>
        <button onClick={() => navigate('/generate')} className="btn-primary">Go to Generate</button>
      </div>
    )
  }

  const totalPages = preview ? Math.ceil(preview.total_rows / pageSize) : 1
  const displayCols = preview?.columns.filter(c => visibleCols.has(c)) ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">Synthetic Dataset Preview</h1>
          <p className="text-slate-500 mt-1 text-sm">
            {preview ? `${preview.total_rows.toLocaleString()} records · ${preview.columns.length} columns` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <a href={getCsvUrl(generation.id)} download className="btn-secondary text-sm">
            <Download className="w-4 h-4" />
            CSV
          </a>
          <a href={getXlsxUrl(generation.id)} download className="btn-primary text-sm">
            <FileSpreadsheet className="w-4 h-4" />
            Excel
          </a>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search records…"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              className="input pl-9 w-56"
            />
          </div>
          <button type="submit" className="btn-secondary">Search</button>
          {search && (
            <button type="button" onClick={() => { setSearch(''); setSearchInput(''); setPage(1) }} className="btn-secondary text-xs">
              Clear
            </button>
          )}
        </form>

        <button onClick={() => setShowColPicker(v => !v)} className="btn-secondary text-sm">
          Columns ({displayCols.length}/{preview?.columns.length ?? 0})
        </button>
      </div>

      {/* Column picker */}
      {showColPicker && preview && (
        <div className="card p-4">
          <p className="text-xs font-semibold text-slate-600 mb-2">Visible columns</p>
          <div className="flex flex-wrap gap-2">
            {preview.columns.map(col => (
              <label key={col} className="flex items-center gap-1.5 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleCols.has(col)}
                  onChange={() => {
                    setVisibleCols(prev => {
                      const next = new Set(prev)
                      next.has(col) ? next.delete(col) : next.add(col)
                      return next
                    })
                  }}
                  className="w-3.5 h-3.5 rounded"
                />
                {col}
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  {displayCols.map(col => (
                    <th
                      key={col}
                      className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap cursor-pointer hover:text-slate-700 select-none"
                      onClick={() => handleSort(col)}
                    >
                      <span className="flex items-center gap-1">
                        {col}
                        {sortCol === col
                          ? sortDir === 'asc'
                            ? <ChevronUp className="w-3 h-3" />
                            : <ChevronDown className="w-3 h-3" />
                          : <span className="w-3 h-3" />
                        }
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {preview?.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50/50">
                    {displayCols.map(col => {
                      const val = row[col]
                      return (
                        <td key={col} className="px-4 py-2.5 text-slate-600 whitespace-nowrap max-w-[180px] truncate">
                          {val === null || val === undefined
                            ? <span className="text-slate-300">—</span>
                            : String(val)
                          }
                        </td>
                      )
                    })}
                  </tr>
                ))}
                {preview?.rows.length === 0 && (
                  <tr>
                    <td colSpan={displayCols.length} className="px-4 py-12 text-center text-slate-400">
                      No records match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {preview && (
          <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-sm text-slate-500">
            <span>
              {((page - 1) * pageSize + 1).toLocaleString()}–{Math.min(page * pageSize, preview.total_rows).toLocaleString()} of {preview.total_rows.toLocaleString()}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary p-1.5 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary p-1.5 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Synthetic data note */}
      <p className="text-xs text-slate-400 text-center">
        This data is <strong>synthetically generated</strong> — it does not represent real patients.
        Do not treat it as actual patient records.
      </p>
    </div>
  )
}
