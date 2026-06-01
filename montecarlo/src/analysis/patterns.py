"""
patterns.py — 30+ pattern recognition: candlestick, chart patterns, divergences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .technical import TechnicalIndicators


@dataclass
class PatternResult:
    """Detected pattern metadata."""

    pattern: str
    category: str           # 'single' | 'double' | 'triple' | 'chart' | 'divergence'
    bias: str               # 'Bullish' | 'Bearish' | 'Neutral'
    confidence: float       # 0–1
    strength: str           # 'Weak' | 'Moderate' | 'Strong'
    timestamp: Optional[datetime]
    price: float
    bar_index: int
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    description: str = ""
    extra: Dict = field(default_factory=dict)


class PatternDetector:
    """Detect candlestick and chart patterns in OHLCV data."""

    # ─────────────────────────────────────────────────────────────────────────
    # CANDLESTICK HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _body(o: float, c: float) -> float:
        return abs(c - o)

    @staticmethod
    def _upper_shadow(o: float, h: float, c: float) -> float:
        return h - max(o, c)

    @staticmethod
    def _lower_shadow(o: float, l: float, c: float) -> float:
        return min(o, c) - l

    @staticmethod
    def _candle_range(h: float, l: float) -> float:
        return h - l if h != l else 1e-10

    # ─────────────────────────────────────────────────────────────────────────
    # SINGLE CANDLESTICK PATTERNS
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_single(self, df: pd.DataFrame,
                        lookback: int) -> List[PatternResult]:
        results: List[PatternResult] = []
        start = max(0, len(df) - lookback)

        for i in range(start, len(df)):
            o, h, l, c = (
                float(df["Open"].iloc[i]),
                float(df["High"].iloc[i]),
                float(df["Low"].iloc[i]),
                float(df["Close"].iloc[i]),
            )
            body = self._body(o, c)
            rng = self._candle_range(h, l)
            upper_sh = self._upper_shadow(o, h, c)
            lower_sh = self._lower_shadow(o, l, c)
            bullish = c >= o
            ts = df.index[i].to_pydatetime() if hasattr(df.index[i], "to_pydatetime") else None

            # Hammer (bullish reversal from bottom)
            if (
                lower_sh >= 2 * body
                and upper_sh <= 0.1 * rng
                and rng > 0
            ):
                bias = "Bullish"
                conf = min(lower_sh / rng, 1.0)
                results.append(PatternResult(
                    pattern="Hammer", category="single", bias=bias,
                    confidence=round(conf, 2),
                    strength="Strong" if conf > 0.7 else "Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Long lower shadow, small body at top. Bullish reversal signal.",
                ))

            # Shooting Star (bearish reversal from top)
            if (
                upper_sh >= 2 * body
                and lower_sh <= 0.1 * rng
                and rng > 0
            ):
                results.append(PatternResult(
                    pattern="Shooting Star", category="single", bias="Bearish",
                    confidence=round(min(upper_sh / rng, 1.0), 2),
                    strength="Strong" if upper_sh / rng > 0.7 else "Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Long upper shadow, small body at bottom. Bearish reversal signal.",
                ))

            # Doji
            if body <= 0.05 * rng and rng > 0:
                if lower_sh > 2 * upper_sh:
                    name, bias = "Dragonfly Doji", "Bullish"
                    desc = "Open ≈ Close at high, long lower shadow. Bullish reversal."
                elif upper_sh > 2 * lower_sh:
                    name, bias = "Gravestone Doji", "Bearish"
                    desc = "Open ≈ Close at low, long upper shadow. Bearish reversal."
                else:
                    name, bias = "Doji", "Neutral"
                    desc = "Open ≈ Close. Indecision candle."
                results.append(PatternResult(
                    pattern=name, category="single", bias=bias,
                    confidence=0.65, strength="Moderate",
                    timestamp=ts, price=c, bar_index=i, description=desc,
                ))

            # Marubozu Bullish
            if body >= 0.9 * rng and bullish and upper_sh < 0.05 * rng and lower_sh < 0.05 * rng:
                results.append(PatternResult(
                    pattern="Bullish Marubozu", category="single", bias="Bullish",
                    confidence=0.80, strength="Strong",
                    timestamp=ts, price=c, bar_index=i,
                    description="Large bullish body, nearly no shadows. Strong buying pressure.",
                ))

            # Marubozu Bearish
            if body >= 0.9 * rng and not bullish and upper_sh < 0.05 * rng and lower_sh < 0.05 * rng:
                results.append(PatternResult(
                    pattern="Bearish Marubozu", category="single", bias="Bearish",
                    confidence=0.80, strength="Strong",
                    timestamp=ts, price=c, bar_index=i,
                    description="Large bearish body, nearly no shadows. Strong selling pressure.",
                ))

            # Spinning Top
            if (
                upper_sh >= body
                and lower_sh >= body
                and body < 0.3 * rng
            ):
                results.append(PatternResult(
                    pattern="Spinning Top", category="single", bias="Neutral",
                    confidence=0.50, strength="Weak",
                    timestamp=ts, price=c, bar_index=i,
                    description="Small body with long shadows. Indecision.",
                ))

            # Belt Hold Bullish
            if bullish and lower_sh <= 0.02 * rng and body >= 0.6 * rng:
                results.append(PatternResult(
                    pattern="Bullish Belt Hold", category="single", bias="Bullish",
                    confidence=0.70, strength="Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Opens at low, closes near high. Bullish signal.",
                ))

            # Belt Hold Bearish
            if not bullish and upper_sh <= 0.02 * rng and body >= 0.6 * rng:
                results.append(PatternResult(
                    pattern="Bearish Belt Hold", category="single", bias="Bearish",
                    confidence=0.70, strength="Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Opens at high, closes near low. Bearish signal.",
                ))

            # Inverted Hammer
            if (
                upper_sh >= 2 * body
                and lower_sh <= 0.1 * rng
                and rng > 0
                and bullish
            ):
                results.append(PatternResult(
                    pattern="Inverted Hammer", category="single", bias="Bullish",
                    confidence=0.60, strength="Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Long upper shadow in downtrend. Potential reversal.",
                ))

            # Hanging Man (like Hammer but in uptrend — context-blind here)
            if (
                lower_sh >= 2 * body
                and upper_sh <= 0.1 * rng
                and not bullish
                and rng > 0
            ):
                results.append(PatternResult(
                    pattern="Hanging Man", category="single", bias="Bearish",
                    confidence=0.60, strength="Moderate",
                    timestamp=ts, price=c, bar_index=i,
                    description="Long lower shadow, bearish body. Bearish reversal when at top.",
                ))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # DOUBLE CANDLESTICK PATTERNS
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_double(self, df: pd.DataFrame,
                        lookback: int) -> List[PatternResult]:
        results: List[PatternResult] = []
        start = max(1, len(df) - lookback)

        for i in range(start, len(df)):
            o1, h1, l1, c1 = (
                float(df["Open"].iloc[i - 1]), float(df["High"].iloc[i - 1]),
                float(df["Low"].iloc[i - 1]),  float(df["Close"].iloc[i - 1]),
            )
            o2, h2, l2, c2 = (
                float(df["Open"].iloc[i]), float(df["High"].iloc[i]),
                float(df["Low"].iloc[i]), float(df["Close"].iloc[i]),
            )
            ts = df.index[i].to_pydatetime() if hasattr(df.index[i], "to_pydatetime") else None
            body1 = abs(c1 - o1)
            body2 = abs(c2 - o2)

            # Bullish Engulfing
            if (
                c1 < o1          # candle 1 is bearish
                and c2 > o2      # candle 2 is bullish
                and o2 <= c1     # opens below or at prior close
                and c2 >= o1     # closes above or at prior open
            ):
                conf = min((body2 / body1), 2.0) / 2.0 if body1 > 0 else 0.7
                results.append(PatternResult(
                    pattern="Bullish Engulfing", category="double", bias="Bullish",
                    confidence=round(min(conf, 0.95), 2),
                    strength="Strong" if conf > 0.7 else "Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Second candle fully engulfs prior bearish candle. Strong reversal.",
                ))

            # Bearish Engulfing
            if (
                c1 > o1
                and c2 < o2
                and o2 >= c1
                and c2 <= o1
            ):
                conf = min((body2 / body1), 2.0) / 2.0 if body1 > 0 else 0.7
                results.append(PatternResult(
                    pattern="Bearish Engulfing", category="double", bias="Bearish",
                    confidence=round(min(conf, 0.95), 2),
                    strength="Strong" if conf > 0.7 else "Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Second candle fully engulfs prior bullish candle. Strong reversal.",
                ))

            # Bullish Harami
            if (
                c1 < o1
                and c2 > o2
                and o2 > c1 and c2 < o1
            ):
                results.append(PatternResult(
                    pattern="Bullish Harami", category="double", bias="Bullish",
                    confidence=0.65, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Small bullish candle inside prior large bearish candle.",
                ))

            # Bearish Harami
            if (
                c1 > o1
                and c2 < o2
                and o2 < c1 and c2 > o1
            ):
                results.append(PatternResult(
                    pattern="Bearish Harami", category="double", bias="Bearish",
                    confidence=0.65, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Small bearish candle inside prior large bullish candle.",
                ))

            # Piercing Line
            if (
                c1 < o1
                and c2 > o2
                and o2 < l1
                and c2 > (o1 + c1) / 2
                and c2 < o1
            ):
                results.append(PatternResult(
                    pattern="Piercing Line", category="double", bias="Bullish",
                    confidence=0.72, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Bullish candle pierces into prior bearish body past midpoint.",
                ))

            # Dark Cloud Cover
            if (
                c1 > o1
                and c2 < o2
                and o2 > h1
                and c2 < (o1 + c1) / 2
                and c2 > o1
            ):
                results.append(PatternResult(
                    pattern="Dark Cloud Cover", category="double", bias="Bearish",
                    confidence=0.72, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Bearish candle opens above prior high, closes below midpoint.",
                ))

            # Tweezer Top
            if abs(h1 - h2) / max(h1, h2, 1) < 0.001 and c1 > o1 and c2 < o2:
                results.append(PatternResult(
                    pattern="Tweezer Top", category="double", bias="Bearish",
                    confidence=0.68, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Two candles with same high. Bearish reversal at resistance.",
                ))

            # Tweezer Bottom
            if abs(l1 - l2) / max(l1, l2, 1) < 0.001 and c1 < o1 and c2 > o2:
                results.append(PatternResult(
                    pattern="Tweezer Bottom", category="double", bias="Bullish",
                    confidence=0.68, strength="Moderate",
                    timestamp=ts, price=c2, bar_index=i,
                    description="Two candles with same low. Bullish reversal at support.",
                ))

            # Bullish Kicker
            if c1 < o1 and o2 > o1 and c2 > o2:
                gap_size = (o2 - o1) / o1
                if gap_size > 0.005:
                    results.append(PatternResult(
                        pattern="Bullish Kicker", category="double", bias="Bullish",
                        confidence=0.85, strength="Strong",
                        timestamp=ts, price=c2, bar_index=i,
                        description="Gap up after bearish candle. Very strong bullish signal.",
                    ))

            # Bearish Kicker
            if c1 > o1 and o2 < o1 and c2 < o2:
                gap_size = (o1 - o2) / o1
                if gap_size > 0.005:
                    results.append(PatternResult(
                        pattern="Bearish Kicker", category="double", bias="Bearish",
                        confidence=0.85, strength="Strong",
                        timestamp=ts, price=c2, bar_index=i,
                        description="Gap down after bullish candle. Very strong bearish signal.",
                    ))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # TRIPLE CANDLESTICK PATTERNS
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_triple(self, df: pd.DataFrame,
                        lookback: int) -> List[PatternResult]:
        results: List[PatternResult] = []
        start = max(2, len(df) - lookback)

        for i in range(start, len(df)):
            candles = []
            for j in (i - 2, i - 1, i):
                candles.append((
                    float(df["Open"].iloc[j]),
                    float(df["High"].iloc[j]),
                    float(df["Low"].iloc[j]),
                    float(df["Close"].iloc[j]),
                ))
            (o1, h1, l1, c1), (o2, h2, l2, c2), (o3, h3, l3, c3) = candles
            ts = df.index[i].to_pydatetime() if hasattr(df.index[i], "to_pydatetime") else None

            # Morning Star
            if (
                c1 < o1  # bearish
                and abs(c2 - o2) < abs(c1 - o1) * 0.35  # small body
                and c3 > o3  # bullish
                and c3 > (o1 + c1) / 2  # closes above mid of first candle
            ):
                results.append(PatternResult(
                    pattern="Morning Star", category="triple", bias="Bullish",
                    confidence=0.82, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Three-candle bullish reversal: bearish, small, bullish.",
                ))

            # Evening Star
            if (
                c1 > o1
                and abs(c2 - o2) < abs(c1 - o1) * 0.35
                and c3 < o3
                and c3 < (o1 + c1) / 2
            ):
                results.append(PatternResult(
                    pattern="Evening Star", category="triple", bias="Bearish",
                    confidence=0.82, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Three-candle bearish reversal: bullish, small, bearish.",
                ))

            # Three White Soldiers
            if (
                c1 > o1 and c2 > o2 and c3 > o3
                and c2 > c1 and c3 > c2
                and o2 > o1 and o2 < c1
                and o3 > o2 and o3 < c2
            ):
                results.append(PatternResult(
                    pattern="Three White Soldiers", category="triple", bias="Bullish",
                    confidence=0.88, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Three consecutive bullish candles, each closing higher.",
                ))

            # Three Black Crows
            if (
                c1 < o1 and c2 < o2 and c3 < o3
                and c2 < c1 and c3 < c2
                and o2 < o1 and o2 > c1
                and o3 < o2 and o3 > c2
            ):
                results.append(PatternResult(
                    pattern="Three Black Crows", category="triple", bias="Bearish",
                    confidence=0.88, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Three consecutive bearish candles, each closing lower.",
                ))

            # Three Inside Up
            if (
                c1 < o1  # bearish
                and c2 > o2 and o2 > c1 and c2 < o1  # bullish harami inside
                and c3 > c2 and c3 > o1  # third closes above first open
            ):
                results.append(PatternResult(
                    pattern="Three Inside Up", category="triple", bias="Bullish",
                    confidence=0.78, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Bullish harami confirmed by third bullish candle.",
                ))

            # Three Inside Down
            if (
                c1 > o1
                and c2 < o2 and o2 < c1 and c2 > o1
                and c3 < c2 and c3 < o1
            ):
                results.append(PatternResult(
                    pattern="Three Inside Down", category="triple", bias="Bearish",
                    confidence=0.78, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Bearish harami confirmed by third bearish candle.",
                ))

            # Abandoned Baby Bullish (gap doji)
            if (
                c1 < o1
                and abs(c2 - o2) < abs(c1 - o1) * 0.1  # doji
                and l2 > l1  # gap below
                and c3 > o3
                and l3 > h2  # gap above
            ):
                results.append(PatternResult(
                    pattern="Abandoned Baby (Bullish)", category="triple", bias="Bullish",
                    confidence=0.90, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Isolated doji gap between bearish and bullish candles. Very rare, very reliable.",
                ))

            # Abandoned Baby Bearish
            if (
                c1 > o1
                and abs(c2 - o2) < abs(c1 - o1) * 0.1
                and h2 < h1
                and c3 < o3
                and h3 < l2
            ):
                results.append(PatternResult(
                    pattern="Abandoned Baby (Bearish)", category="triple", bias="Bearish",
                    confidence=0.90, strength="Strong",
                    timestamp=ts, price=c3, bar_index=i,
                    description="Isolated doji gap between bullish and bearish candles.",
                ))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # CHART PATTERNS (geometric)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _find_pivots(series: pd.Series, window: int = 5) -> pd.Series:
        """Returns a boolean Series where True indicates a local pivot (high or low)."""
        highs = (series == series.rolling(window * 2 + 1, center=True).max())
        lows = (series == series.rolling(window * 2 + 1, center=True).min())
        return highs | lows

    def detect_chart_patterns(self, df: pd.DataFrame,
                               min_bars: int = 15,
                               max_bars: int = 200) -> List[PatternResult]:
        """Detect geometric chart patterns on the price series.

        Args:
            df: OHLCV DataFrame.
            min_bars: Minimum pattern width in bars.
            max_bars: Maximum pattern width in bars.

        Returns:
            List of PatternResult objects.
        """
        results: List[PatternResult] = []
        closes = df["Close"]
        n = len(df)

        if n < min_bars + 5:
            return results

        # Find swing highs and lows
        window = 3
        swing_high_idx = []
        swing_low_idx = []
        for i in range(window, n - window):
            if float(df["High"].iloc[i]) == float(df["High"].iloc[i - window: i + window + 1].max()):
                swing_high_idx.append(i)
            if float(df["Low"].iloc[i]) == float(df["Low"].iloc[i - window: i + window + 1].min()):
                swing_low_idx.append(i)

        if len(swing_high_idx) < 2 or len(swing_low_idx) < 2:
            return results

        last_close = float(closes.iloc[-1])
        ts = df.index[-1].to_pydatetime() if hasattr(df.index[-1], "to_pydatetime") else None

        # ── Double Top ──────────────────────────────────────────────────────
        if len(swing_high_idx) >= 2:
            h1_i, h2_i = swing_high_idx[-2], swing_high_idx[-1]
            h1, h2 = float(df["High"].iloc[h1_i]), float(df["High"].iloc[h2_i])
            if (
                min_bars <= h2_i - h1_i <= max_bars
                and abs(h1 - h2) / h1 < 0.03
            ):
                neckline = float(closes.iloc[h1_i:h2_i].min())
                target = neckline - (h1 - neckline)
                results.append(PatternResult(
                    pattern="Double Top", category="chart", bias="Bearish",
                    confidence=0.75, strength="Strong",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Two peaks at similar levels (~{h1:.2f}). Bearish reversal. Target: {target:.2f}",
                ))

        # ── Double Bottom ────────────────────────────────────────────────────
        if len(swing_low_idx) >= 2:
            l1_i, l2_i = swing_low_idx[-2], swing_low_idx[-1]
            lo1, lo2 = float(df["Low"].iloc[l1_i]), float(df["Low"].iloc[l2_i])
            if (
                min_bars <= l2_i - l1_i <= max_bars
                and abs(lo1 - lo2) / lo1 < 0.03
            ):
                neckline = float(closes.iloc[l1_i:l2_i].max())
                target = neckline + (neckline - lo1)
                results.append(PatternResult(
                    pattern="Double Bottom", category="chart", bias="Bullish",
                    confidence=0.75, strength="Strong",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Two troughs at similar levels (~{lo1:.2f}). Bullish reversal. Target: {target:.2f}",
                ))

        # ── Head and Shoulders ───────────────────────────────────────────────
        if len(swing_high_idx) >= 3:
            ls_i, h_i, rs_i = swing_high_idx[-3], swing_high_idx[-2], swing_high_idx[-1]
            ls, head, rs = (
                float(df["High"].iloc[ls_i]),
                float(df["High"].iloc[h_i]),
                float(df["High"].iloc[rs_i]),
            )
            if (
                head > ls and head > rs
                and abs(ls - rs) / head < 0.05
                and min_bars <= rs_i - ls_i <= max_bars
            ):
                neckline = float(closes.iloc[ls_i:rs_i].min())
                target = neckline - (head - neckline)
                results.append(PatternResult(
                    pattern="Head and Shoulders", category="chart", bias="Bearish",
                    confidence=0.82, strength="Strong",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Classic H&S. Neckline: {neckline:.2f}. Target: {target:.2f}",
                ))

        # ── Inverse Head and Shoulders ───────────────────────────────────────
        if len(swing_low_idx) >= 3:
            ls_i, h_i, rs_i = swing_low_idx[-3], swing_low_idx[-2], swing_low_idx[-1]
            ls, head, rs = (
                float(df["Low"].iloc[ls_i]),
                float(df["Low"].iloc[h_i]),
                float(df["Low"].iloc[rs_i]),
            )
            if (
                head < ls and head < rs
                and abs(ls - rs) / abs(head) < 0.05
                and min_bars <= rs_i - ls_i <= max_bars
            ):
                neckline = float(closes.iloc[ls_i:rs_i].max())
                target = neckline + (neckline - head)
                results.append(PatternResult(
                    pattern="Inverse Head and Shoulders", category="chart", bias="Bullish",
                    confidence=0.82, strength="Strong",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Inverse H&S. Neckline: {neckline:.2f}. Target: {target:.2f}",
                ))

        # ── Ascending Triangle ────────────────────────────────────────────────
        if len(swing_high_idx) >= 2 and len(swing_low_idx) >= 2:
            recent_highs = [float(df["High"].iloc[i]) for i in swing_high_idx[-3:]]
            recent_lows = [float(df["Low"].iloc[i]) for i in swing_low_idx[-3:]]
            if (
                len(recent_highs) >= 2
                and abs(recent_highs[-1] - recent_highs[-2]) / recent_highs[-1] < 0.02
                and len(recent_lows) >= 2
                and recent_lows[-1] > recent_lows[-2]
            ):
                resistance = np.mean(recent_highs[-2:])
                target = resistance + (resistance - recent_lows[-1])
                results.append(PatternResult(
                    pattern="Ascending Triangle", category="chart", bias="Bullish",
                    confidence=0.72, strength="Moderate",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Flat resistance ({resistance:.2f}) + rising lows. Bullish breakout expected.",
                ))

        # ── Descending Triangle ───────────────────────────────────────────────
        if len(swing_high_idx) >= 2 and len(swing_low_idx) >= 2:
            recent_highs = [float(df["High"].iloc[i]) for i in swing_high_idx[-3:]]
            recent_lows = [float(df["Low"].iloc[i]) for i in swing_low_idx[-3:]]
            if (
                len(recent_lows) >= 2
                and abs(recent_lows[-1] - recent_lows[-2]) / recent_lows[-1] < 0.02
                and len(recent_highs) >= 2
                and recent_highs[-1] < recent_highs[-2]
            ):
                support = np.mean(recent_lows[-2:])
                target = support - (recent_highs[-1] - support)
                results.append(PatternResult(
                    pattern="Descending Triangle", category="chart", bias="Bearish",
                    confidence=0.72, strength="Moderate",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Flat support ({support:.2f}) + falling highs. Bearish breakout expected.",
                ))

        # ── Bull Flag ─────────────────────────────────────────────────────────
        if len(closes) >= 30:
            pole_ret = (float(closes.iloc[-30]) - float(closes.iloc[-40])) / float(closes.iloc[-40]) if len(closes) >= 40 else 0
            flag_ret = (float(closes.iloc[-1]) - float(closes.iloc[-30])) / float(closes.iloc[-30])
            if pole_ret > 0.05 and -0.08 < flag_ret < 0:
                target = float(closes.iloc[-1]) * (1 + pole_ret)
                results.append(PatternResult(
                    pattern="Bull Flag", category="chart", bias="Bullish",
                    confidence=0.70, strength="Moderate",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Strong upswing (pole) followed by mild pullback. Target: {target:.2f}",
                ))

        # ── Bear Flag ─────────────────────────────────────────────────────────
        if len(closes) >= 30:
            pole_ret = (float(closes.iloc[-40]) - float(closes.iloc[-30])) / float(closes.iloc[-40]) if len(closes) >= 40 else 0
            flag_ret = (float(closes.iloc[-1]) - float(closes.iloc[-30])) / float(closes.iloc[-30])
            if pole_ret > 0.05 and 0 < flag_ret < 0.08:
                target = float(closes.iloc[-1]) * (1 - pole_ret)
                results.append(PatternResult(
                    pattern="Bear Flag", category="chart", bias="Bearish",
                    confidence=0.70, strength="Moderate",
                    timestamp=ts, price=last_close, bar_index=n - 1,
                    target=target,
                    description=f"Strong downswing followed by mild bounce. Target: {target:.2f}",
                ))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # DIVERGENCES
    # ─────────────────────────────────────────────────────────────────────────

    def detect_divergences(self, df: pd.DataFrame,
                            indicator: str = "RSI",
                            window: int = 5) -> List[PatternResult]:
        """Detect price vs indicator divergences.

        Supports RSI, MACD, OBV, MFI, CCI.

        Args:
            indicator: Name of indicator to use.
            window: Swing pivot window size.

        Returns:
            List of PatternResult describing each divergence.
        """
        closes = df["Close"]
        n = len(df)
        results: List[PatternResult] = []

        if n < 30:
            return results

        # Compute indicator
        if indicator == "RSI":
            ind = TechnicalIndicators.rsi(closes).values
        elif indicator == "MACD":
            ind = TechnicalIndicators.macd(closes)["macd"].values
        elif indicator == "OBV":
            ind = TechnicalIndicators.obv(df).values
        elif indicator == "MFI":
            ind = TechnicalIndicators.mfi(df).values
        elif indicator == "CCI":
            ind = TechnicalIndicators.cci(df).values
        else:
            ind = TechnicalIndicators.rsi(closes).values

        price = closes.values

        # Find pivot lows and highs
        def find_pivots(series: np.ndarray) -> tuple[List[int], List[int]]:
            lows, highs = [], []
            for i in range(window, n - window):
                seg = series[i - window: i + window + 1]
                if not np.any(np.isnan(seg)):
                    if series[i] == seg.min():
                        lows.append(i)
                    if series[i] == seg.max():
                        highs.append(i)
            return lows, highs

        price_lows, price_highs = find_pivots(price)
        ind_lows, ind_highs = find_pivots(ind)

        ts = df.index[-1].to_pydatetime() if hasattr(df.index[-1], "to_pydatetime") else None

        # Regular Bullish: price makes lower low, indicator makes higher low
        if len(price_lows) >= 2 and len(ind_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            il1 = min(ind_lows, key=lambda x: abs(x - pl1))
            il2 = min(ind_lows, key=lambda x: abs(x - pl2))
            if (
                price[pl2] < price[pl1]
                and ind[il2] > ind[il1]
                and abs(pl2 - il2) <= window * 2
            ):
                results.append(PatternResult(
                    pattern=f"Regular Bullish Divergence ({indicator})",
                    category="divergence", bias="Bullish",
                    confidence=0.78, strength="Strong",
                    timestamp=ts, price=float(closes.iloc[-1]), bar_index=n - 1,
                    description=f"Price lower low + {indicator} higher low. Bullish reversal signal.",
                ))

        # Regular Bearish: price makes higher high, indicator makes lower high
        if len(price_highs) >= 2 and len(ind_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            ih1 = min(ind_highs, key=lambda x: abs(x - ph1))
            ih2 = min(ind_highs, key=lambda x: abs(x - ph2))
            if (
                price[ph2] > price[ph1]
                and ind[ih2] < ind[ih1]
                and abs(ph2 - ih2) <= window * 2
            ):
                results.append(PatternResult(
                    pattern=f"Regular Bearish Divergence ({indicator})",
                    category="divergence", bias="Bearish",
                    confidence=0.78, strength="Strong",
                    timestamp=ts, price=float(closes.iloc[-1]), bar_index=n - 1,
                    description=f"Price higher high + {indicator} lower high. Bearish reversal signal.",
                ))

        # Hidden Bullish: price higher low, indicator lower low
        if len(price_lows) >= 2 and len(ind_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            il1 = min(ind_lows, key=lambda x: abs(x - pl1))
            il2 = min(ind_lows, key=lambda x: abs(x - pl2))
            if (
                price[pl2] > price[pl1]
                and ind[il2] < ind[il1]
                and abs(pl2 - il2) <= window * 2
            ):
                results.append(PatternResult(
                    pattern=f"Hidden Bullish Divergence ({indicator})",
                    category="divergence", bias="Bullish",
                    confidence=0.65, strength="Moderate",
                    timestamp=ts, price=float(closes.iloc[-1]), bar_index=n - 1,
                    description=f"Price higher low + {indicator} lower low. Continuation signal in uptrend.",
                ))

        # Hidden Bearish: price lower high, indicator higher high
        if len(price_highs) >= 2 and len(ind_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            ih1 = min(ind_highs, key=lambda x: abs(x - ph1))
            ih2 = min(ind_highs, key=lambda x: abs(x - ph2))
            if (
                price[ph2] < price[ph1]
                and ind[ih2] > ind[ih1]
                and abs(ph2 - ih2) <= window * 2
            ):
                results.append(PatternResult(
                    pattern=f"Hidden Bearish Divergence ({indicator})",
                    category="divergence", bias="Bearish",
                    confidence=0.65, strength="Moderate",
                    timestamp=ts, price=float(closes.iloc[-1]), bar_index=n - 1,
                    description=f"Price lower high + {indicator} higher high. Continuation signal in downtrend.",
                ))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def detect_all(self, df: pd.DataFrame,
                   lookback: int = 60) -> List[PatternResult]:
        """Scan the last N bars for all candlestick patterns.

        Args:
            df: OHLCV DataFrame.
            lookback: Number of bars to scan.

        Returns:
            List of PatternResult sorted by confidence desc.
        """
        if df.empty or len(df) < 3:
            return []

        results: List[PatternResult] = []
        results.extend(self._detect_single(df, lookback))
        results.extend(self._detect_double(df, lookback))
        results.extend(self._detect_triple(df, lookback))

        # Deduplicate: keep highest-confidence per (pattern, bar_index)
        seen: Dict[tuple, PatternResult] = {}
        for r in results:
            key = (r.pattern, r.bar_index)
            if key not in seen or r.confidence > seen[key].confidence:
                seen[key] = r

        return sorted(seen.values(), key=lambda x: -x.confidence)

    def detect_all_with_chart(self, df: pd.DataFrame,
                               lookback: int = 60) -> List[PatternResult]:
        """Detect all candlestick + chart patterns."""
        candle = self.detect_all(df, lookback)
        chart = self.detect_chart_patterns(df)
        divs = self.detect_divergences(df, "RSI")
        return sorted(candle + chart + divs, key=lambda x: -x.confidence)
