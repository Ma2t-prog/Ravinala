"""Ravinala Fundamental Analysis Module
Enterprise valuations, DCF models, financial scoring, peer comparisons.
Core valuations: Discounted Cash Flow (DCF), Monte Carlo DCF, Multiples.
Financial Health: Altman Z-Score, Piotroski F-Score.
Benchmarking: P/E, EV/EBITDA, Price-to-Book, etc. vs. peers.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


# ─────────────────────────────────────────────────────────────────────────────
# 1. FINANCIAL DATA FETCHER
# ─────────────────────────────────────────────────────────────────────────────

class FinancialDataFetcher:
    """Fetch and cache financial data (income statement, balance sheet, cash flow)"""
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper().strip()
        self.yf_ticker = yf.Ticker(self.ticker)
        self._cache = {}
    
    def get_income_statement(self) -> Optional[pd.DataFrame]:
        """Fetch annual income statement"""
        if "income_stmt" in self._cache:
            return self._cache["income_stmt"]
        try:
            stmt = self.yf_ticker.income_stmt
            self._cache["income_stmt"] = stmt
            return stmt
        except Exception:
            return None
    
    def get_balance_sheet(self) -> Optional[pd.DataFrame]:
        """Fetch annual balance sheet"""
        if "balance_sheet" in self._cache:
            return self._cache["balance_sheet"]
        try:
            sheet = self.yf_ticker.balance_sheet
            self._cache["balance_sheet"] = sheet
            return sheet
        except Exception:
            return None
    
    def get_cash_flow(self) -> Optional[pd.DataFrame]:
        """Fetch annual cash flow statement"""
        if "cash_flow" in self._cache:
            return self._cache["cash_flow"]
        try:
            cf = self.yf_ticker.cashflow
            self._cache["cash_flow"] = cf
            return cf
        except Exception:
            return None
    
    def get_info(self) -> Dict:
        """Fetch company info dict"""
        if "info" in self._cache:
            return self._cache["info"]
        try:
            info = self.yf_ticker.info
            self._cache["info"] = info
            return info
        except Exception:
            return {}
    
    def get_quarterly_income(self) -> Optional[pd.DataFrame]:
        """Fetch quarterly income statement"""
        try:
            return self.yf_ticker.quarterly_income_stmt
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. DCF VALUATION
# ─────────────────────────────────────────────────────────────────────────────

class DCFValuation:
    """
    Unlevered DCF model:
    Enterprise Value = Sum(FCF discounted) + Terminal Value
    Price per Share = (EV - Net Debt) / Shares Outstanding
    """
    
    def __init__(self, ticker: str, fetcher: Optional[FinancialDataFetcher] = None):
        self.ticker = ticker
        self.fetcher = fetcher or FinancialDataFetcher(ticker)
        self.info = self.fetcher.get_info()
        self.cash_flow = self.fetcher.get_cash_flow()
        self.balance_sheet = self.fetcher.get_balance_sheet()
        self.income_stmt = self.fetcher.get_income_statement()
    
    def get_ttm_revenue(self) -> Optional[float]:
        """Get trailing twelve months revenue"""
        if self.income_stmt is None or self.income_stmt.empty:
            return None
        try:
            # income_stmt: rows = metrics, columns = dates
            if 'Total Revenue' in self.income_stmt.index:
                revenue = self.income_stmt.loc['Total Revenue'].iloc[0]
                return float(revenue) if revenue and not np.isnan(float(revenue)) else None
        except Exception:
            pass
        return None
    
    def get_fcf_history(self, periods: int = 5) -> List[float]:
        """Get historical free cash flow (Operating CF - CapEx)"""
        fcf_list = []
        if self.cash_flow is None or self.cash_flow.empty:
            return fcf_list
        
        # Operating cash flow - capital expenditure
        try:
            for i in range(min(periods, len(self.cash_flow.columns))):
                op_cf = self.cash_flow.loc['Operating Cash Flow'].iloc[i] if 'Operating Cash Flow' in self.cash_flow.index else 0
                capex = abs(self.cash_flow.loc['Capital Expenditure'].iloc[i]) if 'Capital Expenditure' in self.cash_flow.index else 0
                fcf = float(op_cf - capex) if (op_cf and capex is not None) else 0
                fcf_list.append(fcf)
        except Exception:
            pass
        
        return fcf_list[::-1]  # Reverse to chronological order
    
    def project_fcf(self, base_fcf: float, growth_rates: List[float], years: int = 5) -> List[float]:
        """Project FCF over n years with given growth rates"""
        projected = [base_fcf]
        for i in range(1, years):
            rate = growth_rates[min(i-1, len(growth_rates)-1)]
            projected.append(projected[-1] * (1 + rate))
        return projected
    
    def calculate_wacc(self, risk_free_rate: float = 0.04, market_risk_premium: float = 0.07,
                       cost_of_debt: float = 0.03, tax_rate: float = 0.21) -> float:
        """
        WACC = (E/V)*Re + (D/V)*Rd*(1-Tc)
        Simplified: Uses info dict, assumes typical market data
        """
        try:
            debt = float(self.info.get('totalDebt') or 0)
            equity_val = float(self.info.get('marketCap') or 0)
            
            if equity_val <= 0:
                equity_val = 100e9  # Fallback
            
            total_value = equity_val + debt
            
            # Cost of equity: CAPM
            beta = float(self.info.get('beta') or 1.0)
            re = risk_free_rate + beta * market_risk_premium
            
            # WACC
            wacc = (equity_val / total_value) * re + (debt / total_value) * cost_of_debt * (1 - tax_rate)
            return min(max(wacc, 0.05), 0.15)  # Cap between 5% and 15%
        except Exception:
            return 0.08  # Default WACC
    
    def calculate_dcf(self, wacc: float, terminal_growth: float = 0.025, projection_years: int = 5) -> Dict:
        """
        Core DCF calculation
        Returns dict with: pv_fcf, terminal_value, enterprise_value, per_share
        """
        result = {
            "error": None,
            "pv_fcf": 0,
            "terminal_value": 0,
            "enterprise_value": 0,
            "per_share": 0,
            "projected_fcf": [],
            "discount_factors": []
        }
        
        try:
            # Get base FCF
            ttm_revenue = self.get_ttm_revenue()
            fcf_hist = self.get_fcf_history(5)
            
            if not fcf_hist or fcf_hist[-1] <= 0:
                result["error"] = "Insufficient FCF data"
                return result
            
            base_fcf = fcf_hist[-1]
            
            # Project forward
            growth_rates = [0.08] * 2 + [0.05] * (projection_years - 2)  # Deceleration
            projected = self.project_fcf(base_fcf, growth_rates, projection_years)
            
            # Discount
            pv_fcf = 0
            discount_factors = []
            for year, fcf in enumerate(projected, 1):
                df = 1 / ((1 + wacc) ** year)
                pv_fcf += fcf * df
                discount_factors.append(df)
            
            # Terminal value (perpetuity growth)
            terminal_fcf = projected[-1] * (1 + terminal_growth)
            tv = terminal_fcf / (wacc - terminal_growth) if (wacc > terminal_growth) else 0
            pv_tv = tv / ((1 + wacc) ** projection_years)
            
            # Enterprise Value
            enterprise_value = pv_fcf + pv_tv
            
            # Net debt adjustment
            try:
                cash = float(self.info.get('totalCash') or 0)
                debt = float(self.info.get('totalDebt') or 0)
                net_debt = debt - cash
            except Exception:
                net_debt = 0
            
            # Equity value & per share
            equity_value = enterprise_value - net_debt
            shares_outstanding = float(self.info.get('sharesOutstanding') or 1e9)
            per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
            
            result = {
                "error": None,
                "pv_fcf": pv_fcf,
                "terminal_value": pv_tv,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "per_share": per_share,
                "projected_fcf": projected,
                "discount_factors": discount_factors,
                "shares_outstanding": shares_outstanding,
                "net_debt": net_debt,
                "wacc": wacc
            }
        except Exception as e:
            result["error"] = str(e)
        
        return result

    def calculate_dcf_2stage(self, wacc: float, terminal_growth: float = 0.025,
                              growth_rates: Optional[List[float]] = None,
                              projection_years: int = 10) -> Dict:
        """
        2-Stage DCF with explicit per-year growth rates.
        growth_rates: list of annual rates (e.g. [0.10]*5 + [0.06]*5)
        Falls back to calculate_dcf if FCF data unavailable.
        """
        result = {
            "error": None, "pv_fcf": 0, "terminal_value": 0,
            "enterprise_value": 0, "equity_value": 0,
            "per_share": 0, "projected_fcf": [], "discount_factors": [],
            "shares_outstanding": 0, "net_debt": 0, "wacc": wacc
        }
        try:
            fcf_hist = self.get_fcf_history(5)
            if not fcf_hist:
                result["error"] = "No FCF history found"
                return result

            # Use most recent positive FCF; if negative, try average of available
            positive_fcfs = [f for f in fcf_hist if f > 0]
            if positive_fcfs:
                base_fcf = fcf_hist[-1] if fcf_hist[-1] > 0 else positive_fcfs[-1]
            else:
                result["error"] = "All historical FCF values are negative"
                return result

            n = int(projection_years)
            if growth_rates is None or len(growth_rates) == 0:
                growth_rates = [0.08] * min(5, n) + [0.05] * max(0, n - 5)

            # Pad / trim to exactly n years
            while len(growth_rates) < n:
                growth_rates.append(growth_rates[-1])
            growth_rates = growth_rates[:n]

            # Project
            projected = [base_fcf * (1 + growth_rates[0])]
            for i in range(1, n):
                projected.append(projected[-1] * (1 + growth_rates[i]))

            # Discount to PV
            pv_fcf = 0.0
            discount_factors = []
            for year, fcf in enumerate(projected, 1):
                df = 1 / ((1 + wacc) ** year)
                pv_fcf += fcf * df
                discount_factors.append(df)

            # Terminal value (Gordon Growth)
            terminal_fcf = projected[-1] * (1 + terminal_growth)
            tv = terminal_fcf / (wacc - terminal_growth) if wacc > terminal_growth else 0
            pv_tv = tv / ((1 + wacc) ** n)

            enterprise_value = pv_fcf + pv_tv

            # Net debt
            cash = float(self.info.get('totalCash') or 0)
            debt = float(self.info.get('totalDebt') or 0)
            net_debt = debt - cash

            equity_value = enterprise_value - net_debt
            shares_outstanding = float(self.info.get('sharesOutstanding') or 1e9)
            per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0

            result.update({
                "pv_fcf": pv_fcf,
                "terminal_value": pv_tv,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "per_share": per_share,
                "projected_fcf": projected,
                "discount_factors": discount_factors,
                "shares_outstanding": shares_outstanding,
                "net_debt": net_debt,
                "base_fcf": base_fcf,
                "fcf_history": fcf_hist,
                "tv_pct_of_ev": (pv_tv / enterprise_value * 100) if enterprise_value > 0 else 0,
            })
        except Exception as e:
            result["error"] = str(e)
        return result

    def get_implied_growth_rate(self, target_price: float, wacc: float,
                                 terminal_growth: float = 0.025,
                                 projection_years: int = 10) -> Optional[float]:
        """Reverse DCF: binary-search the growth rate implied by target_price."""
        try:
            fcf_hist = self.get_fcf_history(5)
            if not fcf_hist or fcf_hist[-1] <= 0:
                return None
            base_fcf = fcf_hist[-1]
            shares = float(self.info.get('sharesOutstanding') or 1)
            net_debt = float(self.info.get('totalDebt') or 0) - float(self.info.get('totalCash') or 0)
            target_ev = target_price * shares + net_debt

            def ev_for_g(g: float) -> float:
                projected = [base_fcf * (1 + g)]
                for _ in range(1, projection_years):
                    projected.append(projected[-1] * (1 + g))
                pv = sum(f / ((1 + wacc) ** (i + 1)) for i, f in enumerate(projected))
                tv = projected[-1] * (1 + terminal_growth) / (wacc - terminal_growth) if wacc > terminal_growth else 0
                pv_tv = tv / ((1 + wacc) ** projection_years)
                return pv + pv_tv

            lo, hi = -0.30, 2.0
            for _ in range(60):
                mid = (lo + hi) / 2
                if ev_for_g(mid) < target_ev:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# 3. MONTE CARLO DCF
# ─────────────────────────────────────────────────────────────────────────────

class MonteCarloValuation:
    """Monte Carlo DCF: 5000 scenarios varying growth & WACC"""
    
    def __init__(self, dcf: DCFValuation):
        self.dcf = dcf
    
    def run_monte_carlo(self, n_simulations: int = 5000,
                        growth_mean: float = 0.06, growth_std: float = 0.03,
                        wacc_mean: float = 0.08, wacc_std: float = 0.01,
                        terminal_growth_mean: float = 0.025, terminal_growth_std: float = 0.005) -> Dict:
        """
        Run MC simulations 
        Returns distribution of fair values per share
        """
        fair_values = []
        
        for _ in range(n_simulations):
            # Random draws
            growth = np.random.normal(growth_mean, growth_std)
            wacc = np.random.normal(wacc_mean, wacc_std)
            term_growth = np.random.normal(terminal_growth_mean, terminal_growth_std)
            
            # Bounds
            growth = max(0.01, min(growth, 0.20))
            wacc = max(0.02, min(wacc, 0.15))
            term_growth = max(0.0, min(term_growth, wacc - 0.01))
            
            # DCF calc
            result = self.dcf.calculate_dcf(wacc=wacc, terminal_growth=term_growth)
            if not result["error"]:
                fair_values.append(result["per_share"])
        
        fair_values = np.array(fair_values)
        
        return {
            "mean": np.mean(fair_values),
            "median": np.median(fair_values),
            "std": np.std(fair_values),
            "percentile_5": np.percentile(fair_values, 5),
            "percentile_25": np.percentile(fair_values, 25),
            "percentile_75": np.percentile(fair_values, 75),
            "percentile_95": np.percentile(fair_values, 95),
            "min": np.min(fair_values),
            "max": np.max(fair_values),
            "distribution": fair_values
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. VALUATION MULTIPLES
# ─────────────────────────────────────────────────────────────────────────────

class ValuationMultiples:
    """P/E, EV/EBITDA, P/S, P/B ratios vs. sector/industry"""
    
    def __init__(self, ticker: str, fetcher: Optional[FinancialDataFetcher] = None):
        self.ticker = ticker
        self.fetcher = fetcher or FinancialDataFetcher(ticker)
        self.info = self.fetcher.get_info()
    
    def get_multiples(self) -> Dict[str, float]:
        """Extract current valuation multiples"""
        multiples = {}
        
        try:
            # P/E
            multiples['PE_Ratio'] = float(self.info.get('trailingPE') or 0)
            multiples['Forward_PE'] = float(self.info.get('forwardPE') or 0)
            
            # EV / EBITDA
            multiples['EV_EBITDA'] = float(self.info.get('enterpriseToEbitda') or 0)
            
            # Price / Sales
            multiples['PS_Ratio'] = float(self.info.get('priceToSalesTrailing12Months') or 0)
            
            # Price / Book
            multiples['PB_Ratio'] = float(self.info.get('priceToBook') or 0)
            
            # ROE
            multiples['ROE'] = float(self.info.get('returnOnEquity') or 0)
            
            # ROA
            multiples['ROA'] = float(self.info.get('returnOnAssets') or 0)
            
            # Dividend Yield
            multiples['Dividend_Yield'] = float(self.info.get('dividendYield') or 0)
            
            # Debt / Equity
            try:
                debt = float(self.info.get('totalDebt') or 0)
                equity = float(self.info.get('totalAssets') or 0) - debt
                multiples['Debt_to_Equity'] = debt / equity if equity > 0 else 0
            except Exception:
                multiples['Debt_to_Equity'] = 0
            
        except Exception:
            pass
        
        return multiples
    
    def get_peer_comparison(self, sector_multiples: Dict[str, float]) -> pd.DataFrame:
        """
        Compare company multiples vs sector average
        sector_multiples: dict like {'PE_Ratio': 18.5, 'EV_EBITDA': 12.2, ...}
        """
        company = self.get_multiples()
        
        data = []
        for metric, company_value in company.items():
            if metric in sector_multiples:
                sector_value = sector_multiples[metric]
                premium = ((company_value / sector_value) - 1) * 100 if sector_value > 0 else 0
                
                data.append({
                    'Metric': metric,
                    'Company': round(company_value, 2),
                    'Sector Avg': round(sector_value, 2),
                    'Premium %': round(premium, 1)
                })
        
        return pd.DataFrame(data) if data else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# 5. FINANCIAL HEALTH SCORES
# ─────────────────────────────────────────────────────────────────────────────

class AltmanZScore:
    """
    Altman Z-Score for bankruptcy risk
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    Z > 2.99: Safe, Z < 1.81: Distress, 1.81 < Z < 2.99: Grey zone
    """
    
    def __init__(self, fetcher: FinancialDataFetcher):
        self.fetcher = fetcher
        self.balance = fetcher.get_balance_sheet()
        self.income = fetcher.get_income_statement()
        self.info = fetcher.get_info()
    
    def calculate(self) -> Dict:
        """Calculate Altman Z-Score"""
        try:
            if self.balance is None or self.income is None:
                return {"error": "Insufficient balance sheet data"}
            
            # Get values from most recent year (first column)
            def get_val(df, label, idx=0):
                try:
                    return float(df.loc[label].iloc[idx]) if label in df.index else 0
                except Exception:
                    return 0
            
            # X1 = Working Capital / Total Assets
            current_assets = get_val(self.balance, 'Current Assets')
            current_liab = get_val(self.balance, 'Current Liabilities')
            total_assets = get_val(self.balance, 'Total Assets')
            working_cap = current_assets - current_liab
            x1 = working_cap / total_assets if total_assets > 0 else 0
            
            # X2 = Retained Earnings / Total Assets
            retained_earn = get_val(self.balance, 'Retained Earnings')
            x2 = retained_earn / total_assets if total_assets > 0 else 0
            
            # X3 = EBIT / Total Assets
            ebit = get_val(self.income, 'EBIT')
            x3 = ebit / total_assets if total_assets > 0 else 0
            
            # X4 = Market Value of Equity / Book Value of Liabilities
            market_cap = float(self.info.get('marketCap') or 0)
            total_liab = get_val(self.balance, 'Total Liabilities')
            x4 = market_cap / total_liab if total_liab > 0 else 0
            
            # X5 = Sales / Total Assets
            revenue = get_val(self.income, 'Total Revenue')
            x5 = revenue / total_assets if total_assets > 0 else 0
            
            # Calculate
            z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
            
            # Classification
            if z_score > 2.99:
                risk = "Safe Zone"
            elif z_score > 1.81:
                risk = "Grey Zone"
            else:
                risk = "Distress Zone WARNING"
            
            return {
                "z_score": round(z_score, 2),
                "x1_working_cap": round(x1, 3),
                "x2_retained_earn": round(x2, 3),
                "x3_ebit": round(x3, 3),
                "x4_market_equity": round(x4, 3),
                "x5_asset_turnover": round(x5, 3),
                "risk_classification": risk
            }
        except Exception as e:
            return {"error": str(e)}


class PiotroskiFScore:
    """
    Piotroski F-Score: Quality of earnings
    Score 0-9. Higher = better quality
    """
    
    def __init__(self, fetcher: FinancialDataFetcher):
        self.fetcher = fetcher
        self.balance = fetcher.get_balance_sheet()
        self.income = fetcher.get_income_statement()
        self.cash_flow = fetcher.get_cash_flow()
    
    def calculate(self) -> Dict:
        """Calculate Piotroski F-Score"""
        score = 0
        details = {}
        
        try:
            if self.balance is None or self.income is None or self.cash_flow is None:
                return {"error": "Insufficient financial data"}
            
            def get_val(df, label, idx=0):
                try:
                    return float(df.loc[label].iloc[idx]) if label in df.index else None
                except Exception:
                    return None
            
            # Profitability (4 signals)
            roa_curr = get_val(self.income, 'Net Income') / get_val(self.balance, 'Total Assets')
            roa_prev = get_val(self.income, 'Net Income', 1) / get_val(self.balance, 'Total Assets')
            if roa_curr and roa_curr > 0:
                score += 1
                details['Profitability'] = "PASS"
            if roa_curr and roa_prev and roa_curr > roa_prev:
                score += 1
                details['ROA Trend'] = "PASS"
            
            op_cf = get_val(self.cash_flow, 'Operating Cash Flow')
            if op_cf and op_cf > 0:
                score += 1
                details['Operating CF'] = "PASS"
            
            accruals = (get_val(self.income, 'Net Income') or 0) - (op_cf or 0)
            if accruals < 0:  # Positive = quality earnings
                score += 1
                details['Quality'] = "PASS"
            
            # Leverage/Debt (3 signals)
            curr_ratio_curr = get_val(self.balance, 'Current Assets') / get_val(self.balance, 'Current Liabilities')
            curr_ratio_prev = get_val(self.balance, 'Current Assets', 1) / get_val(self.balance, 'Current Liabilities', 1)
            if curr_ratio_curr and curr_ratio_prev and curr_ratio_curr > curr_ratio_prev:
                score += 1
                details['Liquidity'] = "PASS"
            
            shares_out = get_val(self.balance, 'Common Stock Shares Outstanding')
            shares_prev = get_val(self.balance, 'Common Stock Shares Outstanding', 1)
            if shares_out and shares_prev and shares_out <= shares_prev:
                score += 1
                details['Share Dilution'] = "PASS"
            
            # Asset Efficiency (2 signals)
            asset_turnover = get_val(self.income, 'Total Revenue', 0) / get_val(self.balance, 'Total Assets', 0)
            asset_turnover_prev = get_val(self.income, 'Total Revenue', 1) / get_val(self.balance, 'Total Assets', 1)
            if asset_turnover and asset_turnover_prev and asset_turnover > asset_turnover_prev:
                score += 1
                details['Asset Efficiency'] = "PASS"
            
            gross_margin = (get_val(self.income, 'Total Revenue', 0) or 0) - (get_val(self.income, 'Cost Of Goods Sold', 0) or 0)
            gross_margin_prev = (get_val(self.income, 'Total Revenue', 1) or 0) - (get_val(self.income, 'Cost Of Goods Sold', 1) or 0)
            if gross_margin and gross_margin_prev and gross_margin > gross_margin_prev:
                score += 1
                details['Margin Quality'] = "PASS"
            
            return {
                "f_score": score,
                "rating": f"{score}/9 - {'Excellent' if score >= 8 else 'Good' if score >= 5 else 'Weak'}",
                "details": details
            }
        except Exception as e:
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 6. ANALYST CONSENSUS
# ─────────────────────────────────────────────────────────────────────────────

class AnalystConsensus:
    """Fetch analyst ratings, target price, and recommendations"""
    
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.yf_ticker = yf.Ticker(ticker)
    
    def get_consensus(self) -> Dict:
        """Extract analyst data"""
        try:
            info = self.yf_ticker.info
            
            result = {
                "target_price": float(info.get('targetMeanPrice') or 0),
                "high_target": float(info.get('targetHighPrice') or 0),
                "low_target": float(info.get('targetLowPrice') or 0),
                "recommendation": info.get('recommendationKey', 'N/A'),
                "recommendations_count": float(info.get('numberOfAnalysts') or 0),
                "one_month_target": float(info.get('targetMeanPrice') or 0),
            }
            
            return result
        except Exception:
            return {"error": "Unable to fetch analyst consensus"}


# ─────────────────────────────────────────────────────────────────────────────
# 7. INSIDER & INSTITUTIONAL OWNERSHIP
# ─────────────────────────────────────────────────────────────────────────────

class Ownership:
    """Top shareholders, institutional ownership, insider ownership"""
    
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.info = yf.Ticker(ticker).info
    
    def get_ownership_stats(self) -> Dict:
        """Get ownership percentages"""
        try:
            return {
                "institutional_ownership": float(self.info.get('institutionPercent') or 0),
                "insider_ownership": float(self.info.get('insiderPercent') or 0),
                "shares_outstanding": float(self.info.get('sharesOutstanding') or 0),
                "shares_float": float(self.info.get('floatShares') or 0),
            }
        except Exception:
            return {}


# ─────────────────────────────────────────────────────────────────────────────
# 8. SENSITIVITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class SensitivityAnalysis:
    """WACC vs Terminal Growth heatmap"""
    
    @staticmethod
    def create_sensitivity_matrix(dcf: DCFValuation,
                                   wacc_range: Tuple[float, float] = (0.05, 0.12),
                                   growth_range: Tuple[float, float] = (0.01, 0.04),
                                   steps: int = 7) -> pd.DataFrame:
        """
        Create matrix of fair values for different WACC and terminal growth scenarios
        """
        waccs = np.linspace(wacc_range[0], wacc_range[1], steps)
        growths = np.linspace(growth_range[0], growth_range[1], steps)
        
        matrix = pd.DataFrame(index=[f"{g*100:.1f}%" for g in growths],
                            columns=[f"{w*100:.1f}%" for w in waccs])
        
        for i, wacc in enumerate(waccs):
            for j, growth in enumerate(growths):
                if wacc > growth:
                    result = dcf.calculate_dcf(wacc=wacc, terminal_growth=growth)
                    matrix.iloc[j, i] = result.get("per_share", 0)
                else:
                    matrix.iloc[j, i] = 0
        
        return matrix.astype(float)


# ─────────────────────────────────────────────────────────────────────────────
# OVERALL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def run_full_analysis(ticker: str) -> Dict:
    """Run complete fundamental analysis pipeline"""
    
    try:
        # Fetch data
        fetcher = FinancialDataFetcher(ticker)
        
        # DCF
        dcf = DCFValuation(ticker, fetcher)
        wacc = dcf.calculate_wacc()
        dcf_result = dcf.calculate_dcf(wacc=wacc)
        
        # Monte Carlo
        mc = MonteCarloValuation(dcf)
        mc_result = mc.run_monte_carlo()
        
        # Multiples
        multiples = ValuationMultiples(ticker, fetcher)
        comp_multiples = multiples.get_multiples()
        
        # Health scores
        altman = AltmanZScore(fetcher).calculate()
        piotroski = PiotroskiFScore(fetcher).calculate()
        
        # Analyst consensus
        consensus = AnalystConsensus(ticker).get_consensus()
        
        # Ownership
        ownership = Ownership(ticker).get_ownership_stats()
        
        return {
            "ticker": ticker,
            "dcf": dcf_result,
            "monte_carlo": mc_result,
            "multiples": comp_multiples,
            "altman_z": altman,
            "piotroski_f": piotroski,
            "analyst_consensus": consensus,
            "ownership": ownership,
            "wacc": wacc
        }
    
    except Exception as e:
        return {"error": str(e)}
