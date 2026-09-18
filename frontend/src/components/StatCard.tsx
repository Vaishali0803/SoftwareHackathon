import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  color?: 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'slate'
}

const colorMap = {
  blue:   'bg-brand-50 text-brand-600',
  green:  'bg-clinical-50 text-clinical-600',
  amber:  'bg-amber-50 text-amber-600',
  red:    'bg-red-50 text-red-600',
  purple: 'bg-purple-50 text-purple-600',
  slate:  'bg-slate-100 text-slate-600',
}

export default function StatCard({ label, value, sub, icon: Icon, color = 'blue' }: Props) {
  return (
    <div className="stat-card flex items-start gap-4">
      {Icon && (
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', colorMap[color])}>
          <Icon className="w-5 h-5" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-900 mt-0.5 truncate">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}
