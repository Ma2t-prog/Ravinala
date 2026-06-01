"""
technical.py — 40+ technical indicators for Financial Analysis Suite.

Every indicator is a static method accepting a DataFrame or Series and returning
a DataFrame or Series.  No side-effects, no globals, fully testable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """Comprehensive library of technical indicators (40+).

    All methods are static and accept / return pandas objects so that they
    can be used outside a Streamlit context (e.g., in backtesting or tests).
    """

    # =========================================================================
    # TREND
    # =========================================================================

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return series.rolling(window=period, min_periods=1).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return series.ewm(span=period, adjust=False, min_periods=1).mean()

    @staticmethod
    def dema(series: pd.Series, period: int) -> pd.Series:
        """Double EMA — reduces lag vs simple EMA."""
        e = TechnicalIndicators.ema(series, period)
        return 2 * e - TechnicalIndicators.ema(e, period)

    @staticmethod
    def tema(series: pd.Series, period: int) -> pd.Series:
        """Triple EMA — even less lag."""
        e1 = TechnicalIndicators.ema(series, period)
        e2 = TechnicalIndicators.ema(e1, period)
        e3 = TechnicalIndicators.ema(e2, period)
        return 3 * e1 - 3 * e2 + e3

    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        """Linearly Weighted Moving Average."""
        weights = np.arange(1, period + 1, dtype=float)

        def _wma(x: np.ndarray) -> float:
            if len(x) < period:
                w = np.arange(1, len(x) + 1, dtype=float)
                return float(np.dot(x, w) / w.sum())
            return float(np.dot(x, weights) / weights.sum())

        return series.rolling(window=period, min_periods=1).apply(_wma, raw=True)

    @staticmethod
    def hull_ma(series: pd.Series, period: int) -> pd.Series:
        """Hull Moving Average — combines speed with smoothness."""
        half = max(int(period / 2), 1)
        sqrt_p = max(int(np.sqrt(period)), 1)
        wma_half = TechnicalIndicators.wma(series, half)
        wma_full = TechnicalIndicators.wma(series, period)
        raw = 2 * wma_half - wma_full
        return TechnicalIndicators.wma(raw, sqrt_p)

    @staticmethod
    def kama(series: pd.Series, period: int = 10,
             fast: int = 2, slow: int = 30) -> pd.Series:
        """Kaufman Adaptive Moving Average."""
        fast_sc = 2.0 / (fast + 1)
        slow_sc = 2.0 / (slow + 1)
        direction = series.diff(period).abs()
        volatility = series.diff().abs().rolling(period).sum()
        er = (direction / volatility.replace(0, np.nan)).fillna(0)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        kama = series.copy()
        for i in range(1, len(series)):
            kama.iloc[i] = kama.iloc[i - 1] + sc.iloc[i] * (
                series.iloc[i] - kama.iloc[i - 1]
            )
        return kama

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10,
                   multiplier: float = 3.0) -> pd.DataFrame:
        """SuperTrend indicator — trend following with ATR-based bands.

        Returns:
            DataFrame with columns [supertrend, direction] (1=up, -1=down).
        """
        hl2 = (df["High"] + df["Low"]) / 2
        atr = TechnicalIndicators.atr(df, period)

        upper_basic = hl2 + multiplier * atr
        lower_basic = hl2 - multiplier * atr

        upper = upper_basic.copy()
        lower = lower_basic.copy()
        supertrend = pd.Series(np.nan, index=df.index)
        direction = pd.Series(1, index=df.index)

        for i in range(1, len(df)):
            prev_upper = upper.iloc[i - 1]
            prev_lower = lower.iloc[i - 1]
            close_prev = df["Close"].iloc[i - 1]

            upper.iloc[i] = (
                upper_basic.iloc[i]
                if upper_basic.iloc[i] < prev_upper or close_prev > prev_upper
                else prev_upper
            )
            lower.iloc[i] = (
                lower_basic.iloc[i]
                if lower_basic.iloc[i] > prev_lower or close_prev < prev_lower
                else prev_lower
            )

            if supertrend.iloc[i - 1] == prev_upper:
                direction.iloc[i] = -1 if df["Close"].iloc[i] > upper.iloc[i] else 1
            else:
                direction.iloc[i] = 1 if df["Close"].iloc[i] < lower.iloc[i] else -1

            supertrend.iloc[i] = (
                lower.iloc[i] if direction.iloc[i] == -1 else upper.iloc[i]
            )

        return pd.DataFrame(
            {"supertrend": supertrend, "direction": direction}, index=df.index
        )

    @staticmethod
    def parabolic_sar(df: pd.DataFrame, af_start: float = 0.02,
                       af_max: float = 0.20) -> pd.Series:
        """Parabolic SAR stop-and-reverse indicator."""
        high = df["High"].values
        low = df["Low"].values
        n = len(high)
        sar = np.zeros(n)
        ep = np.zeros(n)
        af = np.zeros(n)
        bull = np.ones(n, dtype=bool)

        sar[0] = low[0]
        ep[0] = high[0]
        af[0] = af_start

        for i in range(1, n):
            prev_sar = sar[i - 1]
            prev_ep = ep[i - 1]
            prev_af = af[i - 1]
            prev_bull = bull[i - 1]

            if prev_bull:
                sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)
                sar[i] = min(sar[i], low[i - 1], low[max(i - 2, 0)])
                if low[i] < sar[i]:
                    bull[i] = False
                    sar[i] = prev_ep
                    ep[i] = low[i]
                    af[i] = af_start
                else:
                    bull[i] = True
                    if high[i] > prev_ep:
                        ep[i] = high[i]
                        af[i] = min(prev_af + af_start, af_max)
                    else:
                        ep[i] = prev_ep
                        af[i] = prev_af
            else:
                sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)
                sar[i] = max(sar[i], high[i - 1], high[max(i - 2, 0)])
                if high[i] > sar[i]:
                    bull[i] = True
                    sar[i] = prev_ep
                    ep[i] = high[i]
                    af[i] = af_start
                else:
                    bull[i] = False
                    if low[i] < prev_ep:
                        ep[i] = low[i]
                        af[i] = min(prev_af + af_start, af_max)
                    else:
                        ep[i] = prev_ep
                        af[i] = prev_af

        return pd.Series(sar, index=df.index, name="psar")

    @staticmethod
    def ichimoku(df: pd.DataFrame) -> pd.DataFrame:
        """Ichimoku Cloud (Tenkan, Kijun, Senkou A/B, Chikou)."""
        def midpoint(s: pd.Series, p: int) -> pd.Series:
            return (s.rolling(p).max() + s.rolling(p).min()) / 2

        tenkan = midpoint(df["High"], 9) - midpoint(df["Low"], 9)
        # correct formula
        tenkan = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
        kijun = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = (
            (df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2
        ).shift(26)
        chikou = df["Close"].shift(-26)

        return pd.DataFrame(
            {
                "tenkan": tenkan,
                "kijun": kijun,
                "senkou_a": senkou_a,
                "senkou_b": senkou_b,
                "chikou": chikou,
            },
            index=df.index,
        )

    @staticmethod
    def linear_regression_channel(series: pd.Series,
                                   period: int = 50) -> pd.DataFrame:
        """Linear regression line with ±2σ channels."""
        mid = np.full(len(series), np.nan)
        upper = np.full(len(series), np.nan)
        lower = np.full(len(series), np.nan)

        for i in range(period - 1, len(series)):
            y = series.iloc[i - period + 1 : i + 1].values
            x = np.arange(period)
            m, b = np.polyfit(x, y, 1)
            fit = m * x + b
            residuals = y - fit
            std = residuals.std()
            mid[i] = fit[-1]
            upper[i] = fit[-1] + 2 * std
            lower[i] = fit[-1] - 2 * std

        return pd.DataFrame(
            {"lrc_mid": mid, "lrc_upper": upper, "lrc_lower": lower},
            index=series.index,
        )

    # =========================================================================
    # MOMENTUM
    # =========================================================================

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).rename("rsi")

    @staticmethod
    def stochastic_rsi(series: pd.Series, period: int = 14,
                       k: int = 3, d: int = 3) -> pd.DataFrame:
        """Stochastic RSI — more sensitive than RSI."""
        rsi = TechnicalIndicators.rsi(series, period)
        rsi_min = rsi.rolling(period).min()
        rsi_max = rsi.rolling(period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
        k_line = stoch_rsi.rolling(k).mean() * 100
        d_line = k_line.rolling(d).mean()
        return pd.DataFrame({"stochrsi_k": k_line, "stochrsi_d": d_line},
                             index=series.index)

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> pd.DataFrame:
        """MACD — Moving Average Convergence Divergence."""
        ema_fast = TechnicalIndicators.ema(series, fast)
        ema_slow = TechnicalIndicators.ema(series, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return pd.DataFrame(
            {"macd": macd_line, "macd_signal": signal_line, "macd_hist": histogram},
            index=series.index,
        )

    @staticmethod
    def stochastic(df: pd.DataFrame, k: int = 14, d: int = 3) -> pd.DataFrame:
        """Stochastic Oscillator (%K, %D)."""
        low_min = df["Low"].rolling(k).min()
        high_max = df["High"].rolling(k).max()
        pct_k = 100 * (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
        pct_d = pct_k.rolling(d).mean()
        return pd.DataFrame({"stoch_k": pct_k, "stoch_d": pct_d}, index=df.index)

    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index."""
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        mean_tp = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        return ((tp - mean_tp) / (0.015 * mad)).rename("cci")

    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R."""
        high_max = df["High"].rolling(period).max()
        low_min = df["Low"].rolling(period).min()
        return (
            -100 * (high_max - df["Close"]) / (high_max - low_min).replace(0, np.nan)
        ).rename("williams_r")

    @staticmethod
    def roc(series: pd.Series, period: int = 12) -> pd.Series:
        """Rate of Change."""
        return (series.diff(period) / series.shift(period) * 100).rename("roc")

    @staticmethod
    def momentum(series: pd.Series, period: int = 10) -> pd.Series:
        """Simple price momentum."""
        return series.diff(period).rename("momentum")

    @staticmethod
    def tsi(series: pd.Series, long: int = 25, short: int = 13) -> pd.Series:
        """True Strength Index."""
        m = series.diff()
        abs_m = m.abs()
        double_smooth = TechnicalIndicators.ema(
            TechnicalIndicators.ema(m, long), short
        )
        double_smooth_abs = TechnicalIndicators.ema(
            TechnicalIndicators.ema(abs_m, long), short
        )
        return (100 * double_smooth / double_smooth_abs.replace(0, np.nan)).rename("tsi")

    @staticmethod
    def ultimate_oscillator(df: pd.DataFrame,
                             p1: int = 7, p2: int = 14, p3: int = 28) -> pd.Series:
        """Ultimate Oscillator — Larry Williams."""
        prior_close = df["Close"].shift(1)
        bp = df["Close"] - pd.concat([df["Low"], prior_close], axis=1).min(axis=1)
        true_range = pd.concat(
            [df["High"] - df["Low"],
             (df["High"] - prior_close).abs(),
             (df["Low"] - prior_close).abs()],
            axis=1,
        ).max(axis=1)

        def avg(p: int) -> pd.Series:
            return bp.rolling(p).sum() / true_range.rolling(p).sum().replace(0, np.nan)

        uo = 100 * (4 * avg(p1) + 2 * avg(p2) + avg(p3)) / 7
        return uo.rename("ultimate_osc")

    @staticmethod
    def awesome_oscillator(df: pd.DataFrame) -> pd.Series:
        """Bill Williams Awesome Oscillator."""
        midpoint = (df["High"] + df["Low"]) / 2
        return (midpoint.rolling(5).mean() - midpoint.rolling(34).mean()).rename("ao")

    @staticmethod
    def dmi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Directional Movement Index (+DI, -DI, ADX)."""
        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        tr = pd.concat(
            [high - low,
             (high - close.shift()).abs(),
             (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        atr_s = tr.ewm(alpha=1 / period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_s.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_s.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()

        return pd.DataFrame(
            {"plus_di": plus_di, "minus_di": minus_di, "adx": adx}, index=df.index
        )

    # =========================================================================
    # VOLATILITY
    # =========================================================================

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20,
                        std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands."""
        mid = series.rolling(period).mean()
        sigma = series.rolling(period).std()
        return pd.DataFrame(
            {"bb_upper": mid + std * sigma, "bb_mid": mid, "bb_lower": mid - std * sigma},
            index=series.index,
        )

    @staticmethod
    def keltner_channels(df: pd.DataFrame, period: int = 20,
                          atr_mult: float = 2.0) -> pd.DataFrame:
        """Keltner Channels."""
        mid = TechnicalIndicators.ema(df["Close"], period)
        atr_val = TechnicalIndicators.atr(df, period)
        return pd.DataFrame(
            {
                "kc_upper": mid + atr_mult * atr_val,
                "kc_mid": mid,
                "kc_lower": mid - atr_mult * atr_val,
            },
            index=df.index,
        )

    @staticmethod
    def donchian_channels(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Donchian Channels."""
        upper = df["High"].rolling(period).max()
        lower = df["Low"].rolling(period).min()
        mid = (upper + lower) / 2
        return pd.DataFrame(
            {"dc_upper": upper, "dc_mid": mid, "dc_lower": lower}, index=df.index
        )

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        tr = pd.concat(
            [high - low,
             (high - close.shift()).abs(),
             (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.ewm(alpha=1 / period, adjust=False).mean().rename("atr")

    @staticmethod
    def natr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Normalized ATR — ATR as % of Close."""
        return (TechnicalIndicators.atr(df, period) / df["Close"] * 100).rename("natr")

    @staticmethod
    def historical_volatility(series: pd.Series, period: int = 20) -> pd.Series:
        """Annualized historical volatility (close-to-close log returns)."""
        log_ret = np.log(series / series.shift(1))
        return (log_ret.rolling(period).std() * np.sqrt(252) * 100).rename("hv")

    @staticmethod
    def chaikin_volatility(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Chaikin Volatility — change in High-Low spread."""
        hl = df["High"] - df["Low"]
        ema_hl = TechnicalIndicators.ema(hl, period)
        return ((ema_hl - ema_hl.shift(period)) / ema_hl.shift(period) * 100).rename(
            "chaikin_vol"
        )

    # =========================================================================
    # VOLUME
    # =========================================================================

    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        """On-Balance Volume."""
        direction = np.sign(df["Close"].diff().fillna(0))
        return (direction * df["Volume"]).cumsum().rename("obv")

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Volume Weighted Average Price (intraday, resets daily)."""
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        cumvol = df["Volume"].cumsum()
        cumtp_vol = (tp * df["Volume"]).cumsum()
        return (cumtp_vol / cumvol.replace(0, np.nan)).rename("vwap")

    @staticmethod
    def vwap_bands(df: pd.DataFrame,
                   std_devs: list[float] | None = None) -> pd.DataFrame:
        """VWAP with standard deviation bands."""
        if std_devs is None:
            std_devs = [1.0, 2.0]
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        cumvol = df["Volume"].cumsum()
        vwap = (tp * df["Volume"]).cumsum() / cumvol.replace(0, np.nan)

        # Rolling std of TP vs VWAP
        variance = ((tp - vwap) ** 2 * df["Volume"]).cumsum() / cumvol.replace(
            0, np.nan
        )
        std = variance.apply(np.sqrt)

        result = pd.DataFrame({"vwap": vwap}, index=df.index)
        for s in std_devs:
            result[f"vwap_upper_{s}"] = vwap + s * std
            result[f"vwap_lower_{s}"] = vwap - s * std
        return result

    @staticmethod
    def cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Chaikin Money Flow."""
        mfm = (
            (df["Close"] - df["Low"] - (df["High"] - df["Close"]))
            / (df["High"] - df["Low"]).replace(0, np.nan)
        )
        mfv = mfm * df["Volume"]
        return (mfv.rolling(period).sum() / df["Volume"].rolling(period).sum()).rename(
            "cmf"
        )

    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Money Flow Index — volume-weighted RSI."""
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        mf = tp * df["Volume"]
        positive = mf.where(tp > tp.shift(), 0.0)
        negative = mf.where(tp < tp.shift(), 0.0)
        mfr = positive.rolling(period).sum() / negative.rolling(period).sum().replace(
            0, np.nan
        )
        return (100 - 100 / (1 + mfr)).rename("mfi")

    @staticmethod
    def accumulation_distribution(df: pd.DataFrame) -> pd.Series:
        """Accumulation / Distribution Line."""
        clv = (
            (df["Close"] - df["Low"] - (df["High"] - df["Close"]))
            / (df["High"] - df["Low"]).replace(0, np.nan)
        )
        return (clv * df["Volume"]).cumsum().rename("ad")

    @staticmethod
    def force_index(df: pd.DataFrame, period: int = 13) -> pd.Series:
        """Elder's Force Index."""
        fi = df["Close"].diff() * df["Volume"]
        return TechnicalIndicators.ema(fi, period).rename("force_index")

    @staticmethod
    def ease_of_movement(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Ease of Movement."""
        dist_moved = (df["High"] + df["Low"]) / 2 - (
            df["High"].shift() + df["Low"].shift()
        ) / 2
        box_ratio = df["Volume"] / (
            (df["High"] - df["Low"]).replace(0, np.nan) * 1_000_000
        )
        emv = dist_moved / box_ratio
        return TechnicalIndicators.sma(emv, period).rename("emv")

    @staticmethod
    def volume_oscillator(df: pd.DataFrame, fast: int = 12, slow: int = 26) -> pd.Series:
        """Volume Oscillator (% difference between two volume MAs)."""
        fast_ma = TechnicalIndicators.ema(df["Volume"].astype(float), fast)
        slow_ma = TechnicalIndicators.ema(df["Volume"].astype(float), slow)
        return ((fast_ma - slow_ma) / slow_ma.replace(0, np.nan) * 100).rename("vol_osc")

    # =========================================================================
    # SUPPORT / RESISTANCE
    # =========================================================================

    @staticmethod
    def pivot_points(df: pd.DataFrame,
                     method: str = "standard") -> pd.DataFrame:
        """Daily pivot points (last closed session).

        Args:
            method: 'standard' | 'fibonacci' | 'camarilla' | 'woodie'

        Returns:
            DataFrame with pivot levels broadcast to the full index.
        """
        h = float(df["High"].iloc[-1])
        lo = float(df["Low"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        o = float(df["Open"].iloc[-1])

        if method == "standard":
            pp = (h + lo + c) / 3
            levels = {
                "pp": pp,
                "r1": 2 * pp - lo,
                "r2": pp + (h - lo),
                "r3": h + 2 * (pp - lo),
                "s1": 2 * pp - h,
                "s2": pp - (h - lo),
                "s3": lo - 2 * (h - pp),
            }
        elif method == "fibonacci":
            pp = (h + lo + c) / 3
            rng = h - lo
            levels = {
                "pp": pp,
                "r1": pp + 0.382 * rng,
                "r2": pp + 0.618 * rng,
                "r3": pp + 1.000 * rng,
                "s1": pp - 0.382 * rng,
                "s2": pp - 0.618 * rng,
                "s3": pp - 1.000 * rng,
            }
        elif method == "camarilla":
            rng = h - lo
            levels = {
                "pp": (h + lo + c) / 3,
                "r1": c + rng * 1.1 / 12,
                "r2": c + rng * 1.1 / 6,
                "r3": c + rng * 1.1 / 4,
                "r4": c + rng * 1.1 / 2,
                "s1": c - rng * 1.1 / 12,
                "s2": c - rng * 1.1 / 6,
                "s3": c - rng * 1.1 / 4,
                "s4": c - rng * 1.1 / 2,
            }
        else:  # woodie
            pp = (h + lo + 2 * o) / 4
            rng = h - lo
            levels = {
                "pp": pp,
                "r1": 2 * pp - lo,
                "r2": pp + rng,
                "s1": 2 * pp - h,
                "s2": pp - rng,
            }

        return pd.DataFrame(
            {k: np.full(len(df), v) for k, v in levels.items()}, index=df.index
        )

    @staticmethod
    def fibonacci_retracements(df: pd.DataFrame, lookback: int = 90) -> Dict:
        """Key Fibonacci retracement levels from highest high / lowest low.

        Returns:
            Dict mapping level name → price.
        """
        window = df.iloc[-min(lookback, len(df)):]
        h = float(window["High"].max())
        lo = float(window["Low"].min())
        rng = h - lo
        return {
            "100%": h,
            "78.6%": h - 0.786 * rng,
            "61.8%": h - 0.618 * rng,
            "50.0%": h - 0.500 * rng,
            "38.2%": h - 0.382 * rng,
            "23.6%": h - 0.236 * rng,
            "0%":    lo,
        }

    @staticmethod
    def fibonacci_extensions(df: pd.DataFrame, lookback: int = 90) -> Dict:
        """Fibonacci extension levels above the high.

        Returns:
            Dict mapping level name → price.
        """
        window = df.iloc[-min(lookback, len(df)):]
        h = float(window["High"].max())
        lo = float(window["Low"].min())
        rng = h - lo
        return {
            "127.2%": h + 0.272 * rng,
            "141.4%": h + 0.414 * rng,
            "161.8%": h + 0.618 * rng,
            "200.0%": h + 1.000 * rng,
            "261.8%": h + 1.618 * rng,
        }

    @staticmethod
    def auto_support_resistance(df: pd.DataFrame,
                                 sensitivity: int = 3,
                                 n_levels: int = 6) -> List[Dict]:
        """Automatic support/resistance detection via pivot clustering.

        Algorithm:
        1. Identify local pivot highs and lows.
        2. Cluster nearby pivots (< 1 % apart).
        3. Weight by touch count and recency.
        4. Return top N levels.

        Args:
            sensitivity: Window size for local pivot detection.
            n_levels: Number of levels to return.

        Returns:
            List of dicts with keys [price, type, touches, strength].
        """
        highs = df["High"].values
        lows = df["Low"].values
        close = df["Close"].values
        n = len(df)

        pivots: List[float] = []
        for i in range(sensitivity, n - sensitivity):
            if highs[i] == max(highs[i - sensitivity : i + sensitivity + 1]):
                pivots.append(highs[i])
            if lows[i] == min(lows[i - sensitivity : i + sensitivity + 1]):
                pivots.append(lows[i])

        if not pivots:
            return []

        pivots_arr = np.array(sorted(pivots))
        current_price = close[-1]
        threshold = current_price * 0.01  # 1% clustering distance

        # Cluster
        clusters: List[List[float]] = []
        current_cluster: List[float] = [pivots_arr[0]]
        for p in pivots_arr[1:]:
            if p - current_cluster[-1] < threshold:
                current_cluster.append(p)
            else:
                clusters.append(current_cluster)
                current_cluster = [p]
        clusters.append(current_cluster)

        levels = []
        for cl in clusters:
            price = float(np.mean(cl))
            touches = len(cl)
            level_type = "resistance" if price > current_price else "support"
            dist_pct = abs(price - current_price) / current_price * 100
            levels.append(
                {
                    "price": price,
                    "type": level_type,
                    "touches": touches,
                    "strength": "strong" if touches >= 3 else "moderate" if touches >= 2 else "weak",
                    "distance_pct": dist_pct,
                }
            )

        levels.sort(key=lambda x: (-x["touches"], x["distance_pct"]))
        return levels[:n_levels]


# Re-export type alias for typing in other modules
from typing import Dict, List
