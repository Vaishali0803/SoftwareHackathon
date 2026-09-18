import clsx from 'clsx'

interface Props {
  score: number
  label: string
  size?: 'sm' | 'md' | 'lg'
  note?: string
}

function scoreColor(s: number) {
  if (s >= 85) return { ring: 'text-clinical-500', label: 'text-clinical-700', bg: 'bg-clinical-50' }
  if (s >= 65) return { ring: 'text-amber-500', label: 'text-amber-700', bg: 'bg-amber-50' }
  return { ring: 'text-red-500', label: 'text-red-700', bg: 'bg-red-50' }
}

export default function ScoreGauge({ score, label, note, size = 'md' }: Props) {
  const s = Math.min(100, Math.max(0, score))
  const c = scoreColor(s)
  const r = size === 'lg' ? 40 : size === 'sm' ? 24 : 32
  const stroke = size === 'lg' ? 5 : 4
  const circumference = 2 * Math.PI * r
  const dash = (s / 100) * circumference

  return (
    <div className={clsx('card p-4 flex flex-col items-center gap-2', c.bg)}>
      <svg
        width={r * 2 + stroke * 2}
        height={r * 2 + stroke * 2}
        className="-rotate-90"
      >
        <circle
          cx={r + stroke}
          cy={r + stroke}
          r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        <circle
          cx={r + stroke}
          cy={r + stroke}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          className={c.ring}
        />
      </svg>
      <div className="text-center -mt-2">
        <p className={clsx('font-bold', size === 'lg' ? 'text-3xl' : 'text-xl', c.label)}>
          {s.toFixed(1)}%
        </p>
        <p className="text-xs font-medium text-slate-600 mt-0.5">{label}</p>
        {note && <p className="text-[10px] text-slate-400 mt-0.5">{note}</p>}
      </div>
    </div>
  )
}
