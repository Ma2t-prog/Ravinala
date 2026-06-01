import { cn } from '../../lib/cn'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeMap = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-10 w-10 border-[3px]',
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        'inline-block rounded-full animate-spin',
        sizeMap[size],
        className
      )}
      style={{
        borderColor: 'rgba(0,217,255,0.2)',
        borderTopColor: '#00D9FF',
      }}
    />
  )
}
