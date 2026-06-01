import { useState } from 'react'

interface TabsProps {
  tabs: string[]
  active: string
  onChange: (tab: string) => void
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  const [hoveredTab, setHoveredTab] = useState<string | null>(null)

  return (
    <div
      style={{
        display: 'flex',
        borderBottom: '1px solid rgba(51,65,85,0.2)',
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab === active
        const isHovered = tab === hoveredTab

        return (
          <button
            key={tab}
            type="button"
            onClick={() => onChange(tab)}
            onMouseEnter={() => setHoveredTab(tab)}
            onMouseLeave={() => setHoveredTab(null)}
            style={{
              color: isActive ? '#00D9FF' : isHovered ? '#F1F5F9' : '#94A3B8',
              fontSize: 13,
              fontWeight: 500,
              letterSpacing: '0.02em',
              padding: '12px 16px',
              borderBottom: isActive
                ? '2px solid #00D9FF'
                : '2px solid transparent',
              cursor: 'pointer',
              background: isHovered && !isActive
                ? 'rgba(0,217,255,0.03)'
                : 'transparent',
              border: 'none',
              borderBottomStyle: 'solid',
              borderBottomWidth: 2,
              borderBottomColor: isActive ? '#00D9FF' : 'transparent',
              transition: 'color 150ms, background 150ms',
              marginBottom: -1,
            }}
          >
            {tab}
          </button>
        )
      })}
    </div>
  )
}
