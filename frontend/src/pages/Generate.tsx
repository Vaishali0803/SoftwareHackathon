import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Cpu, ArrowRight, CheckCircle, AlertCircle, Users, Activity, ShieldAlert } from 'lucide-react'
import { startGeneration, getGenerationStatus, checkHealth, extractError, type HealthResponse } from '../services/api'
import { useStore } from '../store'
import ProgressBar from '../components/ProgressBar'

const MODELS = [
  { value: 'CTGAN',          label: 'CTGAN',          desc: 'Conditional GAN — best quality.' },
  { value: 'TVAE',           label: 'TVAE',           desc: 'Variational autoencoder.' },
  { value: 'GAUSSIANCOPULA', label: 'Gaussian Copula', desc: 'Fastest, simpler distributions.' },
]

export default function Generate() {
  const navigate = useNavigate()
  const { dataset, preprocessing, generation, setGeneration } = useStore()

  const [numRecords, setNumRecords] = useState(10000)
  const [model, setModel]           = useState<'CTGAN' | 'TVAE' | 'GAUSSIANCOPULA'>('CTGAN')
  const [epochs, setEpochs]         = useState(300)
  const [olderPct, setOlderPct]     = useState<number | ''>('')
  const [diabeticPct, setDiabeticPct] = useState<number | ''>('')
  const [actLow, setActLow]         = useState<number | ''>('')
  const [actMed, setActMed]         = useState<number | ''>('')
  const [actHigh, setActHigh]       = useState<number | ''>('')
  const [submitting, setSubmitting] = useState(false)
  // Only track SDV availability to show an error when it's missing — not as a status banner
  const [sdvMissing, setSdvMissing] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    checkHealth()
      .then((h: HealthResponse) => { if (!h.dependencies.generation_ready) setSdvMissing(true) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (generation && ['pending', 'training', 'generating'].includes(generation.status)) {
      startPolling(generation.id)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, []) // eslint-disable-line

  function startPolling(genId: string) {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const status = await getGenerationStatus(genId)
        setGeneration(status)
        if (status.status === 'done') {
          clearInterval(pollRef.current!)
          toast.success(`Generated ${status.num_generated?.toLocaleString()} records in ${status.generation_time_seconds?.toFixed(1)}s`)
        }
        if (status.status === 'error') {
          clearInterval(pollRef.current!)
          toast.error(`Generation failed: ${status.error_message}`)
        }
      } catch { /* silently retry */ }
    }, 2000)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!dataset || !preprocessing) { toast.error('Upload and preprocess a dataset first.'); return }
    setSubmitting(true)
    try {
      const cohort: Record<string, unknown> = {
        age_column: 'Age', diabetes_column: 'Diabetes', activity_column: 'ActivityLevel',
      }
      if (olderPct !== '')  cohort.older_patients_pct = Number(olderPct)
      if (diabeticPct !== '') cohort.diabetic_pct = Number(diabeticPct)
      if (actLow !== '' || actMed !== '' || actHigh !== '') {
        cohort.activity_distribution = {
          ...(actLow  !== '' ? { Low:    Number(actLow)  } : {}),
          ...(actMed  !== '' ? { Medium: Number(actMed)  } : {}),
          ...(actHigh !== '' ? { High:   Number(actHigh) } : {}),
        }
      }
      const hasCohort = cohort.older_patients_pct !== undefined
        || cohort.diabetic_pct !== undefined
        || cohort.activity_distribution !== undefined

      const res = await startGeneration({
        dataset_id: dataset.id,
        num_records: numRecords,
        model,
        epochs,
        cohort: hasCohort ? cohort as Parameters<typeof startGeneration>[0]['cohort'] : undefined,
      })
      const initial = await getGenerationStatus(res.generation_id)
      setGeneration(initial)
      startPolling(res.generation_id)
      toast.success('Generation started!')
    } catch (e) {
      toast.error(extractError(e))
    } finally {
      setSubmitting(false)
    }
  }

  const isRunning = generation && ['pending', 'training', 'generating'].includes(generation.status)
  const isDone    = generation?.status === 'done'
  const isError   = generation?.status === 'error'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="page-title">Generate Synthetic Data</h1>
        <p className="text-slate-500 mt-1 text-sm">
          Configure the synthesis model and cohort requirements, then generate.
        </p>
      </div>

      {/* No dataset — concise prompt */}
      {!preprocessing && (
        <div className="card border-amber-100 bg-amber-50 p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
            <p className="text-sm text-amber-700">No dataset loaded yet.</p>
          </div>
          <button onClick={() => navigate('/upload')} className="btn-secondary text-xs flex-shrink-0">
            Upload dataset <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* SDV missing — only show this error when the dependency is actually absent */}
      {sdvMissing && (
        <div className="card border-red-200 bg-red-50 p-4 flex gap-3">
          <ShieldAlert className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-700">SDV not installed — generation unavailable</p>
            <code className="text-xs text-red-600 mt-1 block">
              pip install sdv ctgan rdt copulas sdmetrics deepecho
            </code>
          </div>
        </div>
      )}

      {/* Generation progress card */}
      {(isRunning || isDone || isError) && generation && (
        <div className={`card p-5 space-y-3 ${isError ? 'border-red-200' : isDone ? 'border-clinical-200' : ''}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isDone
                ? <CheckCircle className="w-4 h-4 text-clinical-600" />
                : isError
                ? <AlertCircle className="w-4 h-4 text-red-500" />
                : <Cpu className="w-4 h-4 text-brand-500 animate-pulse" />
              }
              <span className="text-sm font-semibold text-slate-800">
                {isDone ? 'Generation complete' : isError ? 'Generation failed' : 'Generating…'}
              </span>
            </div>
            {isDone && (
              <span className="text-xs text-slate-400">
                {generation.model_used} · {generation.generation_time_seconds?.toFixed(1)}s
              </span>
            )}
          </div>

          {!isError && (
            <ProgressBar value={generation.progress} animated={isRunning || false} color={isDone ? 'green' : 'blue'} />
          )}
          <p className="text-xs text-slate-500">{generation.progress_message}</p>

          {isError && <p className="text-sm text-red-600">{generation.error_message}</p>}

          {isDone && generation.cohort_results && Object.keys(generation.cohort_results).length > 0 && (
            <CohortResults results={generation.cohort_results as Record<string, unknown>} />
          )}

          {isDone && (
            <div className="flex flex-wrap gap-2 pt-1">
              <button onClick={() => navigate('/dashboard')} className="btn-primary text-sm">
                Dashboard <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => navigate('/validation')} className="btn-secondary text-sm">Validate</button>
              <button onClick={() => navigate('/synthetic')}  className="btn-secondary text-sm">Preview data</button>
              <button onClick={() => navigate('/reports')}    className="btn-secondary text-sm">Export</button>
            </div>
          )}
        </div>
      )}

      {/* Config form — hidden while running */}
      {!isRunning && (
        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Dataset context */}
          {preprocessing && (
            <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-lg border border-slate-200">
              <Activity className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="text-sm text-slate-600">
                <strong>{preprocessing.rows_after.toLocaleString()}</strong> source records ·{' '}
                <strong>{preprocessing.columns_included.length}</strong> columns
              </span>
            </div>
          )}

          {/* Generation settings */}
          <div className="card p-5 space-y-4">
            <h2 className="section-title">Generation Settings</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Synthetic records</label>
                <input
                  type="number" min={100} max={500000} required
                  value={numRecords}
                  onChange={e => setNumRecords(Number(e.target.value))}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Training epochs</label>
                <input
                  type="number" min={10} max={2000}
                  value={epochs}
                  onChange={e => setEpochs(Number(e.target.value))}
                  className="input"
                />
                <p className="text-xs text-slate-400 mt-1">Higher = better quality, slower</p>
              </div>
            </div>

            {/* Model selector — compact pill style */}
            <div>
              <label className="label">Model</label>
              <div className="flex gap-2 flex-wrap">
                {MODELS.map(m => (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => setModel(m.value as typeof model)}
                    className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                      model === m.value
                        ? 'border-brand-500 bg-brand-50 text-brand-700 font-semibold'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-1.5">
                Auto-fallback: CTGAN → TVAE → Gaussian Copula if training fails.
              </p>
            </div>
          </div>

          {/* Cohort requirements */}
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-slate-400" />
              <h2 className="section-title">Cohort Requirements</h2>
              <span className="badge-gray text-xs ml-1">Optional</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Older patients (age ≥ 60) %</label>
                <input
                  type="number" min={0} max={100} placeholder="e.g. 40"
                  value={olderPct}
                  onChange={e => setOlderPct(e.target.value === '' ? '' : Number(e.target.value))}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Diabetic patients %</label>
                <input
                  type="number" min={0} max={100} placeholder="e.g. 30"
                  value={diabeticPct}
                  onChange={e => setDiabeticPct(e.target.value === '' ? '' : Number(e.target.value))}
                  className="input"
                />
              </div>
            </div>

            <div>
              <label className="label">Activity level distribution %</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Low',    val: actLow,  set: setActLow  },
                  { label: 'Medium', val: actMed,  set: setActMed  },
                  { label: 'High',   val: actHigh, set: setActHigh },
                ].map(({ label, val, set }) => (
                  <div key={label}>
                    <label className="text-xs text-slate-500 mb-1 block">{label}</label>
                    <input
                      type="number" min={0} max={100} placeholder="e.g. 33"
                      value={val}
                      onChange={e => set(e.target.value === '' ? '' : Number(e.target.value))}
                      className="input"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || !preprocessing || sdvMissing}
            className="btn-primary w-full py-3 text-base justify-center"
          >
            {submitting ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Starting…</>
            ) : (
              <><Cpu className="w-5 h-5" />Generate {numRecords.toLocaleString()} Synthetic Records</>
            )}
          </button>
        </form>
      )}
    </div>
  )
}

function CohortResults({ results }: { results: Record<string, unknown> }) {
  const rows: { label: string; requested: unknown; actual: unknown; diff: unknown }[] = []
  if (results.older_pct_requested !== undefined)
    rows.push({ label: 'Older (≥60)', requested: results.older_pct_requested, actual: results.older_pct_actual, diff: results.older_pct_diff })
  if (results.diabetic_pct_requested !== undefined)
    rows.push({ label: 'Diabetic', requested: results.diabetic_pct_requested, actual: results.diabetic_pct_actual, diff: results.diabetic_pct_diff })
  if (!rows.length) return null
  return (
    <div className="pt-1">
      <p className="text-xs font-semibold text-slate-500 mb-1.5">Cohort accuracy</p>
      <div className="space-y-1">
        {rows.map(r => (
          <div key={String(r.label)} className="flex items-center gap-4 text-xs text-slate-600">
            <span className="w-20 font-medium">{String(r.label)}</span>
            <span>Requested <strong>{String(r.requested)}%</strong></span>
            <span>Achieved <strong>{String(r.actual)}%</strong></span>
            <span className={Number(r.diff) > 5 ? 'text-amber-600' : 'text-clinical-600'}>
              Δ {String(r.diff)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
