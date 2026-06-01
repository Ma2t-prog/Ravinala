import { useState } from 'react'
import { cn } from '../../lib/cn'

interface StatCardProps {
  label: string
  value: string | number
  change?: number
  changePercent?: number
  color?: string
  className?: string
}

function ArrowUp() {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 10 10"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M5 1L9 7H1L5 1Z" />
    </svg>
  )
}

function ArrowDown() {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 10 10"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M5 9L1 3H9L5 9Z" />
    </svg>
  )
}

export function StatCard({
  label,
  value,
  change,
  changePercent,
  color,
  className,
}: StatCardProps) {
  const [hovered, setHovered] = useState(false)

  const hasChange = change !== undefined || changePercent !== undefined
  const isPositive = (change ?? changePercent ?? 0) >= 0
  const isNeutral = change === 0 && changePercent === 0

  const changeColor = isNeutral
    ? '#94A3B8'
    : isPositive
    ? '#10B981'
    : '#EF4444'

  return (
    <div
      className={cn('', className)}
      style={{
        background:
          'linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6))',
        border: '1px solid rgba(51,65,85,0.3)',
        borderRadius: 10,
        padding: 24,
        transition: 'all 250ms cubic-bezier(0.34, 1.56, 0.64, 1)',
        ...(hovered
          ? {
              borderColor: 'rgba(0,217,255,0.25)',
              boxShadow: '0 8px 24px rgba(0,217,255,0.06)',
              transform: 'translateY(-2px)',
            }
          : {
              borderColor: 'rgba(51,65,85,0.3)',
              boxShadow: 'none',
              transform: 'translateY(0)',
            }),
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Label */}
      <p
        style={{
          fontSize: 10,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#94A3B8',
          fontWeight: 600,
          marginBottom: 4,
        }}
      >
        {label}
      </p>

      {/* Value */}
      <p
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 22,
          fontWeight: 700,
          fontVariantNumeric: 'tabular-nums',
          color: color ?? '#F1F5F9',
          lineHeight: 1.2,
        }}
      >
        {value}
      </p>

      {/* Change indicator */}
      {hasChange && (
        <div
          style={{
            marginTop: 8,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            fontWeight: 600,
            color: changeColor,
          }}
        >
          {!isNeutral && (
            <span style={{ display: 'flex', alignItems: 'center' }}>
              {isPositive ? <ArrowUp /> : <ArrowDown />}
            </span>
          )}

          {change !== undefined && (
            <span>
              {isPositive && !isNeutral ? '+' : ''}
              {typeof change === 'number' ? change.toLocaleString(undefined, { maximumFractionDigits: 4 }) : change}
            </span>
          )}

          {changePercent !== undefined && (
            <span style={{ color: '#64748B' }}>
              (
              {isPositive && !isNeutral ? '+' : ''}
              {changePercent.toFixed(2)}%
              )
            </span>
          )}
        </div>
      )}
    </div>
  )
}
