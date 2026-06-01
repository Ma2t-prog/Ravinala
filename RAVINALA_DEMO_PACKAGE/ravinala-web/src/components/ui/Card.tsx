import { type ReactNode, useState } from 'react'
import { cn } from '../../lib/cn'

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
  subtitle?: string
}

export function Card({ children, className, title, subtitle }: CardProps) {
  const [hovered, setHovered] = useState(false)

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
      {(title || subtitle) && (
        <div className="mb-3">
          {title && (
            <h3
              className="text-sm font-semibold leading-tight"
              style={{ color: '#F1F5F9' }}
            >
              {title}
            </h3>
          )}
          {subtitle && (
            <p
              className="mt-0.5 text-xs"
              style={{ color: '#94A3B8' }}
            >
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  )
}
