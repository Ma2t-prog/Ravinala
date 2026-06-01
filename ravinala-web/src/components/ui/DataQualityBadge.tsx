import type { DataQuality } from "../../api/types";
import { cn } from "../../lib/cn";

interface Props {
  quality: DataQuality;
  className?: string;
}

const CONFIG: Record<
  DataQuality,
  { label: string; bg: string; color: string; border: string; dot: string }
> = {
  live: {
    label: "LIVE",
    bg: "rgba(16,185,129,0.12)",
    color: "#10B981",
    border: "rgba(16,185,129,0.25)",
    dot: "#10B981",
  },
  demo_static: {
    label: "DEMO",
    bg: "rgba(245,158,11,0.12)",
    color: "#F59E0B",
    border: "rgba(245,158,11,0.25)",
    dot: "#F59E0B",
  },
  stale_cache: {
    label: "STALE",
    bg: "rgba(107,114,128,0.15)",
    color: "#9CA3AF",
    border: "rgba(107,114,128,0.25)",
    dot: "#9CA3AF",
  },
  mixed: {
    label: "MIXED",
    bg: "rgba(0,217,255,0.1)",
    color: "#00D9FF",
    border: "rgba(0,217,255,0.2)",
    dot: "#00D9FF",
  },
  error: {
    label: "ERROR",
    bg: "rgba(239,68,68,0.12)",
    color: "#EF4444",
    border: "rgba(239,68,68,0.25)",
    dot: "#EF4444",
  },
  unknown: {
    label: "···",
    bg: "rgba(100,116,139,0.1)",
    color: "#64748B",
    border: "rgba(100,116,139,0.2)",
    dot: "#64748B",
  },
};

const MONO = "JetBrains Mono, monospace";

export function DataQualityBadge({ quality, className }: Props) {
  const cfg = CONFIG[quality] ?? CONFIG.unknown;
  const animate = quality === "live";

  return (
    <span
      className={cn("inline-flex items-center gap-1", className)}
      title={`Data quality: ${quality}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.border}`,
        color: cfg.color,
        borderRadius: 9999,
        padding: "2px 8px",
        fontFamily: MONO,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.08em",
        flexShrink: 0,
        userSelect: "none",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: cfg.dot,
          display: "inline-block",
          flexShrink: 0,
          animation: animate ? "pulse-green 1.5s ease-in-out infinite" : "none",
        }}
      />
      {cfg.label}
    </span>
  );
}
