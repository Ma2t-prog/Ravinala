"""
alerts_engine.py — Intelligent multi-condition alert system.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from .core import DataFetcher
from .technical import TechnicalIndicators


CONDITION_TYPES = [
    "price_above", "price_below",
    "price_crosses_above", "price_crosses_below",
    "rsi_above", "rsi_below",
    "rsi_crosses_above", "rsi_crosses_below",
    "macd_bullish", "macd_bearish",
    "price_above_sma", "price_below_sma",
    "volume_spike",
    "pct_change_above", "pct_change_below",
    "new_52w_high", "new_52w_low",
    "bb_breakout_upper", "bb_breakout_lower",
]


@dataclass
class AlertCondition:
    condition_type: str
    threshold: Optional[float] = None
    period: Optional[int] = None
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Alert:
    alert_id: str
    symbol: str
    name: str
    conditions: List[AlertCondition]
    logic: str = "ALL"   # 'ALL' (AND) | 'ANY' (OR)
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    triggered_at: Optional[str] = None
    trigger_count: int = 0
    note: str = ""

    def to_dict(self) -> Dict:
        return {
            "alert_id":    self.alert_id,
            "symbol":      self.symbol,
            "name":        self.name,
            "conditions":  [c.to_dict() for c in self.conditions],
            "logic":       self.logic,
            "active":      self.active,
            "created_at":  self.created_at,
            "triggered_at": self.triggered_at,
            "trigger_count": self.trigger_count,
            "note":        self.note,
        }


class AlertsEngine:
    """Multi-condition alert engine with Streamlit session state persistence."""

    STATE_KEY = "fa_alerts_v2"

    def __init__(self):
        if self.STATE_KEY not in st.session_state:
            st.session_state[self.STATE_KEY] = []

    @property
    def alerts(self) -> List[Dict]:
        return st.session_state.get(self.STATE_KEY, [])

    def add_alert(self, alert: Alert) -> None:
        """Add a new alert."""
        alerts = self.alerts.copy()
        alerts.append(alert.to_dict())
        st.session_state[self.STATE_KEY] = alerts

    def remove_alert(self, alert_id: str) -> None:
        """Remove alert by ID."""
        st.session_state[self.STATE_KEY] = [
            a for a in self.alerts if a["alert_id"] != alert_id
        ]

    def toggle_alert(self, alert_id: str) -> None:
        """Toggle active state of an alert."""
        alerts = self.alerts.copy()
        for a in alerts:
            if a["alert_id"] == alert_id:
                a["active"] = not a["active"]
        st.session_state[self.STATE_KEY] = alerts

    # ─────────────────────────────────────────────────────────────────────────
    # CONDITION EVALUATION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _evaluate_condition(condition: Dict, df: pd.DataFrame,
                              snapshot: Dict) -> bool:
        """Evaluate a single condition against current data."""
        ct = condition.get("condition_type", "")
        threshold = condition.get("threshold")
        period = condition.get("period", 14)

        price = snapshot.get("price", 0)
        prev_price = None

        try:
            if len(df) >= 2:
                prev_price = float(df["Close"].iloc[-2])
        except Exception:
            pass

        if ct == "price_above":
            return price > threshold if threshold else False
        if ct == "price_below":
            return price < threshold if threshold else False
        if ct == "price_crosses_above" and prev_price:
            return prev_price <= threshold <= price
        if ct == "price_crosses_below" and prev_price:
            return prev_price >= threshold >= price

        try:
            if ct in ("rsi_above", "rsi_below", "rsi_crosses_above", "rsi_crosses_below"):
                if len(df) < 15:
                    return False
                rsi_val = float(TechnicalIndicators.rsi(df["Close"], period or 14).iloc[-1])
                prev_rsi = float(TechnicalIndicators.rsi(df["Close"], period or 14).iloc[-2]) if len(df) >= 16 else rsi_val
                if ct == "rsi_above":
                    return rsi_val > threshold
                if ct == "rsi_below":
                    return rsi_val < threshold
                if ct == "rsi_crosses_above":
                    return prev_rsi <= threshold <= rsi_val
                if ct == "rsi_crosses_below":
                    return prev_rsi >= threshold >= rsi_val

            if ct in ("macd_bullish", "macd_bearish"):
                if len(df) < 30:
                    return False
                macd = TechnicalIndicators.macd(df["Close"])
                macd_val = float(macd["macd"].iloc[-1])
                signal_val = float(macd["macd_signal"].iloc[-1])
                prev_macd = float(macd["macd"].iloc[-2])
                prev_sig = float(macd["macd_signal"].iloc[-2])
                if ct == "macd_bullish":
                    return prev_macd <= prev_sig and macd_val > signal_val
                if ct == "macd_bearish":
                    return prev_macd >= prev_sig and macd_val < signal_val

            if ct in ("price_above_sma", "price_below_sma"):
                if len(df) < (period or 50):
                    return False
                sma_val = float(TechnicalIndicators.sma(df["Close"], period or 50).iloc[-1])
                return price > sma_val if ct == "price_above_sma" else price < sma_val

            if ct == "volume_spike":
                if len(df) < 21 or "Volume" not in df.columns:
                    return False
                avg_vol = float(df["Volume"].iloc[-21:-1].mean())
                curr_vol = float(df["Volume"].iloc[-1])
                return curr_vol > avg_vol * (threshold or 2.0)

            if ct == "pct_change_above" and prev_price:
                pct = (price - prev_price) / prev_price * 100
                return pct > threshold
            if ct == "pct_change_below" and prev_price:
                pct = (price - prev_price) / prev_price * 100
                return pct < threshold

            if ct == "new_52w_high":
                if len(df) < 252:
                    return False
                high_52w = float(df["High"].iloc[-252:].max())
                return price >= high_52w * 0.999

            if ct == "new_52w_low":
                if len(df) < 252:
                    return False
                low_52w = float(df["Low"].iloc[-252:].min())
                return price <= low_52w * 1.001

            if ct in ("bb_breakout_upper", "bb_breakout_lower"):
                if len(df) < 21:
                    return False
                bb = TechnicalIndicators.bollinger_bands(df["Close"])
                if ct == "bb_breakout_upper":
                    return price > float(bb["bb_upper"].iloc[-1])
                return price < float(bb["bb_lower"].iloc[-1])

        except Exception:
            pass

        return False

    def check_alerts(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """Check all active alerts and return triggered ones.

        Args:
            symbols: If provided, only check alerts for these symbols.

        Returns:
            List of triggered alert dicts.
        """
        triggered = []
        alerts = [a for a in self.alerts if a.get("active", True)]

        if symbols:
            alerts = [a for a in alerts if a["symbol"] in symbols]

        for alert in alerts:
            sym = alert["symbol"]
            try:
                df = DataFetcher.ohlcv(sym, "1d")
                snapshot = DataFetcher.snapshot(sym)
                if df.empty or not snapshot:
                    continue

                results = [
                    self._evaluate_condition(c, df, snapshot)
                    for c in alert.get("conditions", [])
                ]

                logic = alert.get("logic", "ALL")
                fired = all(results) if logic == "ALL" else any(results)

                if fired:
                    triggered.append({
                        **alert,
                        "triggered_now": True,
                        "price": snapshot.get("price"),
                        "change_pct": snapshot.get("change_pct"),
                    })
            except Exception:
                continue

        # Update trigger counts in session state
        if triggered:
            triggered_ids = {a["alert_id"] for a in triggered}
            updated = []
            for a in self.alerts:
                if a["alert_id"] in triggered_ids:
                    a["trigger_count"] = a.get("trigger_count", 0) + 1
                    a["triggered_at"] = datetime.now().isoformat()
                updated.append(a)
            st.session_state[self.STATE_KEY] = updated

        return triggered

    @staticmethod
    def build_simple_alert(
        symbol: str,
        alert_type: str,
        threshold: Optional[float] = None,
        period: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Alert:
        """Helper to quickly create a single-condition alert.

        Args:
            symbol: Ticker.
            alert_type: One of CONDITION_TYPES.
            threshold: Numeric threshold (price, RSI level, etc.).
            period: MA / RSI period if applicable.
            name: Display name.

        Returns:
            Alert object (not yet saved — call add_alert() to persist).
        """
        import uuid
        condition = AlertCondition(
            condition_type=alert_type,
            threshold=threshold,
            period=period,
        )
        auto_name = name or f"{symbol} — {alert_type.replace('_', ' ').title()}"
        if threshold:
            auto_name += f" @ {threshold}"

        return Alert(
            alert_id=str(uuid.uuid4())[:8],
            symbol=symbol,
            name=auto_name,
            conditions=[condition],
        )
