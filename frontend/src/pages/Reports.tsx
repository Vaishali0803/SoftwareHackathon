import { useNavigate } from 'react-router-dom'
import { FileText, Download, FileSpreadsheet, BarChart2, ShieldCheck, CheckCircle, AlertCircle } from 'lucide-react'
import { getCsvUrl, getXlsxUrl, getReportXlsxUrl } from '../services/api'
import { useStore } from '../store'
import RiskBadge from '../components/RiskBadge'
import ScoreGauge from '../components/ScoreGauge'

export default function Reports() {
  const navigate = useNavigate()
  const { generation, validation, privacy, dataset, preprocessing } = useStore()

  const ready = generation?.status === 'done'

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="page-title">Reports & Export</h1>
        <p className="text-slate-500 mt-1 text-sm">Download your synthetic dataset and validation reports.</p>
      </div>

      {/* Workflow status */}
      <div className="card p-6 space-y-3">
        <h2 className="section-title mb-2">Workflow Status</h2>
        {[
          { label: 'Dataset uploaded', done: !!dataset, link: '/upload' },
          { label: 'Data preprocessed', done: !!preprocessing, link: '/upload' },
          { label: 'Synthetic data generated', done: ready, link: '/generate' },
          { label: 'Statistical validation complete', done: !!validation, link: '/validation' },
          { label: 'Privacy check complete', done: !!privacy, link: '/privacy' },
        ].map(({ label, done, link }) => (
          <div key={label} className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {done
                ? <CheckCircle className="w-4 h-4 text-clinical-500" />
                : <AlertCircle className="w-4 h-4 text-slate-300" />
              }
              <span className={`text-sm ${done ? 'text-slate-700' : 'text-slate-400'}`}>{label}</span>
            </div>
            {!done && (
              <button onClick={() => navigate(link)} className="text-xs text-brand-600 hover:underline">
                Go →
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Quick summary */}
      {(validation || privacy) && (
        <div className="card p-6">
          <h2 className="section-title mb-4">Quality Summary</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {validation?.overall_scores && (
              <>
                <ScoreGauge score={validation.overall_scores.distribution_similarity} label="Distribution" size="sm" />
                <ScoreGauge score={validation.overall_scores.correlation_preservation} label="Correlation" size="sm" />
                <ScoreGauge score={validation.overall_scores.overall_quality} label="Overall Quality" size="sm" />
              </>
            )}
            {privacy && (
              <div className="card p-4 text-center bg-slate-50">
                <RiskBadge level={privacy.risk_level} />
                <p className="text-xs text-slate-400 mt-2">Privacy risk</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Downloads */}
      <div className="card p-6 space-y-4">
        <h2 className="section-title">Download Synthetic Data</h2>
        {ready ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <a
              href={getCsvUrl(generation!.id)}
              download
              className="btn-secondary justify-center py-3 text-sm"
            >
              <Download className="w-4 h-4" />
              Download CSV
            </a>
            <a
              href={getXlsxUrl(generation!.id)}
              download
              className="btn-primary justify-center py-3 text-sm"
            >
              <FileSpreadsheet className="w-4 h-4" />
              Download Excel (.xlsx)
            </a>
          </div>
        ) : (
          <div className="bg-slate-50 rounded-lg p-4 text-center text-sm text-slate-400">
            Generate a synthetic dataset to enable downloads.
          </div>
        )}
        {ready && generation && (
          <p className="text-xs text-slate-400 text-center">
            {generation.num_generated?.toLocaleString()} synthetic records · {generation.model_used}
          </p>
        )}
      </div>

      {/* Validation report download */}
      <div className="card p-6 space-y-4">
        <h2 className="section-title">Download Validation Report</h2>
        {ready ? (
          <a
            href={getReportXlsxUrl(generation!.id)}
            download
            className="btn-secondary justify-center py-3 text-sm w-full"
          >
            <FileText className="w-4 h-4" />
            Download Validation Report (.xlsx)
          </a>
        ) : (
          <div className="bg-slate-50 rounded-lg p-4 text-center text-sm text-slate-400">
            Run validation to generate a report.
          </div>
        )}
        <p className="text-xs text-slate-400">
          The report includes: distribution statistics, correlation analysis, categorical comparison,
          privacy risk checks, and a summary sheet. All metrics are prototype-level indicators.
        </p>
      </div>

      {/* Generation info */}
      {generation && (
        <div className="card p-5 space-y-2">
          <h2 className="section-title text-base">Generation Details</h2>
          <div className="grid grid-cols-2 gap-y-1 text-sm">
            {[
              ['Generation ID', generation.id.slice(0, 16) + '…'],
              ['Model used', generation.model_used ?? '—'],
              ['Records requested', generation.num_requested?.toLocaleString()],
              ['Records generated', generation.num_generated?.toLocaleString() ?? '—'],
              ['Generation time', generation.generation_time_seconds ? `${generation.generation_time_seconds.toFixed(1)}s` : '—'],
              ['Created at', new Date(generation.created_at).toLocaleString()],
            ].map(([k, v]) => (
              <div key={String(k)} className="contents">
                <span className="text-slate-400">{k}</span>
                <span className="text-slate-700 font-medium">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
