"""
Number, date, and currency formatting utilities for GenesiX.

Provides consistent formatting for display in Streamlit dashboard.
"""

from typing import Union
from datetime import datetime
import pandas as pd
import numpy as np


def format_currency(
    value: float | None,
    currency: str = "EUR",
    precision: int = 2,
    sign: bool = False,
) -> str:
    """
    Format a number as currency string.
    
    Args:
        value: Numeric value to format.
        currency: Currency code (USD, EUR, GBP, etc.)
        precision: Decimal places (default 2).
        sign: Include +/- sign (default False).
    
    Returns:
        Formatted currency string (e.g., "€1,234.56").
    """
    if value is None or np.isnan(value):
        return "N/A"
    
    from .constants import CURRENCY_SYMBOLS
    
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    sign_str = "+" if sign and value > 0 else ""
    
    return f"{sign_str}{symbol}{value:,.{precision}f}"


def format_percentage(
    value: float | None,
    precision: int = 2,
    sign: bool = True,
) -> str:
    """
    Format a decimal as percentage string.
    
    Args:
        value: Decimal value (0.05 → "5.00%").
        precision: Decimal places.
        sign: Include +/- sign.
    
    Returns:
        Formatted percentage (e.g., "+5.25%").
    """
    if value is None or np.isnan(value):
        return "N/A"
    
    pct_value = value * 100
    sign_str = "+" if sign and pct_value > 0 else ""
    
    return f"{sign_str}{pct_value:.{precision}f}%"


def format_number(
    value: float | None,
    precision: int = 2,
    suffix: str = "",
) -> str:
    """
    Format a number with thousand separators.
    
    Args:
        value: Numeric value.
        precision: Decimal places.
        suffix: Suffix (e.g., "M", "B" for millions/billions).
    
    Returns:
        Formatted number string.
    """
    if value is None or np.isnan(value):
        return "N/A"
    
    if suffix.upper() == "B":
        return f"{value / 1e9:,.{precision}f}B"
    elif suffix.upper() == "M":
        return f"{value / 1e6:,.{precision}f}M"
    elif suffix.upper() == "K":
        return f"{value / 1e3:,.{precision}f}K"
    else:
        return f"{value:,.{precision}f}{suffix}"


def format_date(date_val: Union[str, datetime, pd.Timestamp], fmt: str = "%Y-%m-%d") -> str:
    """
    Format a date/timestamp string.
    
    Args:
        date_val: Date value (string, datetime, or Timestamp).
        fmt: Strftime format string.
    
    Returns:
        Formatted date string.
    """
    if isinstance(date_val, str):
        try:
            date_val = pd.to_datetime(date_val)
        except:
            return date_val
    
    if isinstance(date_val, pd.Timestamp):
        return date_val.strftime(fmt)
    elif isinstance(date_val, datetime):
        return date_val.strftime(fmt)
    
    return str(date_val)


def format_large_number(value: float | None) -> str:
    """
    Format large numbers with smart suffix (M, B, T).
    
    Args:
        value: Numeric value.
    
    Returns:
        Formatted string (e.g., "1.5B").
    """
    if value is None or np.isnan(value):
        return "N/A"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1e12:
        return f"{sign}{abs_value / 1e12:.1f}T"
    elif abs_value >= 1e9:
        return f"{sign}{abs_value / 1e9:.1f}B"
    elif abs_value >= 1e6:
        return f"{sign}{abs_value / 1e6:.1f}M"
    elif abs_value >= 1e3:
        return f"{sign}{abs_value / 1e3:.1f}K"
    else:
        return f"{sign}{abs_value:.0f}"


def color_code_performance(value: float | None) -> tuple[str, str]:
    """
    Return color and emoji for performance visualization.
    
    Args:
        value: Performance value (typically percentage as decimal).
    
    Returns:
        Tuple of (color_hex, emoji).
    """
    if value is None:
        return "#888888", "[--]"
    
    if value > 0.05:
        return "#00B050", "[OK]"  # Strong green
    elif value > 0.01:
        return "#70AD47", ""  # Light green
    elif value > -0.01:
        return "#808080", "[--]"  # Neutral
    elif value > -0.05:
        return "#FF6B6B", ""  # Light red
    else:
        return "#FF0000", "[ERR]"  # Strong red


def format_investment_outcome(
    initial_investment: float,
    return_pct: float,
    currency: str = "EUR",
) -> dict[str, str]:
    """
    Format investment outcome for display.
    
    Args:
        initial_investment: Initial amount invested.
        return_pct: Return as percentage (0.05 for 5%).
        currency: Currency code.
    
    Returns:
        Dictionary with formatted strings for display.
    """
    final_value = initial_investment * (1 + return_pct)
    profit_loss = final_value - initial_investment
    
    return {
        "initial": format_currency(initial_investment, currency),
        "final": format_currency(final_value, currency),
        "profit_loss": format_currency(profit_loss, currency, sign=True),
        "return_pct": format_percentage(return_pct, sign=True),
        "color": color_code_performance(return_pct)[0],
    }


def format_risk_metrics(
    value: float | None,
    metric_type: str = "var",
) -> str:
    """
    Format risk metrics (VaR, CVaR, volatility, Sharpe, etc.).
    
    Args:
        value: Metric value.
        metric_type: Type of metric (var, cvar, volatility, sharpe).
    
    Returns:
        Formatted string appropriate for the metric type.
    """
    if value is None or np.isnan(value):
        return "N/A"
    
    if metric_type in ["var", "cvar"]:
        # VaR/CVaR: typically negative (loss)
        return format_currency(value)
    elif metric_type == "volatility":
        # Volatility: annualized %
        return format_percentage(value)
    elif metric_type == "sharpe":
        # Sharpe ratio: decimal
        return f"{value:.2f}x"
    elif metric_type == "correlation":
        # Correlation: -1 to 1
        return f"{value:.3f}"
    else:
        return format_number(value)


def format_probability(prob: float | None, as_pct: bool = True) -> str:
    """
    Format probability value.
    
    Args:
        prob: Probability (0.0 to 1.0).
        as_pct: Format as percentage if True.
    
    Returns:
        Formatted probability string.
    """
    if prob is None or np.isnan(prob):
        return "N/A"
    
    # Clamp to valid range
    prob = max(0.0, min(1.0, prob))
    
    if as_pct:
        return f"{prob * 100:.1f}%"
    else:
        return f"{prob:.3f}"


# Convenience: Create a formatter class for Streamlit displays
class MetricFormatter:
    """Formatter for KPI cards and metrics tables."""
    
    @staticmethod
    def kpi_card(label: str, value: float, metric_type: str = "number", currency: str = "EUR") -> dict:
        """
        Create a formatted KPI card data.
        
        Args:
            label: Card label.
            value: Numeric value.
            metric_type: Type of metric.
            currency: Currency if applicable.
        
        Returns:
            Dictionary suitable for st.metric() call.
        """
        if metric_type == "currency":
            formatted = format_currency(value, currency)
        elif metric_type == "percentage":
            formatted = format_percentage(value)
        elif metric_type == "number":
            formatted = format_large_number(value)
        else:
            formatted = format_number(value)
        
        delta = None
        delta_color = "normal"
        
        if not np.isnan(value):
            if value > 0:
                delta = format_percentage(abs(value))
                delta_color = "off" if metric_type == "currency" else "normal"
        
        return {
            "label": label,
            "value": formatted,
            "delta": delta,
            "delta_color": delta_color,
        }
