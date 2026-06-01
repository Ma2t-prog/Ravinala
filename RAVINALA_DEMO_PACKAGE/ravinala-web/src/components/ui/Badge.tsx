import { type ReactNode } from 'react'
import { cn } from '../../lib/cn'

type BadgeVariant = 'up' | 'down' | 'neutral' | 'warning' | 'info'

interface BadgeProps {
  variant: BadgeVariant
  children: ReactNode
  className?: string
}

const variantStyles: Record<BadgeVariant, { bg: string; color: string; border: string }> = {
  up: {
    bg: 'rgba(16,185,129,0.15)',
    color: '#10B981',
    border: 'rgba(16,185,129,0.25)',
  },
  down: {
    bg: 'rgba(239,68,68,0.15)',
    color: '#EF4444',
    border: 'rgba(239,68,68,0.25)',
  },
  neutral: {
    bg: 'rgba(100,116,139,0.15)',
    color: '#94A3B8',
    border: 'rgba(100,116,139,0.25)',
  },
  warning: {
    bg: 'rgba(245,158,11,0.15)',
    color: '#F59E0B',
    border: 'rgba(245,158,11,0.25)',
  },
  info: {
    bg: 'rgba(0,217,255,0.1)',
    color: '#00D9FF',
    border: 'rgba(0,217,255,0.2)',
  },
}

const variantIcons: Record<BadgeVariant, string | null> = {
  up: '▲',
  down: '▼',
  neutral: null,
  warning: '⚠',
  info: null,
}

export function Badge({ variant, children, className }: BadgeProps) {
  const { bg, color, border } = variantStyles[variant]
  const icon = variantIcons[variant]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium leading-none whitespace-nowrap',
        className
      )}
      style={{
        backgroundColor: bg,
        color,
        border: `1px solid ${border}`,
      }}
    >
      {icon && (
        <span className="text-[10px] leading-none" aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  )
}
