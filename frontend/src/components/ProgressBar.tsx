import clsx from 'clsx'

interface Props {
  value: number       // 0-100
  label?: string
  color?: 'blue' | 'green' | 'amber' | 'red'
  animated?: boolean
  showValue?: boolean
}

const colorMap = {
  blue:  'bg-brand-500',
  green: 'bg-clinical-500',
  amber: 'bg-amber-400',
  red:   'bg-red-500',
}

export default function ProgressBar({
  value, label, color = 'blue', animated = false, showValue = true,
}: Props) {
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div>
      {(label || showValue) && (
        <div className="flex justify-between mb-1.5">
          {label && <span className="text-sm text-slate-600">{label}</span>}
          {showValue && <span className="text-sm font-semibold text-slate-700">{pct.toFixed(0)}%</span>}
        </div>
      )}
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-500',
            colorMap[color],
            animated && pct < 100 && 'progress-pulse'
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
