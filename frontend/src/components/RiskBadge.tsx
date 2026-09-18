import clsx from 'clsx'
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react'

interface Props { level: 'Low' | 'Medium' | 'High' | string; large?: boolean }

export default function RiskBadge({ level, large = false }: Props) {
  const cfg = {
    Low:    { cls: 'bg-clinical-100 text-clinical-700', Icon: ShieldCheck },
    Medium: { cls: 'bg-amber-100 text-amber-700',       Icon: Shield },
    High:   { cls: 'bg-red-100 text-red-700',           Icon: ShieldAlert },
  }[level] ?? { cls: 'bg-slate-100 text-slate-600', Icon: Shield }

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 font-semibold rounded-full',
      cfg.cls,
      large ? 'px-4 py-2 text-sm' : 'px-2.5 py-1 text-xs'
    )}>
      <cfg.Icon className={large ? 'w-4 h-4' : 'w-3 h-3'} />
      {level} Risk
    </span>
  )
}
