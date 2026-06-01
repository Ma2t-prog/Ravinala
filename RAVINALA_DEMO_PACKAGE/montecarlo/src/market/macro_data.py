"""Macro Data Module - Comprehensive market snapshot
Global indices, commodities, FX, rates, economic indicators
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone
import warnings

warnings.filterwarnings('ignore')


# ─────────────────────────────────────────────────────────────────────────────
# INDICES
# ─────────────────────────────────────────────────────────────────────────────

MAJOR_INDICES = {
    # US
    "^GPSC": "S&P 500",
    "^INDU": "Dow Jones",
    "^NDX": "Nasdaq 100",
    "^VIX": "VIX",
    "^GSPC": "S&P 500",
    
    # Europe
    "^STOXX50E": "Euro Stoxx 50",
    "^FTSE": "FTSE 100",
    "^GDAXI": "DAX 40",
    "^FCHI": "CAC 40",
    "^IBEX": "IBEX 35",
    "^BFX": "BEL 20",
    
    # Asia-Pacific
    "^N225": "Nikkei 225",
    "000001.SS": "Shanghai",
    "^HSI": "Hang Seng",
    "^AORD": "ASX 200",
    "^STI": "Straits Times",
    "^KS11": "KOSPI",
    "^TWII": "Taiwan Weighted",
    "^JKSE": "Jakarta Composite",
    "BK.BK": "SET Thailand",
    "^AXJO": "All Ordinaries",
    
    # Emerging
    "^BVSP": "Bovespa (Brazil)",
    "^MERV": "Merval (Argentina)",
    "^IMOEX": "IMOEX (Russia)",
    "^CASE30": "EGX 30 (Egypt)",
    "^NSEBANK": "NIFTY Bank (India)",
    "^NSEI": "NIFTY 50 (India)",
}

# ─────────────────────────────────────────────────────────────────────────────
# COMMODITIES
# ─────────────────────────────────────────────────────────────────────────────

MAJOR_COMMODITIES = {
    "CL=F": "WTI Crude Oil",
    "BZ=F": "Brent Crude",
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CU=F": "Copper",
    "NG=F": "Natural Gas",
    "ZW=F": "Wheat",
    "ZC=F": "Corn",
    "ZS=F": "Soybeans",
    "KC=F": "Coffee",
    "CC=F": "Cocoa",
    "CT=F": "Cotton",
    "LL=F": "Lumber",
    "PL=F": "Platinum",
    "PA=F": "Palladium",
}

# ─────────────────────────────────────────────────────────────────────────────
# FX MAJORS & CROSSES
# ─────────────────────────────────────────────────────────────────────────────

MAJOR_FX = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF",
    "NZDUSD=X": "NZD/USD",
    "AUDUSD=X": "AUD/USD",
    "USDCAD=X": "USD/CAD",
    "CADJPY=X": "CAD/JPY",
    "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY",
    "AUDNZD=X": "AUD/NZD",
    "EURGBP=X": "EUR/GBP",
    "EURCHF=X": "EUR/CHF",
    "EURCAD=X": "EUR/CAD",
    "EURAUD=X": "EUR/AUD",
    "SGDUSD=X": "SGD/USD",
    "HKDUSD=X": "HKD/USD",
    "CNHUSD=X": "CNH/USD",
    "INRUSD=X": "INR/USD",
    "THBUSD=X": "THB/USD",
}

# ─────────────────────────────────────────────────────────────────────────────
# INTEREST RATES
# ─────────────────────────────────────────────────────────────────────────────

MAJOR_RATES = {
    # US Treasuries
    "^IRX": "US 13W T-Bill",
    "^TNX": "US 10Y Yield",
    "^TYX": "US 30Y Yield",
    "^FVX": "US 5Y Yield",
    
    # Euro OAT/BUND
    "TEUR10Y=X": "EUR 10Y OAT",
    "TDEUY=X": "Germany 10Y Bund",
    
    # UK Gilts
    "^TGBP10Y": "UK 10Y Gilt",
    
    # Japan JGB
    "^JGBY10": "Japan 10Y JGB",
    
    # Switzerland
    "^ZSW10": "Swiss 10Y",
    
    # Canada
    "^CADUSD": "Canada 10Y",
}


def _flatten_df(df):
    """Flatten yfinance 1.x multi-level columns to single level."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_price_changes(ticker: str, periods_days: List[int] = [1, 5, 20, 65, 252, 756, 1260]) -> Dict[str, float]:
    """
    Calculate % change for different periods:
    1 day = vs yesterday
    5 days = WTD
    20 days = MTD
    65 days = QTD
    252 days = YTD
    756 days = 3Y
    1260 days = 5Y
    """
    try:
        data = _flatten_df(yf.download(ticker, period='5y', progress=False))
        if data.empty:
            return {}

        current_price = float(data['Close'].iloc[-1])
        changes = {}
        
        period_names = {
            1: "vs Yesterday",
            5: "WTD",
            20: "MTD",
            65: "QTD",
            252: "YTD",
            756: "3Y",
            1260: "5Y"
        }
        
        for days in periods_days:
            if len(data) > days:
                past_price = data['Close'].iloc[-(days+1)]
                change_pct = ((current_price - past_price) / past_price) * 100
                changes[period_names.get(days, f"{days}D")] = round(change_pct, 2)
            else:
                changes[period_names.get(days, f"{days}D")] = None
        
        return changes
    except Exception:
        return {}


def fetch_indices_snapshot() -> pd.DataFrame:
    """Fetch all major indices with current prices and changes"""
    data = []
    
    for ticker, name in list(MAJOR_INDICES.items())[:20]:  # Top 20
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period='1y')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                yesterday = hist['Close'].iloc[-2] if len(hist) > 1 else current
                ytd_start = hist['Close'].iloc[0]
                
                change_1d = ((current - yesterday) / yesterday) * 100
                change_ytd = ((current - ytd_start) / ytd_start) * 100
                
                data.append({
                    'Index': name,
                    'Ticker': ticker,
                    'Price': round(current, 2),
                    'vs Yesterday %': round(change_1d, 2),
                    'YTD %': round(change_ytd, 2),
                })
        except Exception:
            continue
    
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_commodities_snapshot() -> pd.DataFrame:
    """Fetch major commodities"""
    data = []
    
    for ticker, name in MAJOR_COMMODITIES.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period='1y')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                yesterday = hist['Close'].iloc[-2] if len(hist) > 1 else current
                ytd_start = hist['Close'].iloc[0]
                
                change_1d = ((current - yesterday) / yesterday) * 100
                change_ytd = ((current - ytd_start) / ytd_start) * 100
                
                data.append({
                    'Commodity': name,
                    'Ticker': ticker,
                    'Price': round(current, 3),
                    'vs Yesterday %': round(change_1d, 2),
                    'YTD %': round(change_ytd, 2),
                })
        except Exception:
            continue
    
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_fx_snapshot() -> pd.DataFrame:
    """Fetch major FX pairs"""
    data = []
    
    for ticker, name in MAJOR_FX.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period='1y')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                yesterday = hist['Close'].iloc[-2] if len(hist) > 1 else current
                ytd_start = hist['Close'].iloc[0]
                
                change_1d = ((current - yesterday) / yesterday) * 100
                change_ytd = ((current - ytd_start) / ytd_start) * 100
                
                data.append({
                    'Pair': name,
                    'Ticker': ticker,
                    'Rate': round(current, 5),
                    'vs Yesterday %': round(change_1d, 2),
                    'YTD %': round(change_ytd, 2),
                })
        except Exception:
            continue
    
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_rates_snapshot() -> pd.DataFrame:
    """Fetch major interest rates"""
    data = []
    
    for ticker, name in MAJOR_RATES.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period='1y')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                yesterday = hist['Close'].iloc[-2] if len(hist) > 1 else current
                
                change_1d = current - yesterday
                
                data.append({
                    'Instrument': name,
                    'Ticker': ticker,
                    'Yield %': round(current, 3),
                    'vs Yesterday (bps)': round(change_1d * 100, 2),
                })
        except Exception:
            continue
    
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_macro_data() -> Dict:
    """Fetch global macro data"""
    macro = {
        "Global Population": "~8.1 billion",
        "Global GDP": "~$105 trillion USD (2024)",
        "Global Trade": "~$32 trillion USD (2024)",
        "Major Central Banks": {
            "Federal Reserve": "2.50% (as of 2026)",
            "ECB": "2.50%",
            "BOJ": "0.50%",
            "BOE": "4.75%",
            "SNB": "1.00%",
        }
    }
    return macro


def fetch_cpi_data() -> Dict:
    """Fetch latest CPI data for major countries"""
    # This would typically come from FRED, World Bank, or OECD
    # For now, returning simulated data
    return {
        "US CPI YoY": "2.8%",
        "Eurozone CPI YoY": "2.1%",
        "UK CPI YoY": "3.9%",
        "Japan CPI YoY": "1.8%",
        "China CPI YoY": "0.8%",
        "India CPI YoY": "5.2%",
    }


def fetch_gdp_data() -> Dict:
    """Fetch latest GDP growth data"""
    return {
        "US GDP Growth": "2.5% (2024)",
        "Eurozone GDP Growth": "0.8% (2024)",
        "UK GDP Growth": "0.5% (2024)",
        "Japan GDP Growth": "1.2% (2024)",
        "China GDP Growth": "5.0% (2024)",
        "India GDP Growth": "6.7% (2024)",
    }

import base64
import concurrent.futures
import smtplib
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import threading
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# SPARKLINE HELPER
# ─────────────────────────────────────────────────────────────────

def _spark(prices: list, w: int = 80, h: int = 22) -> str:
    """Return inline <img> tag with SVG sparkline as base64 data URI."""
    clean = [p for p in prices if p is not None and not (isinstance(p, float) and (p != p))]
    if len(clean) < 2:
        return ""
    mn, mx = min(clean), max(clean)
    if mx <= mn:
        mx = mn + 1e-9
    color = "#00C853" if clean[-1] >= clean[0] else "#FF1744"
    n = len(clean)
    pts = " ".join(f"{i/(n-1)*w:.1f},{h-(p-mn)/(mx-mn)*h:.2f}" for i, p in enumerate(clean))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
           f'<polyline points="{pts}" fill="none" stroke="{color}" '
           f'stroke-width="1.5" stroke-linejoin="round"/></svg>')
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{w}" height="{h}" style="vertical-align:middle">'


def _pct_span(val: Optional[float], decimals: int = 2, suffix: str = "%") -> str:
    """Return colored HTML span for a numeric change value."""
    if val is None:
        return '<span style="color:#555">N/A</span>'
    css = "color:#00C853" if val >= 0 else "color:#FF1744"
    sign = "+" if val >= 0 else ""
    return f'<span style="{css}">{sign}{val:.{decimals}f}{suffix}</span>'


def _fmt(val, decimals: int = 2, thousands: bool = True) -> str:
    if val is None:
        return "N/A"
    try:
        if thousands and abs(val) >= 1000:
            return f"{val:,.{decimals}f}"
        return f"{val:.{decimals}f}"
    except Exception:
        return str(val)


# ─────────────────────────────────────────────────────────────────
# MacroDataProvider
# ─────────────────────────────────────────────────────────────────

class MacroDataProvider:
    """
    Provides global macro market data via yfinance.
    All fetch methods return DataFrames/dicts. No Streamlit dependency.
    """

    EQUITY_INDICES = {
        '^GSPC':      ('S&P 500',          'US', 'Americas'),
        '^DJI':       ('Dow Jones',         'US', 'Americas'),
        '^IXIC':      ('NASDAQ Comp.',      'US', 'Americas'),
        '^NDX':       ('NASDAQ 100',        'US', 'Americas'),
        '^RUT':       ('Russell 2000',      'US', 'Americas'),
        '^BVSP':      ('Bovespa',           'BR', 'Americas'),
        '^GSPTSE':    ('S&P/TSX',           'CA', 'Americas'),
        '^MXX':       ('IPC Mexico',        'MX', 'Americas'),
        '^FCHI':      ('CAC 40',            'FR', 'Europe'),
        '^GDAXI':     ('DAX 40',            'DE', 'Europe'),
        '^FTSE':      ('FTSE 100',          'GB', 'Europe'),
        '^STOXX50E':  ('Euro Stoxx 50',     'EU', 'Europe'),
        '^IBEX':      ('IBEX 35',           'ES', 'Europe'),
        'FTSEMIB.MI': ('FTSE MIB',          'IT', 'Europe'),
        '^AEX':       ('AEX',               'NL', 'Europe'),
        '^SSMI':      ('SMI',               'CH', 'Europe'),
        '^N225':      ('Nikkei 225',        'JP', 'Asia-Pac'),
        '^HSI':       ('Hang Seng',         'HK', 'Asia-Pac'),
        '000001.SS':  ('Shanghai Comp.',    'CN', 'Asia-Pac'),
        '^KS11':      ('KOSPI',             'KR', 'Asia-Pac'),
        '^AXJO':      ('ASX 200',           'AU', 'Asia-Pac'),
        '^BSESN':     ('SENSEX',            'IN', 'Asia-Pac'),
    }

    BOND_TICKERS = {
        '^TNX': ('US 10Y T-Note',  'US', 10),
        '^FVX': ('US 5Y',          'US',  5),
        '^TYX': ('US 30Y Bond',    'US', 30),
        '^IRX': ('US 13W T-Bill',  'US', 0.25),
    }

    FX_G10 = {
        'EURUSD=X': ('EUR/USD', 'EU'),
        'GBPUSD=X': ('GBP/USD', 'GB'),
        'USDJPY=X': ('USD/JPY', 'JP'),
        'USDCHF=X': ('USD/CHF', 'CH'),
        'AUDUSD=X': ('AUD/USD', 'AU'),
        'USDCAD=X': ('USD/CAD', 'CA'),
        'NZDUSD=X': ('NZD/USD', 'NZ'),
        'EURGBP=X': ('EUR/GBP', 'EU'),
        'EURJPY=X': ('EUR/JPY', 'EU'),
        'GBPJPY=X': ('GBP/JPY', 'GB'),
    }

    FX_EM = {
        'USDCNY=X': ('USD/CNY', 'CN'),
        'USDINR=X': ('USD/INR', 'IN'),
        'USDBRL=X': ('USD/BRL', 'BR'),
        'USDMXN=X': ('USD/MXN', 'MX'),
        'USDTRY=X': ('USD/TRY', 'TR'),
        'USDZAR=X': ('USD/ZAR', 'ZA'),
        'USDKRW=X': ('USD/KRW', 'KR'),
        'USDSEK=X': ('USD/SEK', 'SE'),
        'USDNOK=X': ('USD/NOK', 'NO'),
    }

    COMMODITIES = {
        'CL=F':  ('WTI Crude',    '', 'Energy'),
        'BZ=F':  ('Brent Crude',  '', 'Energy'),
        'NG=F':  ('Natural Gas',  '', 'Energy'),
        'GC=F':  ('Gold',         '', 'Metals'),
        'SI=F':  ('Silver',       '', 'Metals'),
        'PL=F':  ('Platinum',     '', 'Metals'),
        'HG=F':  ('Copper',       '', 'Metals'),
        'ZW=F':  ('Wheat',        '', 'Agri'),
        'ZC=F':  ('Corn',         '', 'Agri'),
        'ZS=F':  ('Soybeans',     '', 'Agri'),
        'KC=F':  ('Coffee',       '', 'Agri'),
        'CC=F':  ('Cocoa',        '', 'Agri'),
    }

    VOL_RATES = {
        '^VIX': ('VIX (S&P Vol)',   'Vol'),
        '^VXN': ('VXN (NDX Vol)',   'Vol'),
        '^TNX': ('US 10Y Yield',    'Rates'),
        '^TYX': ('US 30Y Yield',    'Rates'),
        '^FVX': ('US 5Y Yield',     'Rates'),
        '^IRX': ('US 13W T-Bill',   'Rates'),
    }

    CRYPTO = {
        'BTC-USD': ('Bitcoin',  'BTC'),
        'ETH-USD': ('Ethereum', 'ETH'),
        'SOL-USD': ('Solana',   'SOL'),
        'XRP-USD': ('XRP',      'XRP'),
        'BNB-USD': ('BNB',      'BNB'),
    }

    def _batch_download(self, tickers: list, period: str = '35d') -> pd.DataFrame:
        """Download close prices for a list of tickers. Returns DataFrame[ticker->closes]."""
        if not tickers:
            return pd.DataFrame()
        try:
            raw = yf.download(
                tickers, period=period, interval='1d',
                auto_adjust=True, progress=False, threads=True,
            )
            if raw.empty:
                return pd.DataFrame()
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw['Close']
            else:
                closes = raw[['Close']].rename(columns={'Close': tickers[0]})
            if closes.index.tz is not None:
                closes.index = closes.index.tz_localize(None)
            return closes
        except Exception:
            return pd.DataFrame()

    def _row_from_closes(self, col: pd.Series, name: str, flag: str,
                          region_or_cat: str, decimals: int = 2,
                          is_yield: bool = False) -> Optional[dict]:
        """Build a data row from a price series."""
        s = col.dropna()
        if len(s) < 2:
            return None
        last = float(s.iloc[-1])
        prev = float(s.iloc[-2])
        chg_pct = (last - prev) / abs(prev) * 100 if prev != 0 else 0.0
        chg_net = last - prev
        hi52 = float(s.tail(252).max()) if len(s) >= 252 else float(s.max())
        lo52 = float(s.tail(252).min()) if len(s) >= 252 else float(s.min())
        ytd_start = float(s.iloc[0])
        ytd_pct = (last - ytd_start) / abs(ytd_start) * 100 if ytd_start != 0 else 0.0
        sparkline = s.tail(30).tolist()
        return {
            'name': name, 'flag': flag, 'group': region_or_cat,
            'last': round(last, decimals),
            'change_pct': round(chg_pct, 2),
            'change_net': round(chg_net, decimals),
            'hi52': round(hi52, decimals), 'lo52': round(lo52, decimals),
            'ytd_pct': round(ytd_pct, 2),
            'sparkline': sparkline,
            'chg_bps': round(chg_net * 100, 1) if is_yield else None,
        }

    def fetch_equity_indices(self) -> pd.DataFrame:
        tickers = list(self.EQUITY_INDICES.keys())
        closes = self._batch_download(tickers, period='1y')
        rows = []
        for tkr, (name, flag, region) in self.EQUITY_INDICES.items():
            if tkr not in closes.columns:
                continue
            row = self._row_from_closes(closes[tkr], name, flag, region, decimals=2)
            if row:
                rows.append(row)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_bond_yields(self) -> pd.DataFrame:
        tickers = list(self.BOND_TICKERS.keys())
        closes = self._batch_download(tickers, period='1y')
        us10y = None
        rows = []
        for tkr, (name, flag, maturity) in self.BOND_TICKERS.items():
            if tkr not in closes.columns:
                continue
            s = closes[tkr].dropna()
            if len(s) < 2:
                continue
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2])
            chg_bps = round((last - prev) * 100, 1)
            if tkr == '^TNX':
                us10y = last
            rows.append({
                'name': name, 'flag': flag, 'maturity': maturity,
                'yield_pct': round(last, 3),
                'chg_bps': chg_bps,
                'sparkline': s.tail(30).tolist(),
            })
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if not df.empty and us10y is not None:
            df['spread_vs_us'] = df['yield_pct'].apply(
                lambda y: round((y - us10y) * 100, 1)
            )
        return df

    def fetch_fx(self) -> pd.DataFrame:
        all_fx = {**self.FX_G10, **self.FX_EM}
        closes = self._batch_download(list(all_fx.keys()), period='35d')
        rows = []
        for tkr, (name, flag) in all_fx.items():
            group = 'G10' if tkr in self.FX_G10 else 'EM'
            if tkr not in closes.columns:
                continue
            dec = 4 if 'JPY' not in name and 'KRW' not in name else 2
            row = self._row_from_closes(closes[tkr], name, flag, group, decimals=dec)
            if row:
                rows.append(row)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_commodities(self) -> pd.DataFrame:
        closes = self._batch_download(list(self.COMMODITIES.keys()), period='35d')
        rows = []
        for tkr, (name, icon, cat) in self.COMMODITIES.items():
            if tkr not in closes.columns:
                continue
            row = self._row_from_closes(closes[tkr], name, icon, cat, decimals=2)
            if row:
                rows.append(row)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_vol_and_rates(self) -> dict:
        closes = self._batch_download(list(self.VOL_RATES.keys()), period='35d')
        result = {}
        for tkr, (name, cat) in self.VOL_RATES.items():
            if tkr not in closes.columns:
                continue
            s = closes[tkr].dropna()
            if len(s) < 2:
                continue
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2])
            chg_pct = (last - prev) / abs(prev) * 100 if prev != 0 else 0.0
            chg_bps = (last - prev) * 100

            # VIX level context
            context = ""
            if tkr == '^VIX':
                if last < 15:   context = "Low Vol — Complacency"
                elif last < 20: context = "Normal"
                elif last < 30: context = "Elevated — Risk-Off"
                else:            context = "High Vol — Stress WARNING"

            result[tkr] = {
                'name': name, 'cat': cat,
                'last': round(last, 3),
                'chg_pct': round(chg_pct, 2),
                'chg_bps': round(chg_bps, 1),
                'context': context,
                'sparkline': s.tail(30).tolist(),
            }

        # Yield curve slope (10Y - 2Y approximated by 10Y - 13W)
        try:
            v10 = result.get('^TNX', {}).get('last', 0)
            v13w = result.get('^IRX', {}).get('last', 0)
            result['curve_slope'] = round(v10 - v13w, 3)
            result['curve_inverted'] = result['curve_slope'] < 0
        except Exception:
            result['curve_slope'] = None
            result['curve_inverted'] = False

        return result

    def fetch_crypto(self) -> pd.DataFrame:
        closes = self._batch_download(list(self.CRYPTO.keys()), period='35d')
        rows = []
        for tkr, (name, icon) in self.CRYPTO.items():
            if tkr not in closes.columns:
                continue
            s = closes[tkr].dropna()
            if len(s) < 2:
                continue
            last  = float(s.iloc[-1])
            prev  = float(s.iloc[-2])
            w7ago = float(s.iloc[-8]) if len(s) >= 8 else float(s.iloc[0])
            chg1d = (last - prev) / abs(prev) * 100 if prev != 0 else 0.0
            chg7d = (last - w7ago) / abs(w7ago) * 100 if w7ago != 0 else 0.0
            rows.append({
                'name': name, 'icon': icon,
                'last': round(last, 2),
                'chg_1d': round(chg1d, 2),
                'chg_7d': round(chg7d, 2),
                'sparkline': s.tail(30).tolist(),
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def fetch_economic_calendar(self) -> pd.DataFrame:
        """Static calendar for next 7 days based on known schedules (2026-03)."""
        today = datetime.now(timezone.utc).date()
        events = [
            # (date_offset_days, time_utc, country, flag, event, importance, prev, forecast)
            (0,  '13:30', 'US', 'US', 'Initial Jobless Claims',        'High',   '221K', '225K'),
            (0,  '15:30', 'US', 'US', 'EIA Natural Gas Storage',        'Medium', '-80B', '-75B'),
            (1,  '09:00', 'EU', 'EU', 'ECB President Lagarde Speech',   'High',   '',     ''),
            (2,  '13:30', 'US', 'US', 'US Retail Sales MoM',            'High',   '0.4%', '0.6%'),
            (2,  '13:30', 'US', 'US', 'US PPI MoM',                     'Medium', '0.2%', '0.3%'),
            (2,  '15:15', 'US', 'US', 'US Industrial Production',        'Medium', '0.5%', '0.4%'),
            (3,  '14:00', 'US', 'US', 'Michigan Consumer Sentiment',     'Medium', '67.8', '68.5'),
            (4,  '09:30', 'UK', 'GB', 'UK CPI YoY',                     'High',   '3.0%', '2.9%'),
            (4,  '10:00', 'DE', 'DE', 'Germany ZEW Economic Sentiment',  'Medium', '26.0', '28.5'),
            (5,  '02:00', 'CN', 'CN', 'China M2 Money Supply YoY',       'Medium', '7.0%', '7.2%'),
            (5,  '02:00', 'CN', 'CN', 'China New Loans',                 'High',   '1.5T', '1.3T'),
            (5,  '18:00', 'US', 'US', 'FOMC Meeting Begins',             'High',   '',     ''),
            (6,  '18:00', 'US', 'US', 'Fed Rate Decision',              'High',   '4.25%','4.25%'),
            (6,  '18:30', 'US', 'US', 'Fed Press Conference — Powell',   'High',   '',     ''),
            (7,  '09:00', 'EU', 'EU', 'Eurozone CPI Final YoY',          'High',   '2.5%', '2.4%'),
        ]
        rows = []
        for off, t, country, flag, event, imp, prev, fcst in events:
            dt = today + timedelta(days=off)
            rows.append({
                'date': dt.strftime('%b %d'),
                'time': t,
                'flag': flag,
                'country': country,
                'event': event,
                'importance': imp,
                'previous': prev,
                'forecast': fcst,
                'actual': '',
            })
        return pd.DataFrame(rows)

    def fetch_news(self, n: int = 15) -> pd.DataFrame:
        """Fetch financial news headlines via yfinance."""
        rows = []
        sources = ['^GSPC', '^VIX', 'GC=F', 'CL=F', 'EURUSD=X']
        seen = set()
        for src in sources:
            try:
                news_list = yf.Ticker(src).news or []
                for item in news_list:
                    title = item.get('title', '')
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    ts = item.get('providerPublishTime', 0)
                    pub_dt = datetime.fromtimestamp(ts, timezone.utc) if ts else datetime.now(timezone.utc)
                    ago_secs = (datetime.now(timezone.utc) - pub_dt).total_seconds()
                    if ago_secs < 3600:
                        ago = f"{int(ago_secs//60)}m ago"
                    elif ago_secs < 86400:
                        ago = f"{int(ago_secs//3600)}h ago"
                    else:
                        ago = f"{int(ago_secs//86400)}d ago"
                    rows.append({
                        'ago': ago,
                        'source': item.get('publisher', 'Reuters'),
                        'headline': title,
                        'url': item.get('link', '#'),
                        'ts': pub_dt,
                    })
            except Exception:
                continue
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if not df.empty:
            df = df.sort_values('ts', ascending=False).drop_duplicates('headline').head(n)
        return df

    def fetch_all(self) -> dict:
        """Fetch all categories in parallel using ThreadPoolExecutor."""
        results = {'errors': [], 'timestamp': datetime.now(timezone.utc)}
        fns = {
            'indices':    self.fetch_equity_indices,
            'bonds':      self.fetch_bond_yields,
            'fx':         self.fetch_fx,
            'commodities':self.fetch_commodities,
            'vol_rates':  self.fetch_vol_and_rates,
            'crypto':     self.fetch_crypto,
            'calendar':   self.fetch_economic_calendar,
            'news':       self.fetch_news,
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(fn): name for name, fn in fns.items()}
            for fut in concurrent.futures.as_completed(futs, timeout=35):
                name = futs[fut]
                try:
                    results[name] = fut.result(timeout=30)
                except Exception as e:
                    results[name] = pd.DataFrame() if name != 'vol_rates' else {}
                    results['errors'].append(f"{name}: {e}")
        return results


# ─────────────────────────────────────────────────────────────────
# CACHED FETCH WRAPPER
# ─────────────────────────────────────────────────────────────────

def _get_macro_provider():
    return MacroDataProvider()


# ─────────────────────────────────────────────────────────────────
# HTML TABLE BUILDERS
# ─────────────────────────────────────────────────────────────────

_CSS = """
<style>
.mkt { width:100%; border-collapse:collapse; font-size:11.5px;
       font-family:'JetBrains Mono',monospace; }
.mkt th { background:#1B2838; color:#8B949E; padding:3px 6px;
          border-bottom:1px solid #30363D; font-weight:600;
          text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; }
.mkt th:first-child,.mkt td:first-child { text-align:left; padding-left:8px; }
.mkt th,.mkt td { text-align:right; }
.mkt td { padding:2px 6px; border-bottom:1px solid rgba(48,54,61,.35);
          color:#E6EDF3; white-space:nowrap; }
.mkt tr:hover td { background:rgba(48,54,61,.5); }
.pos { color:#00C853; } .neg { color:#FF1744; } .neu { color:#8B949E; }
.grp { background:#0E1623; color:#5B7FA6; font-size:10px;
       padding:2px 8px; letter-spacing:.08em; text-transform:uppercase; }
.imp-H { color:#FF1744; font-weight:700; }
.imp-M { color:#FF9100; }
.imp-L { color:#00C853; }
.mkt-panel { background:#111827; border:1px solid #1F2937;
             border-radius:6px; padding:10px; margin-bottom:8px; }
.panel-title { color:#8B949E; font-size:10px; font-weight:700;
               text-transform:uppercase; letter-spacing:.1em;
               margin-bottom:6px; padding-bottom:4px;
               border-bottom:1px solid #1F2937; }
</style>
"""


def _chg_cell(val: Optional[float], suffix: str = "%", dec: int = 2) -> str:
    if val is None: return '<td class="neu">N/A</td>'
    css = "pos" if val >= 0 else "neg"
    sign = "+" if val >= 0 else ""
    return f'<td class="{css}">{sign}{val:.{dec}f}{suffix}</td>'


def _build_indices_html(df: pd.DataFrame) -> str:
    if df.empty: return "<p>No data</p>"
    rows_html = ""
    current_grp = None
    for _, r in df.iterrows():
        if r.get('group') != current_grp:
            current_grp = r.get('group', '')
            rows_html += f'<tr><td class="grp" colspan="6">{current_grp}</td></tr>'
        spark = _spark(r.get('sparkline', []))
        chg_pct = r.get('change_pct')
        chg_net = r.get('change_net')
        css = "pos" if (chg_pct or 0) >= 0 else "neg"
        rows_html += (
            f'<tr>'
            f'<td>{r.get("flag","")} {r.get("name","")}</td>'
            f'<td style="font-weight:600">{_fmt(r.get("last"), 2)}</td>'
            f'{_chg_cell(chg_pct)}'
            f'<td class="{css}">{_fmt(chg_net, 2, False)}</td>'
            f'<td>{spark}</td>'
            f'</tr>'
        )
    return (f'<table class="mkt"><thead><tr>'
            f'<th>Index</th><th>Last</th><th>Chg%</th>'
            f'<th>Net</th><th>30D</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>')


def _build_fx_html(df: pd.DataFrame, group: str) -> str:
    sub = df[df['group'] == group] if not df.empty and 'group' in df.columns else df
    if sub.empty: return "<p>No data</p>"
    rows_html = ""
    for _, r in sub.iterrows():
        spark = _spark(r.get('sparkline', []))
        rows_html += (
            f'<tr>'
            f'<td>{r.get("flag","")} {r.get("name","")}</td>'
            f'<td style="font-weight:600">{_fmt(r.get("last"), 4)}</td>'
            f'{_chg_cell(r.get("change_pct"))}'
            f'<td>{spark}</td>'
            f'</tr>'
        )
    return (f'<table class="mkt"><thead><tr>'
            f'<th>Pair</th><th>Last</th><th>Chg%</th><th>30D</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>')


def _build_commodities_html(df: pd.DataFrame) -> str:
    if df.empty: return "<p>No data</p>"
    rows_html = ""
    current_cat = None
    for _, r in df.iterrows():
        cat = r.get('group', '')
        if cat != current_cat:
            current_cat = cat
            rows_html += f'<tr><td class="grp" colspan="5">{cat}</td></tr>'
        spark = _spark(r.get('sparkline', []))
        rows_html += (
            f'<tr>'
            f'<td>{r.get("flag","")} {r.get("name","")}</td>'
            f'<td style="font-weight:600">{_fmt(r.get("last"), 2)}</td>'
            f'{_chg_cell(r.get("change_pct"))}'
            f'<td>{spark}</td>'
            f'</tr>'
        )
    return (f'<table class="mkt"><thead><tr>'
            f'<th>Commodity</th><th>Last</th><th>Chg%</th><th>30D</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>')


def _build_calendar_html(df: pd.DataFrame) -> str:
    if df.empty: return "<p>No events</p>"
    rows_html = ""
    for _, r in df.iterrows():
        imp = r.get('importance', 'Low')
        icss = {'High': 'imp-H', 'Medium': 'imp-M', 'Low': 'imp-L'}.get(imp, 'neu')
        rows_html += (
            f'<tr>'
            f'<td>{r.get("flag","")} {r.get("date","")} {r.get("time","")}</td>'
            f'<td style="max-width:200px;overflow:hidden">{r.get("event","")}</td>'
            f'<td class="{icss}">{imp[0]}</td>'
            f'<td class="neu">{r.get("previous","")}</td>'
            f'<td class="neu">{r.get("forecast","")}</td>'
            f'<td style="color:#00C853">{r.get("actual","")}</td>'
            f'</tr>'
        )
    return (f'<table class="mkt"><thead><tr>'
            f'<th>When</th><th>Event</th><th>!</th>'
            f'<th>Prev</th><th>Est</th><th>Act</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>')


def _build_news_html(df: pd.DataFrame) -> str:
    if df.empty: return "<p>No news available</p>"
    items = ""
    for _, r in df.iterrows():
        url = r.get('url', '#')
        headline = r.get('headline', '')
        source = r.get('source', '')
        ago = r.get('ago', '')
        items += (
            f'<div style="padding:4px 0; border-bottom:1px solid #1F2937;">'
            f'<span style="color:#5B7FA6;font-size:10px">{ago} · {source}</span><br>'
            f'<a href="{url}" target="_blank" style="color:#E6EDF3;font-size:11.5px;'
            f'text-decoration:none;font-family:Inter,sans-serif">{headline}</a>'
            f'</div>'
        )
    return f'<div style="font-size:11.5px">{items}</div>'


def _build_crypto_html(df: pd.DataFrame) -> str:
    if df.empty: return "<p>No data</p>"
    rows_html = ""
    for _, r in df.iterrows():
        spark = _spark(r.get('sparkline', []))
        rows_html += (
            f'<tr>'
            f'<td>{r.get("icon","")} {r.get("name","")}</td>'
            f'<td style="font-weight:600">${_fmt(r.get("last"), 2)}</td>'
            f'{_chg_cell(r.get("chg_1d"))}'
            f'{_chg_cell(r.get("chg_7d"))}'
            f'<td>{spark}</td>'
            f'</tr>'
        )
    return (f'<table class="mkt"><thead><tr>'
            f'<th>Asset</th><th>Price</th><th>24h</th><th>7d</th><th>Chart</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>')


def _build_vol_html(vr: dict) -> str:
    if not vr: return "<p>No data</p>"
    vix = vr.get('^VIX', {})
    vix_val = vix.get('last', 0)
    vix_ctx = vix.get('context', '')
    vix_chg = vix.get('chg_pct', 0)

    # VIX gauge bar
    gauge_pct = min(vix_val / 50 * 100, 100)
    gauge_color = ('#00C853' if vix_val < 15 else
                   '#FFD700' if vix_val < 20 else
                   '#FF9100' if vix_val < 30 else '#FF1744')

    html = (
        f'<div style="margin-bottom:10px">'
        f'<div style="color:#8B949E;font-size:10px;margin-bottom:2px">VIX — Fear Index</div>'
        f'<div style="font-size:22px;font-weight:700;color:{gauge_color}">'
        f'{vix_val:.2f} '
        f'<span style="font-size:12px">{_pct_span(vix_chg)}</span></div>'
        f'<div style="background:#1B2838;border-radius:4px;height:6px;margin:4px 0">'
        f'<div style="background:{gauge_color};width:{gauge_pct:.0f}%;height:6px;border-radius:4px"></div></div>'
        f'<div style="color:{gauge_color};font-size:10px">{vix_ctx}</div>'
        f'</div>'
    )

    # Yield curve
    slope = vr.get('curve_slope')
    inverted = vr.get('curve_inverted', False)
    if slope is not None:
        slope_color = "#FF1744" if inverted else "#00C853"
        inv_txt = "WARNING INVERTED" if inverted else ""
        html += (
            f'<div style="margin-bottom:8px">'
            f'<div style="color:#8B949E;font-size:10px">Yield Curve (10Y–13W)</div>'
            f'<div style="color:{slope_color};font-size:14px;font-weight:600">'
            f'{slope:+.3f}%{inv_txt}</div></div>'
        )

    # Rates table
    rate_rows = ""
    for tkr in ['^IRX', '^FVX', '^TNX', '^TYX']:
        d = vr.get(tkr, {})
        if not d: continue
        bps = d.get('chg_bps', 0)
        bps_css = "pos" if bps >= 0 else "neg"
        sign = "+" if bps >= 0 else ""
        rate_rows += (
            f'<tr>'
            f'<td style="color:#E6EDF3">{d.get("name","")}</td>'
            f'<td style="font-weight:600;color:#E6EDF3">{d.get("last",0):.3f}%</td>'
            f'<td class="{bps_css}">{sign}{bps:.1f}bps</td>'
            f'</tr>'
        )
    if rate_rows:
        html += (f'<table class="mkt"><thead><tr>'
                 f'<th>Instrument</th><th>Yield</th><th>Δbps</th>'
                 f'</tr></thead><tbody>{rate_rows}</tbody></table>')
    return html


# ─────────────────────────────────────────────────────────────────
# MAIN UI RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────

def render_macro_tab():
    """Render the Global Macro Terminal tab."""
    import streamlit as st
    from macro_export import MacroExcelExporter, MacroEmailSender

    st.markdown(_CSS, unsafe_allow_html=True)

    # ── HEADER ──────────────────────────────────────────────────
    h_left, h_mid, h_right = st.columns([3, 2, 2])
    with h_left:
        ts = st.session_state.get('_macro_ts', '')
        st.markdown(f"## Global Macro Terminal")
        if ts:
            st.caption(f"Last updated: {ts} UTC")

    with h_mid:
        if st.button("Update Snapshot", type="primary", key="_macro_refresh"):
            with st.spinner("Fetching global market data…"):
                provider = MacroDataProvider()
                data = provider.fetch_all()
                st.session_state['_macro_data'] = data
                st.session_state['_macro_ts'] = data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                if data.get('errors'):
                    st.warning(f"Partial data — {len(data['errors'])} source(s) unavailable.")
                st.rerun()

    with h_right:
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            if st.button("Export Excel", key="_macro_xl"):
                data = st.session_state.get('_macro_data')
                if data:
                    with st.spinner("Generating Excel…"):
                        try:
                            exporter = MacroExcelExporter()
                            xl_bytes = exporter.export_bytes(data)
                            fname = f"ravinala_macro_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.xlsx"
                            st.download_button("Download", xl_bytes, fname,
                                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="_macro_xl_dl")
                        except Exception as e:
                            st.error(f"Export error: {e}")
                else:
                    st.info("Load data first.")

        with ecol2:
            with st.popover("Email"):
                email_to = st.text_input("Recipient", placeholder="pm@fund.com", key="_macro_email_to")
                attach = st.checkbox("Attach Excel", True, key="_macro_attach")
                with st.expander("SMTP"):
                    smtp_srv = st.text_input("Server", "smtp.gmail.com", key="_macro_smtp")
                    smtp_port = st.number_input("Port", value=587, key="_macro_port")
                    smtp_user = st.text_input("Email", key="_macro_su")
                    smtp_pass = st.text_input("Password", type="password", key="_macro_sp")
                if st.button("Send", type="primary", key="_macro_send_btn"):
                    data = st.session_state.get('_macro_data')
                    if not data:
                        st.error("Load data first.")
                    elif not email_to:
                        st.error("Enter recipient email.")
                    else:
                        with st.spinner("Sending…"):
                            try:
                                sender = MacroEmailSender(
                                    smtp_server=smtp_srv, smtp_port=int(smtp_port),
                                    smtp_user=smtp_user, smtp_password=smtp_pass,
                                )
                                ok = sender.send_snapshot(email_to, data, attach_excel=attach)
                                if ok:
                                    st.success("Sent!")
                                else:
                                    st.error("Failed — check SMTP settings.")
                            except Exception as e:
                                st.error(f"Error: {e}")

    # Auto-load on first visit
    if '_macro_data' not in st.session_state:
        st.info("Click **Update Snapshot** to load live market data.")
        return

    data = st.session_state['_macro_data']

    st.markdown("---")

    # ── ROW 1: Indices | Bonds | Calendar ───────────────────────
    col_idx, col_bond, col_cal = st.columns([1.4, 0.9, 1.2])

    with col_idx:
        st.markdown('<div class="panel-title">Equity Indices</div>', unsafe_allow_html=True)
        idx_df = data.get('indices', pd.DataFrame())
        if not idx_df.empty:
            # Sort by region for grouping
            region_order = {'Americas': 0, 'Europe': 1, 'Asia-Pac': 2}
            idx_df['_ro'] = idx_df['group'].map(region_order).fillna(3)
            idx_df = idx_df.sort_values(['_ro', 'name']).drop(columns='_ro')
        st.markdown(_build_indices_html(idx_df), unsafe_allow_html=True)

    with col_bond:
        st.markdown('<div class="panel-title">Govt Yields</div>', unsafe_allow_html=True)
        bond_df = data.get('bonds', pd.DataFrame())
        if not bond_df.empty:
            rows_h = ""
            for _, r in bond_df.iterrows():
                spark = _spark(r.get('sparkline', []))
                bps = r.get('chg_bps', 0)
                css = "pos" if bps >= 0 else "neg"
                sign = "+" if bps >= 0 else ""
                rows_h += (f'<tr>'
                            f'<td>{r.get("flag","")} {r.get("name","")}</td>'
                            f'<td style="font-weight:600">{r.get("yield_pct",0):.3f}%</td>'
                            f'<td class="{css}">{sign}{bps:.1f}bps</td>'
                            f'<td>{spark}</td></tr>')
            st.markdown(
                f'<table class="mkt"><thead><tr><th>Bond</th><th>Yield</th><th>Δ</th><th>30D</th></tr></thead>'
                f'<tbody>{rows_h}</tbody></table>', unsafe_allow_html=True
            )
        else:
            st.caption("N/A")

    with col_cal:
        st.markdown('<div class="panel-title">Economic Calendar (7 days)</div>', unsafe_allow_html=True)
        cal_df = data.get('calendar', pd.DataFrame())
        st.markdown(_build_calendar_html(cal_df), unsafe_allow_html=True)

    st.markdown("---")

    # ── ROW 2: FX | Commodities | News ──────────────────────────
    col_fx, col_comm, col_news = st.columns([1.0, 1.0, 1.2])

    with col_fx:
        fx_df = data.get('fx', pd.DataFrame())
        st.markdown('<div class="panel-title">FX — G10</div>', unsafe_allow_html=True)
        st.markdown(_build_fx_html(fx_df, 'G10'), unsafe_allow_html=True)
        st.markdown('<div class="panel-title" style="margin-top:10px">FX — Emerging</div>', unsafe_allow_html=True)
        st.markdown(_build_fx_html(fx_df, 'EM'), unsafe_allow_html=True)

    with col_comm:
        st.markdown('<div class="panel-title">Commodities</div>', unsafe_allow_html=True)
        comm_df = data.get('commodities', pd.DataFrame())
        if not comm_df.empty:
            cat_order = {'Energy': 0, 'Metals': 1, 'Agri': 2}
            comm_df['_co'] = comm_df['group'].map(cat_order).fillna(3)
            comm_df = comm_df.sort_values(['_co', 'name']).drop(columns='_co')
        st.markdown(_build_commodities_html(comm_df), unsafe_allow_html=True)

    with col_news:
        st.markdown('<div class="panel-title">Market News</div>', unsafe_allow_html=True)
        news_df = data.get('news', pd.DataFrame())
        st.markdown(_build_news_html(news_df), unsafe_allow_html=True)

    st.markdown("---")

    # ── ROW 3: Vol & Rates | Crypto ─────────────────────────────
    col_vol, col_crypto = st.columns([1.0, 1.0])

    with col_vol:
        st.markdown('<div class="panel-title">Volatility & Rates</div>', unsafe_allow_html=True)
        vr = data.get('vol_rates', {})
        st.markdown(_build_vol_html(vr), unsafe_allow_html=True)

        # Mini yield curve chart
        if vr:
            maturities, yields_vals = [], []
            for tkr, mat_label in [('^IRX', 0.25), ('^FVX', 5), ('^TNX', 10), ('^TYX', 30)]:
                d = vr.get(tkr, {})
                if d.get('last'):
                    maturities.append(mat_label)
                    yields_vals.append(d['last'])
            if len(maturities) >= 2:
                import plotly.graph_objects as go
                fig_yc = go.Figure(go.Scatter(
                    x=maturities, y=yields_vals,
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=2),
                    marker=dict(color='#00D9A6', size=6),
                ))
                fig_yc.update_layout(
                    paper_bgcolor='#0A0A0F', plot_bgcolor='#0A0A0F',
                    font=dict(color='rgba(255,255,255,.72)', size=10),
                    margin=dict(l=0, r=0, t=20, b=0), height=160,
                    xaxis=dict(title='Maturity (Y)', gridcolor='rgba(255,255,255,.04)',
                               tickvals=maturities,
                               ticktext=['13W', '5Y', '10Y', '30Y']),
                    yaxis=dict(title='Yield %', gridcolor='rgba(255,255,255,.04)'),
                    title=dict(text='US Yield Curve', font=dict(size=11)),
                    template='plotly_dark',
                )
                st.plotly_chart(fig_yc, width="stretch")

    with col_crypto:
        st.markdown('<div class="panel-title">BTC Crypto</div>', unsafe_allow_html=True)
        crypto_df = data.get('crypto', pd.DataFrame())
        st.markdown(_build_crypto_html(crypto_df), unsafe_allow_html=True)

        # VXN panel
        vxn = vr.get('^VXN', {}) if vr else {}
        if vxn:
            st.markdown(
                f'<div style="margin-top:10px"><div class="panel-title">VXN (Nasdaq Vol)</div>'
                f'<div style="font-size:20px;font-weight:700;color:#FF9100">{vxn.get("last",0):.2f}'
                f'<span style="font-size:11px;margin-left:6px">{_pct_span(vxn.get("chg_pct"))}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
