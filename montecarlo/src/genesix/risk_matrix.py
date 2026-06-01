"""
Institutional Risk Matrix — 20-Level Scale
==========================================
Professional risk classification used by asset managers, family offices,
hedge funds and institutional desks.

Each level defines:
  - Annualized volatility budget
  - VaR limits (95% and 99%, 1-day)
  - Maximum drawdown tolerance
  - Beta cap (net exposure to S&P 500)
  - Leverage ceiling
  - Asset class allocation constraints (min/max weights)
  - Allowed instrument universe
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List


@dataclass
class RiskLevel:
    level: int
    label: str                    # Short institutional label
    category: str                 # Broad bucket
    target_return_pa: float       # % p.a.
    vol_budget_pa: float          # Annualized sigma %
    max_drawdown_pct: float       # Max tolerated drawdown %
    var_95_1d: float              # 1-day 95% VaR as % of NAV
    var_99_1d: float              # 1-day 99% VaR as % of NAV
    beta_cap: float               # Max net beta vs S&P 500
    max_leverage: float           # 1.0 = no leverage
    sharpe_target: float          # Minimum acceptable Sharpe
    typical_mandate: str
    constraints: Dict[str, Tuple[float, float]]   # {asset_class: (min%, max%)}
    universe: List[str]           # Allowed instruments
    color: str                    # UI color hex


# ============================================================================
#  THE 20-LEVEL INSTITUTIONAL RISK MATRIX
# ============================================================================

RISK_MATRIX: Dict[int, RiskLevel] = {

    # ── TIER I — CAPITAL PRESERVATION (1-3) ──────────────────────────────────
    1: RiskLevel(
        level=1, label="Capital Preservation I", category="Capital Preservation",
        target_return_pa=2.5, vol_budget_pa=1.0, max_drawdown_pct=1.5,
        var_95_1d=0.06, var_99_1d=0.09, beta_cap=0.05, max_leverage=1.0,
        sharpe_target=2.0,
        typical_mandate="Insurance float, central bank reserves, pension surplus buffer",
        constraints={
            "T-Bills / Money Market": (70.0, 100.0),
            "Short IG Bonds (< 1Y)":  (0.0,  30.0),
            "Equities":               (0.0,   0.0),
            "Alternatives":           (0.0,   0.0),
        },
        universe=["T-Bills", "SOFR swaps", "Money Market funds", "O/N repos",
                  "Short-duration sovereign (AAA-AA, < 1Y)"],
        color="#1a9850",
    ),

    2: RiskLevel(
        level=2, label="Capital Preservation II", category="Capital Preservation",
        target_return_pa=3.2, vol_budget_pa=2.0, max_drawdown_pct=3.0,
        var_95_1d=0.12, var_99_1d=0.18, beta_cap=0.10, max_leverage=1.0,
        sharpe_target=1.5,
        typical_mandate="Pension de-risking, LGIM LDI strategies, liability-matching",
        constraints={
            "T-Bills / Money Market":  (30.0, 70.0),
            "Short IG Bonds (1-3Y)":   (20.0, 60.0),
            "IG Credit (< 2Y)":        (0.0,  20.0),
            "Equities":                (0.0,   5.0),
        },
        universe=["US Treasuries (< 3Y)", "Agency MBS", "TIPS (< 3Y)",
                  "IG corporate bonds (< 2Y)", "CD", "SHV", "BIL", "SGOV"],
        color="#66bd63",
    ),

    3: RiskLevel(
        level=3, label="Capital Preservation III", category="Capital Preservation",
        target_return_pa=4.0, vol_budget_pa=3.5, max_drawdown_pct=5.0,
        var_95_1d=0.22, var_99_1d=0.32, beta_cap=0.15, max_leverage=1.0,
        sharpe_target=1.2,
        typical_mandate="Short-duration fixed income mandate, absolute return floor",
        constraints={
            "Short IG Bonds (1-5Y)":   (40.0, 80.0),
            "T-Bills / Money Market":  (10.0, 40.0),
            "IG Credit":               (0.0,  25.0),
            "Equities (dividend)":     (0.0,  10.0),
        },
        universe=["US Treasuries (1-5Y)", "SHY", "IEF", "AGG (short dur)",
                  "BND", "Dividend blue-chips (JNJ, PG, KO)", "TIPS"],
        color="#a6d96a",
    ),

    # ── TIER II — CONSERVATIVE (4-6) ─────────────────────────────────────────
    4: RiskLevel(
        level=4, label="Conservative I", category="Conservative",
        target_return_pa=4.8, vol_budget_pa=5.0, max_drawdown_pct=8.0,
        var_95_1d=0.31, var_99_1d=0.46, beta_cap=0.25, max_leverage=1.0,
        sharpe_target=1.0,
        typical_mandate="Conservative endowment, DC pension default fund",
        constraints={
            "IG Bonds":                (50.0, 75.0),
            "Equities (dividend)":     (10.0, 25.0),
            "Gold / Real Assets":      (5.0,  15.0),
            "Cash":                    (5.0,  15.0),
        },
        universe=["AGG", "BND", "TLT (hedged)", "GLD", "IAU", "VYM",
                  "JNJ", "PG", "KO", "VNQ", "VTIP"],
        color="#d9ef8b",
    ),

    5: RiskLevel(
        level=5, label="Conservative II", category="Conservative",
        target_return_pa=5.5, vol_budget_pa=6.5, max_drawdown_pct=10.0,
        var_95_1d=0.40, var_99_1d=0.60, beta_cap=0.35, max_leverage=1.0,
        sharpe_target=0.85,
        typical_mandate="Foundation, charitable endowment with spending rule",
        constraints={
            "IG Bonds":                (40.0, 65.0),
            "Equities (blend)":        (15.0, 30.0),
            "REITs":                   (0.0,  10.0),
            "Gold":                    (5.0,  15.0),
            "Cash":                    (5.0,  15.0),
        },
        universe=["AGG", "BND", "TLT", "GLD", "VYM", "VNQ", "SCHD",
                  "VOO (capped)", "SPY (capped)", "TIPS", "IEI"],
        color="#fee08b",
    ),

    6: RiskLevel(
        level=6, label="Conservative III", category="Conservative",
        target_return_pa=6.2, vol_budget_pa=8.0, max_drawdown_pct=13.0,
        var_95_1d=0.50, var_99_1d=0.74, beta_cap=0.45, max_leverage=1.0,
        sharpe_target=0.78,
        typical_mandate="Pension fund balanced mandate, conservative SWF allocation",
        constraints={
            "IG Bonds":                (35.0, 55.0),
            "Equities (global)":       (20.0, 35.0),
            "Real Assets (REITs/Gold)":(5.0,  15.0),
            "IG Credit":               (5.0,  15.0),
            "Cash":                    (5.0,  10.0),
        },
        universe=["AGG", "BND", "VEU", "VOO", "VYM", "GLD", "VNQ",
                  "LQD", "VCIT", "HYG (capped 10%)", "TIPS"],
        color="#fdae61",
    ),

    # ── TIER III — BALANCED (7-9) ─────────────────────────────────────────────
    7: RiskLevel(
        level=7, label="Balanced I", category="Balanced",
        target_return_pa=7.0, vol_budget_pa=9.5, max_drawdown_pct=16.0,
        var_95_1d=0.59, var_99_1d=0.88, beta_cap=0.55, max_leverage=1.0,
        sharpe_target=0.73,
        typical_mandate="60/40 institutional mandate, sovereign pension balanced",
        constraints={
            "Equities (global)":       (35.0, 55.0),
            "Bonds (IG)":              (30.0, 50.0),
            "Alternatives":            (0.0,  10.0),
            "Real Assets":             (5.0,  15.0),
            "Cash":                    (0.0,  10.0),
        },
        universe=["VOO", "VTI", "VEU", "BND", "AGG", "TLT", "GLD",
                  "VNQ", "DBC", "VXUS", "EFA"],
        color="#f46d43",
    ),

    8: RiskLevel(
        level=8, label="Balanced II", category="Balanced",
        target_return_pa=7.8, vol_budget_pa=11.0, max_drawdown_pct=19.0,
        var_95_1d=0.68, var_99_1d=1.02, beta_cap=0.65, max_leverage=1.0,
        sharpe_target=0.71,
        typical_mandate="Multi-asset fund, balanced mandate with alternatives sleeve",
        constraints={
            "Equities (global)":       (40.0, 60.0),
            "Bonds (IG/HY blend)":     (20.0, 40.0),
            "Alternatives":            (0.0,  15.0),
            "Real Assets":             (5.0,  15.0),
            "Cash":                    (0.0,  10.0),
        },
        universe=["VOO", "VTI", "QQQ (capped)", "VEU", "EEM (capped)",
                  "BND", "HYG", "TLT", "GLD", "VNQ", "DBC", "VXUS"],
        color="#d73027",
    ),

    9: RiskLevel(
        level=9, label="Balanced III", category="Balanced",
        target_return_pa=8.5, vol_budget_pa=12.5, max_drawdown_pct=22.0,
        var_95_1d=0.78, var_99_1d=1.16, beta_cap=0.75, max_leverage=1.1,
        sharpe_target=0.68,
        typical_mandate="Endowment model light (Yale/Swensen adapted), family office core",
        constraints={
            "Equities (global)":       (45.0, 65.0),
            "Bonds":                   (15.0, 30.0),
            "Alternatives (PE/HF)":    (5.0,  20.0),
            "Real Assets":             (5.0,  15.0),
            "Cash":                    (0.0,  5.0),
        },
        universe=["VOO", "VTI", "QQQ", "VEU", "EEM", "IWM", "BND",
                  "HYG", "GLD", "VNQ", "PDBC", "Liquid alts (AQR, etc.)"],
        color="#a50026",
    ),

    # ── TIER IV — GROWTH (10-12) ──────────────────────────────────────────────
    10: RiskLevel(
        level=10, label="Growth I", category="Growth",
        target_return_pa=9.5, vol_budget_pa=14.0, max_drawdown_pct=26.0,
        var_95_1d=0.87, var_99_1d=1.30, beta_cap=0.85, max_leverage=1.2,
        sharpe_target=0.68,
        typical_mandate="Institutional growth mandate, university endowment core equity",
        constraints={
            "Equities (global)":       (55.0, 75.0),
            "Bonds / Credit":          (10.0, 25.0),
            "Alternatives":            (5.0,  20.0),
            "Real Assets":             (0.0,  10.0),
        },
        universe=["VOO", "VTI", "QQQ", "VEU", "EEM", "IWM",
                  "Individual large-caps", "HYG", "EMB", "GLD",
                  "Private credit (illiquid bucket)"],
        color="#313695",
    ),

    11: RiskLevel(
        level=11, label="Growth II", category="Growth",
        target_return_pa=10.5, vol_budget_pa=16.0, max_drawdown_pct=30.0,
        var_95_1d=0.99, var_99_1d=1.49, beta_cap=0.95, max_leverage=1.3,
        sharpe_target=0.66,
        typical_mandate="Growth-oriented family office, aggressive endowment equity sleeve",
        constraints={
            "Equities (global)":       (60.0, 80.0),
            "Credit (HY/EM)":          (5.0,  20.0),
            "Alternatives":            (5.0,  20.0),
            "Real Assets":             (0.0,  10.0),
        },
        universe=["VOO", "QQQ", "VGT", "VEU", "EEM", "IWM", "NVDA",
                  "MSFT", "AAPL", "GOOGL", "AMZN", "HYG", "EMB"],
        color="#4575b4",
    ),

    12: RiskLevel(
        level=12, label="Growth III", category="Growth",
        target_return_pa=11.5, vol_budget_pa=18.0, max_drawdown_pct=34.0,
        var_95_1d=1.12, var_99_1d=1.68, beta_cap=1.05, max_leverage=1.4,
        sharpe_target=0.64,
        typical_mandate="Concentrated equity mandate, global growth overlay",
        constraints={
            "Equities (global)":       (65.0, 85.0),
            "HY Credit / EM debt":     (0.0,  15.0),
            "Alternatives":            (5.0,  20.0),
            "Commodities":             (0.0,  10.0),
        },
        universe=["QQQ", "VGT", "ARKK", "VWO", "EEM", "IWM", "SPMD",
                  "Individual growth names", "HYG", "BNDX", "DBC"],
        color="#74add1",
    ),

    # ── TIER V — AGGRESSIVE GROWTH (13-15) ────────────────────────────────────
    13: RiskLevel(
        level=13, label="Aggressive Growth I", category="Aggressive Growth",
        target_return_pa=13.0, vol_budget_pa=20.0, max_drawdown_pct=38.0,
        var_95_1d=1.24, var_99_1d=1.86, beta_cap=1.15, max_leverage=1.5,
        sharpe_target=0.65,
        typical_mandate="Aggressive family office, concentrated equity book",
        constraints={
            "Equities (domestic)":     (45.0, 65.0),
            "Equities (EM/Intl)":      (10.0, 25.0),
            "Alternatives":            (5.0,  20.0),
            "Crypto":                  (0.0,   5.0),
        },
        universe=["QQQ", "VGT", "IBB", "ARKK", "VWO", "EEM", "IWM",
                  "Individual names (NVDA, TSLA, META)", "GBTC (capped)"],
        color="#abd9e9",
    ),

    14: RiskLevel(
        level=14, label="Aggressive Growth II", category="Aggressive Growth",
        target_return_pa=14.5, vol_budget_pa=23.0, max_drawdown_pct=43.0,
        var_95_1d=1.43, var_99_1d=2.14, beta_cap=1.25, max_leverage=1.75,
        sharpe_target=0.63,
        typical_mandate="Long/short equity lite, HF L-only book",
        constraints={
            "Equities (concentrated)": (50.0, 75.0),
            "Equities (EM)":           (10.0, 25.0),
            "Alternatives / HF":       (5.0,  25.0),
            "Crypto":                  (0.0,  10.0),
        },
        universe=["Individual names (10-20 positions)", "QQQ", "TQQQ (tactical)",
                  "VWO", "XBI", "ARKK", "GBTC", "ETHE", "Leveraged ETFs (tactical)"],
        color="#e0f3f8",
    ),

    15: RiskLevel(
        level=15, label="Aggressive Growth III", category="Aggressive Growth",
        target_return_pa=16.0, vol_budget_pa=27.0, max_drawdown_pct=48.0,
        var_95_1d=1.68, var_99_1d=2.52, beta_cap=1.40, max_leverage=2.0,
        sharpe_target=0.59,
        typical_mandate="Opportunistic growth overlay, event-driven sleeve",
        constraints={
            "Equities (concentrated)": (50.0, 80.0),
            "EM / Frontier":           (5.0,  25.0),
            "Alternatives":            (5.0,  25.0),
            "Crypto":                  (0.0,  15.0),
        },
        universe=["Concentrated L-only (5-15 names)", "Leveraged equity ETFs",
                  "XBI", "ARKK", "BTC-USD", "ETH-USD", "VWO", "FM (frontier)"],
        color="#fee090",
    ),

    # ── TIER VI — HIGH RISK (16-17) ────────────────────────────────────────────
    16: RiskLevel(
        level=16, label="High Risk I", category="High Risk",
        target_return_pa=18.0, vol_budget_pa=32.0, max_drawdown_pct=55.0,
        var_95_1d=1.99, var_99_1d=2.98, beta_cap=1.60, max_leverage=2.5,
        sharpe_target=0.56,
        typical_mandate="Prop desk directional book, leveraged long-only mandate",
        constraints={
            "Equities (concentrated)": (40.0, 80.0),
            "Derivatives (long delta)": (0.0, 30.0),
            "Crypto":                  (0.0,  20.0),
            "Leverage / Margin":       (0.0,  50.0),
        },
        universe=["Individual names (5-10 pos)", "TQQQ", "SOXL", "UPRO",
                  "Long calls/puts", "BTC-USD", "ETH-USD", "SOL-USD", "Margin"],
        color="#fdae61",
    ),

    17: RiskLevel(
        level=17, label="High Risk II", category="High Risk",
        target_return_pa=21.0, vol_budget_pa=38.0, max_drawdown_pct=63.0,
        var_95_1d=2.36, var_99_1d=3.54, beta_cap=1.80, max_leverage=3.0,
        sharpe_target=0.55,
        typical_mandate="Aggressive prop, stat-arb with risk-on overlay, HF multi-strat",
        constraints={
            "Equities (concentrated)": (30.0, 70.0),
            "Derivatives":             (5.0,  40.0),
            "Crypto":                  (0.0,  30.0),
            "Leverage":                (0.0,  67.0),
        },
        universe=["Concentrated single names", "Options (long gamma)",
                  "3x Leveraged ETFs", "BTC/ETH/SOL/ALT", "Futures (CME, CBOT)"],
        color="#f46d43",
    ),

    # ── TIER VII — SPECULATIVE (18) ────────────────────────────────────────────
    18: RiskLevel(
        level=18, label="Speculative", category="Speculative",
        target_return_pa=25.0, vol_budget_pa=50.0, max_drawdown_pct=75.0,
        var_95_1d=3.11, var_99_1d=4.66, beta_cap=2.20, max_leverage=4.0,
        sharpe_target=0.50,
        typical_mandate="Special situations, distressed, pre-IPO, venture-adjacent",
        constraints={
            "Equities / Event-driven":  (20.0, 60.0),
            "Derivatives (structured)": (10.0, 50.0),
            "Crypto / Digital Assets":  (0.0,  40.0),
            "Leverage":                 (0.0, 75.0),
        },
        universe=["Distressed equities", "Convertible arb", "SPAC",
                  "Long-dated OTM options", "BTC/ETH/SOL", "DeFi tokens (bluechip)",
                  "Leveraged futures", "Pre-IPO private placements"],
        color="#d73027",
    ),

    # ── TIER VIII — MAXIMUM RISK (19-20) ──────────────────────────────────────
    19: RiskLevel(
        level=19, label="Maximum Risk I", category="Maximum Risk",
        target_return_pa=30.0, vol_budget_pa=65.0, max_drawdown_pct=85.0,
        var_95_1d=4.03, var_99_1d=6.05, beta_cap=3.0, max_leverage=5.0,
        sharpe_target=0.46,
        typical_mandate="Personal prop book of senior trader, crypto-native fund",
        constraints={
            "High-conviction concentrated": (20.0, 70.0),
            "Derivatives (complex)":         (0.0,  60.0),
            "Crypto / Web3":                 (0.0,  60.0),
        },
        universe=["Any single-name equity", "Deep OTM options (naked)",
                  "BTC/ETH/SOL/ALT (full position)",
                  "Perpetual futures (crypto)", "5x+ leveraged instruments"],
        color="#a50026",
    ),

    20: RiskLevel(
        level=20, label="Maximum Risk II — Unconstrained", category="Maximum Risk",
        target_return_pa=40.0, vol_budget_pa=90.0, max_drawdown_pct=100.0,
        var_95_1d=5.59, var_99_1d=8.38, beta_cap=float('inf'), max_leverage=10.0,
        sharpe_target=0.44,
        typical_mandate="Pure speculation — full risk capital only. No constraints.",
        constraints={
            "Unconstrained": (0.0, 100.0),
        },
        universe=["Anything — full discretion, no guardrails"],
        color="#67000d",
    ),
}


def get_level(level: int) -> RiskLevel:
    return RISK_MATRIX[max(1, min(20, level))]


def get_category_range(category: str) -> List[int]:
    return [lvl for lvl, r in RISK_MATRIX.items() if r.category == category]


CATEGORIES = [
    "Capital Preservation",  # 1-3
    "Conservative",          # 4-6
    "Balanced",              # 7-9
    "Growth",                # 10-12
    "Aggressive Growth",     # 13-15
    "High Risk",             # 16-17
    "Speculative",           # 18
    "Maximum Risk",          # 19-20
]

CATEGORY_COLORS = {
    "Capital Preservation": "#1a9850",
    "Conservative":         "#fee08b",
    "Balanced":             "#f46d43",
    "Growth":               "#4575b4",
    "Aggressive Growth":    "#abd9e9",
    "High Risk":            "#d73027",
    "Speculative":          "#a50026",
    "Maximum Risk":         "#67000d",
}
