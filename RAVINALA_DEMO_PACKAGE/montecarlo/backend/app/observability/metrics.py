"""
observability/metrics.py — In-memory request & business metrics.

Étape 11 — Observabilité
─────────────────────────
Thread-safe counters and histograms for:
  - HTTP request count / error count / latency percentiles per endpoint
  - Business metrics (backtests run, ML trainings, risk computations)
  - Cache hit/miss ratio

Exposed via GET /api/v1/monitoring/metrics in Prometheus text format.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _LatencyBucket:
    """Accumulates latency samples for percentile computation."""
    samples: list[float] = field(default_factory=list)
    count: int = 0
    error_count: int = 0

    def record(self, duration_ms: float, is_error: bool = False) -> None:
        self.samples.append(duration_ms)
        self.count += 1
        if is_error:
            self.error_count += 1
        # Cap stored samples to avoid unbounded memory
        if len(self.samples) > 10_000:
            self.samples = self.samples[-5_000:]

    def percentile(self, p: float) -> float | None:
        if not self.samples:
            return None
        s = sorted(self.samples)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]


class MetricsCollector:
    """
    Singleton in-memory metrics store.

    Thread-safe via a simple lock; designed for moderate request rates
    (< 10k req/s).  For higher rates, switch to prometheus_client.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.time()
        # Per-endpoint latency buckets
        self._endpoints: dict[str, _LatencyBucket] = defaultdict(_LatencyBucket)
        # Simple counters
        self._counters: dict[str, int] = defaultdict(int)

    # ─── Recording ────────────────────────────────────────────────────

    def record_request(self, endpoint: str, method: str,
                       status_code: int, duration_ms: float) -> None:
        """Record an HTTP request."""
        with self._lock:
            key = f"{method} {endpoint}"
            is_error = status_code >= 500
            self._endpoints[key].record(duration_ms, is_error=is_error)
            self._counters["http_requests_total"] += 1
            if is_error:
                self._counters["http_errors_total"] += 1
            if status_code == 429:
                self._counters["http_rate_limited_total"] += 1

    def inc(self, name: str, amount: int = 1) -> None:
        """Increment a named counter."""
        with self._lock:
            self._counters[name] += amount

    # ─── Reading ──────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of all metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            endpoints = {}
            for key, bucket in self._endpoints.items():
                endpoints[key] = {
                    "count": bucket.count,
                    "errors": bucket.error_count,
                    "p50_ms": round(bucket.percentile(50), 1) if bucket.percentile(50) else None,
                    "p95_ms": round(bucket.percentile(95), 1) if bucket.percentile(95) else None,
                    "p99_ms": round(bucket.percentile(99), 1) if bucket.percentile(99) else None,
                }
            return {
                "uptime_seconds": round(uptime, 1),
                "counters": dict(self._counters),
                "endpoints": endpoints,
            }

    def prometheus_text(self) -> str:
        """Return metrics in Prometheus exposition format."""
        snap = self.snapshot()
        lines: list[str] = []
        lines.append(f"# HELP uptime_seconds Seconds since server start")
        lines.append(f"# TYPE uptime_seconds gauge")
        lines.append(f'uptime_seconds {snap["uptime_seconds"]}')

        for name, val in snap["counters"].items():
            safe = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {safe} counter")
            lines.append(f"{safe} {val}")

        for ep, stats in snap["endpoints"].items():
            safe = ep.replace(" ", "_").replace("/", "_").replace("{", "").replace("}", "")
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.5"}} {stats["p50_ms"] or 0}')
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.95"}} {stats["p95_ms"] or 0}')
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.99"}} {stats["p99_ms"] or 0}')
            lines.append(f'http_request_count{{endpoint="{ep}"}} {stats["count"]}')
            lines.append(f'http_request_errors{{endpoint="{ep}"}} {stats["errors"]}')

        return "\n".join(lines) + "\n"


# ─── Singleton ────────────────────────────────────────────────────────────

_collector: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
