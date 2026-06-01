interface PageHeaderProps {
  icon: string
  title: string
  subtitle: string
  badge?: string
  badgeColor?: string
}

export function PageHeader({
  icon,
  title,
  subtitle,
  badge,
  badgeColor = '#00D9FF',
}: PageHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(51,65,85,0.2)',
        paddingBottom: 24,
        marginBottom: 24,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Icon box */}
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: 'rgba(0,217,255,0.06)',
            border: '1px solid rgba(0,217,255,0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#00D9FF',
            fontSize: 14,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {icon}
        </div>

        {/* Title + subtitle */}
        <div>
          <h1
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: '#F1F5F9',
              letterSpacing: '-0.02em',
              lineHeight: 1.2,
              margin: 0,
            }}
          >
            {title}
          </h1>
          <p
            style={{
              fontSize: 12,
              color: '#94A3B8',
              fontWeight: 400,
              margin: 0,
              marginTop: 2,
            }}
          >
            {subtitle}
          </p>
        </div>
      </div>

      {/* Badge */}
      {badge && (
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            padding: '4px 12px',
            borderRadius: 9999,
            background: `${badgeColor}10`,
            border: `1px solid ${badgeColor}2E`,
            color: badgeColor,
          }}
        >
          {badge}
        </span>
      )}
    </div>
  )
}
