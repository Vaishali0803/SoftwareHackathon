import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BarChart2, RefreshCw, AlertCircle, Info, ChevronDown, ChevronUp } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { runValidation, extractError } from '../services/api'
import { useStore } from '../store'
import ScoreGauge from '../components/ScoreGauge'
import ProgressBar from '../components/ProgressBar'
import type { NumericalColumnStats } from '../types'

// re-run endpoint (force fresh)
async function rerunValidation(generationId: string) {
  const axios = (await import('axios')).default
  const { data } = await axios.post(`/api/validation/${generationId}/rerun`)
  return data
}

export default function Validation() {
  const navigate = useNavigate()
  const { generation, validation, setValidation } = useStore()
  const [running, setRunning] = useState(false)
  const [showKsDetail, setShowKsDetail] = useState(true)

  async function handleRun(force = false) {
    if (!generation || generation.status !== 'done') return
    setRunning(true)
    try {
      let v
      if (force) {
        // DELETE existing then POST
        const axios = (await import('axios')).default
        try { await axios.post(`/api/validation/${generation.id}/rerun`) }
        catch { /* fall through to regular run */ }
        v = await runValidation(generation.id)
      } else {
        v = await runValidation(generation.id)
      }
      setValidation(v)
      toast.success('Validation complete')
    } catch (e) {
      toast.error(extractError(e))
    } finally {
      setRunning(false)
    }
  }

  if (!generation || generation.status !== 'done') {
    return (
      <div className="max-w-xl mx-auto text-center py-24">
        <BarChart2 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
        <p className="text-slate-500 mb-6">Generate synthetic data first.</p>
        <button onClick={() => navigate('/generate')} className="btn-primary">Go to Generate</button>
      </div>
    )
  }

  const scores = validation?.overall_scores

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Statistical Validation</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Comparing source and synthetic datasets across all columns.
          </p>
        </div>
        <div className="flex gap-2">
          {validation && (
            <button onClick={() => handleRun(true)} disabled={running} className="btn-secondary text-sm">
              <RefreshCw className="w-4 h-4" /> Re-run
            </button>
          )}
          <button onClick={() => handleRun(false)} disabled={running} className="btn-primary text-sm">
            {running
              ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Running…</>
              : <><RefreshCw className="w-4 h-4" />{validation ? 'Refresh' : 'Run Validation'}</>
            }
          </button>
        </div>
      </div>

      {!validation && !running && (
        <div className="card p-8 text-center">
          <BarChart2 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Click "Run Validation" to compare source and synthetic datasets.</p>
        </div>
      )}

      {running && (
        <div className="card p-8 flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
          <p className="text-slate-500 text-sm">Running statistical tests…</p>
        </div>
      )}

      {validation && scores && (
        <>
          {/* Score gauges */}
          <div>
            <h2 className="section-title mb-1">Overall Quality Scores</h2>
            <p className="text-xs text-slate-400 mb-4">Prototype metrics — not a formal clinical validation.</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <ScoreGauge score={scores.distribution_similarity}     label="Distribution Similarity" />
              <ScoreGauge score={scores.correlation_preservation}    label="Correlation Preservation" />
              <ScoreGauge score={scores.ks_pass_rate}                label="KS Pass Rate"
                note={`${scores.ks_passed_columns ?? '?'}/${scores.ks_tested_columns ?? '?'} columns p > 0.05`} />
              <ScoreGauge score={scores.overall_quality}             label="Overall Quality" size="lg" />
            </div>
          </div>

          {/* KS explanation banner */}
          <div className="card border-blue-100 bg-blue-50 p-4 flex gap-3">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-blue-700 space-y-1">
              <p><strong>KS Test (Kolmogorov-Smirnov, two-sample):</strong> Tests whether source and
              synthetic values for each numeric column come from the same distribution.
              Uses <code>scipy.stats.ks_2samp</code>. Pass criterion: <strong>p-value &gt; 0.05</strong>.</p>
              <p>Synthetic sample is capped at <strong>2× source size</strong> for balanced test power —
              comparing 200 source rows against 10,000 synthetic rows gives the KS test extreme
              sensitivity to tiny differences. The cap makes the test symmetric.</p>
              <p>Columns targeted by cohort resampling (e.g. Age when older_patients_pct was set)
              are expected to fail — the distribution was intentionally shifted.</p>
            </div>
          </div>

          {/* Per-column KS detail table */}
          {validation.numerical_stats.length > 0 && (
            <div className="card">
              <div
                className="card-header flex items-center justify-between cursor-pointer select-none"
                onClick={() => setShowKsDetail(v => !v)}
              >
                <div>
                  <h2 className="section-title">KS Test Results — Per Column</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    scipy.stats.ks_2samp · p &gt; 0.05 = PASS · synthetic capped at 2× source n
                  </p>
                </div>
                {showKsDetail ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </div>
              {showKsDetail && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                        <th className="px-4 py-2 text-left">Column</th>
                        <th className="px-4 py-2 text-right">Src n</th>
                        <th className="px-4 py-2 text-right">Syn n</th>
                        <th className="px-4 py-2 text-right">KS cap n</th>
                        <th className="px-4 py-2 text-right">KS stat</th>
                        <th className="px-4 py-2 text-right">p-value</th>
                        <th className="px-4 py-2 text-center">Result</th>
                        <th className="px-4 py-2 text-right">Dist sim</th>
                        <th className="px-4 py-2 text-left">Note</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {validation.numerical_stats.map((s: NumericalColumnStats & {
                        source_n?: number; synth_n?: number; ks_capped_synth_n?: number;
                        ks_pass?: boolean; ks_status?: string; cohort_affected?: boolean
                      }) => (
                        <tr key={s.column} className={s.cohort_affected ? 'bg-amber-50/30' : ''}>
                          <td className="px-4 py-2 font-medium text-slate-700">{s.column}</td>
                          <td className="px-4 py-2 text-right text-slate-500">{s.source_n ?? '—'}</td>
                          <td className="px-4 py-2 text-right text-slate-500">{s.synth_n ?? '—'}</td>
                          <td className="px-4 py-2 text-right text-slate-400 text-xs">{s.ks_capped_synth_n ?? '—'}</td>
                          <td className="px-4 py-2 text-right font-mono">
                            {s.ks_statistic != null ? s.ks_statistic.toFixed(4) : '—'}
                          </td>
                          <td className="px-4 py-2 text-right font-mono">
                            {s.ks_pvalue != null ? s.ks_pvalue.toFixed(6) : '—'}
                          </td>
                          <td className="px-4 py-2 text-center">
                            {s.ks_status === 'pass'
                              ? <span className="badge-green">PASS</span>
                              : s.ks_status === 'fail'
                              ? <span className="badge-red">FAIL</span>
                              : <span className="badge-gray">{s.ks_status ?? '—'}</span>
                            }
                          </td>
                          <td className="px-4 py-2 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-12">
                                <ProgressBar
                                  value={s.distribution_similarity}
                                  showValue={false}
                                  color={s.distribution_similarity >= 80 ? 'green' : s.distribution_similarity >= 60 ? 'amber' : 'red'}
                                />
                              </div>
                              <span className="text-xs font-medium w-10 text-right">{s.distribution_similarity.toFixed(1)}%</span>
                            </div>
                          </td>
                          <td className="px-4 py-2 text-xs text-amber-600">
                            {s.cohort_affected ? '⚠ cohort-targeted' : ''}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Numerical stats summary */}
          {validation.numerical_stats.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="section-title">Numerical Columns — Distribution Summary</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                      <th className="px-4 py-2 text-left">Column</th>
                      <th className="px-4 py-2 text-right">Src Mean</th>
                      <th className="px-4 py-2 text-right">Syn Mean</th>
                      <th className="px-4 py-2 text-right">Src Std</th>
                      <th className="px-4 py-2 text-right">Syn Std</th>
                      <th className="px-4 py-2 text-right">Src Median</th>
                      <th className="px-4 py-2 text-right">Syn Median</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {validation.numerical_stats.map((s: NumericalColumnStats) => (
                      <tr key={s.column}>
                        <td className="px-4 py-2 font-medium text-slate-700">{s.column}</td>
                        <td className="px-4 py-2 text-right">{s.source_mean.toFixed(2)}</td>
                        <td className="px-4 py-2 text-right">{s.synth_mean.toFixed(2)}</td>
                        <td className="px-4 py-2 text-right">{s.source_std.toFixed(2)}</td>
                        <td className="px-4 py-2 text-right">{s.synth_std.toFixed(2)}</td>
                        <td className="px-4 py-2 text-right">{s.source_median.toFixed(2)}</td>
                        <td className="px-4 py-2 text-right">{s.synth_median.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Categorical stats */}
          {validation.categorical_stats.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="section-title">Categorical Columns</h2>
              </div>
              <div className="p-6 space-y-6">
                {validation.categorical_stats.map(cat => {
                  const chartData = Object.keys(cat.source_distribution).map(k => ({
                    name: k,
                    Source: cat.source_distribution[k] ?? 0,
                    Synthetic: cat.synth_distribution[k] ?? 0,
                  }))
                  return (
                    <div key={cat.column}>
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold text-slate-700">{cat.column}</p>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>TVD: {cat.tvd.toFixed(3)}</span>
                          <span className={`font-semibold ${cat.similarity_score >= 80 ? 'text-clinical-600' : 'text-amber-600'}`}>
                            {cat.similarity_score.toFixed(1)}% similar
                          </span>
                        </div>
                      </div>
                      <ResponsiveContainer width="100%" height={120}>
                        <BarChart data={chartData} barSize={20}>
                          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} unit="%" />
                          <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                          <Legend wrapperStyle={{ fontSize: 10 }} />
                          <Bar dataKey="Source" fill="#94a3b8" />
                          <Bar dataKey="Synthetic" fill="#3b82f6" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Correlations */}
          {validation.correlation_stats.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="section-title">Correlation Preservation</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                      <th className="px-4 py-2 text-left">Column A</th>
                      <th className="px-4 py-2 text-left">Column B</th>
                      <th className="px-4 py-2 text-right">Source r</th>
                      <th className="px-4 py-2 text-right">Synthetic r</th>
                      <th className="px-4 py-2 text-right">|Diff|</th>
                      <th className="px-4 py-2 text-right">Quality</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {validation.correlation_stats.map(c => (
                      <tr key={`${c.col_a}-${c.col_b}`}>
                        <td className="px-4 py-2 font-medium text-slate-700">{c.col_a}</td>
                        <td className="px-4 py-2 text-slate-600">{c.col_b}</td>
                        <td className="px-4 py-2 text-right font-mono">{c.source_correlation.toFixed(3)}</td>
                        <td className="px-4 py-2 text-right font-mono">{c.synth_correlation.toFixed(3)}</td>
                        <td className={`px-4 py-2 text-right font-mono font-semibold ${c.difference > 0.15 ? 'text-red-600' : c.difference > 0.05 ? 'text-amber-600' : 'text-clinical-600'}`}>
                          {c.difference.toFixed(3)}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {c.difference <= 0.05
                            ? <span className="badge-green">Excellent</span>
                            : c.difference <= 0.15
                            ? <span className="badge-blue">Good</span>
                            : <span className="badge-yellow">Review</span>
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <div className="card border-slate-200 bg-slate-50 p-4 flex gap-3">
            <AlertCircle className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-500 leading-relaxed">
              KS p-value &gt; 0.05 suggests the two distributions are not statistically distinguishable
              at the 5% significance level. A low pass rate does not necessarily mean the synthetic
              data is unusable — it may reflect intentional cohort shifts or the high sensitivity of
              the KS test with large synthetic sample sizes. All scores are prototype-level indicators.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
