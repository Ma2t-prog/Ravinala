import { type ReactNode, useState } from 'react'

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'accent' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  className?: string
}

const sizes = {
  sm: { padding: '8px 16px', fontSize: 12, minHeight: 36 },
  md: { padding: '12px 24px', fontSize: 14, minHeight: 44 },
  lg: { padding: '14px 32px', fontSize: 15, minHeight: 48 },
} as const

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className,
}: ButtonProps) {
  const [hovered, setHovered] = useState(false)
  const [active, setActive] = useState(false)

  const sizeStyle = sizes[size]

  const getStyle = (): React.CSSProperties => {
    if (variant === 'accent') {
      return {
        background: hovered
          ? 'rgba(0,217,255,0.12)'
          : 'rgba(0,217,255,0.06)',
        border: `1px solid ${hovered ? '#00D9FF' : 'rgba(0,217,255,0.2)'}`,
        color: '#00D9FF',
        borderRadius: 6,
        fontFamily: "'DM Sans', sans-serif",
        fontWeight: 600,
        fontSize: sizeStyle.fontSize,
        padding: sizeStyle.padding,
        minHeight: sizeStyle.minHeight,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      }
    }

    if (variant === 'danger') {
      return {
        background: hovered
          ? 'rgba(239,68,68,0.12)'
          : 'rgba(239,68,68,0.06)',
        border: `1px solid ${hovered ? 'rgba(239,68,68,0.4)' : 'rgba(239,68,68,0.2)'}`,
        color: '#EF4444',
        borderRadius: 6,
        fontFamily: "'DM Sans', sans-serif",
        fontWeight: 600,
        fontSize: sizeStyle.fontSize,
        padding: sizeStyle.padding,
        minHeight: sizeStyle.minHeight,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      }
    }

    // Primary
    const base: React.CSSProperties = {
      background: hovered
        ? 'linear-gradient(135deg, rgba(192,192,200,0.18) 0%, rgba(212,212,220,0.25) 50%, rgba(192,192,200,0.18) 100%)'
        : 'linear-gradient(135deg, rgba(192,192,200,0.12) 0%, rgba(212,212,220,0.18) 50%, rgba(192,192,200,0.12) 100%)',
      border: `1px solid ${hovered ? 'rgba(192,192,210,0.40)' : 'rgba(192,192,210,0.25)'}`,
      color: hovered ? '#FFFFFF' : '#F0F0F5',
      borderRadius: 10,
      fontFamily: "'DM Sans', sans-serif",
      fontWeight: 500,
      fontSize: sizeStyle.fontSize,
      padding: sizeStyle.padding,
      minHeight: sizeStyle.minHeight,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: 'all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      transform: active
        ? 'translateY(0) scale(0.98)'
        : hovered
        ? 'translateY(-1px)'
        : 'translateY(0)',
      boxShadow: active
        ? '0 1px 2px rgba(0,0,0,0.4), inset 0 1px 3px rgba(0,0,0,0.2)'
        : hovered
        ? '0 2px 8px rgba(192,192,210,0.15), 0 1px 2px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08)'
        : '0 1px 2px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06)',
    }

    return base
  }

  return (
    <button
      type="button"
      className={className}
      style={getStyle()}
      onClick={disabled ? undefined : onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false)
        setActive(false)
      }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
