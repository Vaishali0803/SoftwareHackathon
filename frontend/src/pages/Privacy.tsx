import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ShieldCheck, RefreshCw, Info } from 'lucide-react'
import { runPrivacyCheck, extractError } from '../services/api'
import { useStore } from '../store'
import RiskBadge from '../components/RiskBadge'

export default function Privacy() {
  const navigate = useNavigate()
  const { generation, privacy, setPrivacy } = useStore()
  const [running, setRunning] = useState(false)

  async function handleRun() {
    if (!generation || generation.status !== 'done') return
    setRunning(true)
    try {
      const p = await runPrivacyCheck(generation.id)
      setPrivacy(p)
      toast.success('Privacy check complete')
    } catch (e) {
      toast.error(extractError(e))
    } finally {
      setRunning(false)
    }
  }

  if (!generation || generation.status !== 'done') {
    return (
      <div className="max-w-xl mx-auto text-center py-24">
        <ShieldCheck className="w-12 h-12 text-slate-300 mx-auto mb-4" />
        <p className="text-slate-500 mb-6">Generate synthetic data first.</p>
        <button onClick={() => navigate('/generate')} className="btn-primary">Go to Generate</button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Privacy Risk Checks</h1>
          <p className="text-slate-500 mt-1 text-sm">Prototype-level duplicate and similarity detection.</p>
        </div>
        <button onClick={handleRun} disabled={running} className="btn-secondary">
          {running
            ? <><span className="w-4 h-4 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />Checking…</>
            : <><RefreshCw className="w-4 h-4" />{privacy ? 'Re-run' : 'Run'} Privacy Check</>
          }
        </button>
      </div>

      {!privacy && !running && (
        <div className="card p-8 text-center">
          <ShieldCheck className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Click "Run Privacy Check" to begin analysis.</p>
        </div>
      )}

      {privacy && (
        <>
          {/* Risk level */}
          <div className="card p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-700 mb-1">Overall Risk Level</p>
              <p className="text-xs text-slate-400">{privacy.details.risk_interpretation}</p>
            </div>
            <RiskBadge level={privacy.risk_level} large />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Source records', value: privacy.total_source_records.toLocaleString() },
              { label: 'Synthetic records', value: privacy.total_synthetic_records.toLocaleString() },
              { label: 'Exact duplicates', value: privacy.exact_duplicates, highlight: privacy.exact_duplicates > 0 },
              { label: 'Near duplicates (est.)', value: privacy.near_duplicates, highlight: privacy.near_duplicates > privacy.total_synthetic_records * 0.02 },
            ].map(({ label, value, highlight }) => (
              <div key={label} className="card p-4">
                <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
                <p className={`text-2xl font-bold mt-0.5 ${highlight ? 'text-amber-600' : 'text-slate-800'}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Rate bars */}
          <div className="card p-6 space-y-4">
            <h2 className="section-title">Duplicate Rates</h2>
            {[
              {
                label: 'Exact duplicate rate',
                pct: privacy.duplicate_rate_pct,
                threshold: 1,
                desc: 'Synthetic rows that are identical to a source row.',
              },
              {
                label: 'Near-duplicate rate (estimated)',
                pct: privacy.near_duplicate_rate_pct,
                threshold: 5,
                desc: 'Synthetic rows with high similarity to any source row (L2 distance < 0.05 on normalised features).',
              },
            ].map(({ label, pct, threshold, desc }) => (
              <div key={label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-700">{label}</span>
                  <span className={`text-sm font-bold ${pct > threshold ? 'text-amber-600' : 'text-clinical-600'}`}>
                    {pct.toFixed(4)}%
                  </span>
                </div>
                <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${pct > threshold ? 'bg-amber-400' : 'bg-clinical-500'}`}
                    style={{ width: `${Math.min(100, pct * 10)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">{desc}</p>
              </div>
            ))}
          </div>

          {/* Near-duplicate samples */}
          {privacy.details.near_duplicate_sample_details?.length > 0 && (
            <div className="card p-6">
              <h2 className="section-title mb-3">Near-Duplicate Samples (top {privacy.details.near_duplicate_sample_details.length})</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                      <th className="px-4 py-2 text-left">Synthetic record #</th>
                      <th className="px-4 py-2 text-left">Nearest source record #</th>
                      <th className="px-4 py-2 text-right">L2 distance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {privacy.details.near_duplicate_sample_details.map((d, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-slate-700">#{d.synth_idx}</td>
                        <td className="px-4 py-2 text-slate-600">#{d.nearest_source_idx}</td>
                        <td className="px-4 py-2 text-right font-mono text-amber-600">{d.distance.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Technical note */}
          <div className="card border-slate-200 bg-slate-50 p-4 flex gap-3">
            <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-500 leading-relaxed">{privacy.details.note}</p>
          </div>
        </>
      )}
    </div>
  )
}
