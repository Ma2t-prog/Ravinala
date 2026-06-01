"""Generate professional PDF risk reports for GenesiX portfolios."""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional
import json

try:
    from fpdf import FPDF
except ImportError:  # pragma: no cover - optional dependency
    FPDF = None
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Constants
PAGE_WIDTH = 210  # A4 width in mm
PAGE_HEIGHT = 297  # A4 height in mm
MARGIN = 15


class GenesiXReport(FPDF if FPDF is not None else object):
    """Professional PDF report generator."""
    
    def __init__(self, portfolio_name: str = "My Portfolio"):
        self.portfolio_name = portfolio_name
        self._fpdf_available = FPDF is not None
        if self._fpdf_available:
            super().__init__(orientation='P', unit='mm', format='A4')
            self.set_auto_page_break(auto=True, margin=MARGIN)
            self.page_num = 0
    
    def header(self):
        """Page header with title and date."""
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(30, 30, 30)
        title = f'GenesiX Risk Report — {self.portfolio_name}'
        self.cell(120, 8, title, align='L', border=0)
        
        self.set_font('Helvetica', '', 8)
        self.set_text_color(100, 100, 100)
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        self.cell(0, 8, date_str, align='R', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.set_draw_color(200, 200, 200)
        self.line(MARGIN, self.get_y(), PAGE_WIDTH - MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)
    
    def footer(self):
        """Page footer with disclaimer."""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(100, 100, 100)
        page_text = f'Page {self.page_no()} — GenesiX by Ravinala — For educational purposes only'
        self.cell(0, 10, page_text, align='C', border=0)
    
    def generate(self, results: dict, portfolio_weights: dict, investment: float) -> bytes:
        """
        Generate complete PDF report.
        
        Args:
            results: Portfolio analysis results dict
            portfolio_weights: {asset: weight} dict
            investment: Investment amount (EUR)
        
        Returns:
            PDF as bytes
        """
        if not self._fpdf_available:
            return self._generate_reportlab(results, portfolio_weights, investment)

        self.alias_nb_pages()
        
        # Build report sections
        self._add_cover_page(investment)
        self._add_executive_summary(results, investment)
        self._add_portfolio_composition(portfolio_weights, investment)
        self._add_risk_analysis(results, investment)
        self._add_scenario_analysis(results, investment)
        self._add_recommendations(results)
        self._add_disclaimer()
        
        # Return PDF as bytes
        return bytes(self.output())

    def _generate_reportlab(self, results: dict, portfolio_weights: dict, investment: float) -> bytes:
        """Rich PDF fallback when `fpdf2` is unavailable."""
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        pred = results.get('prediction', {})
        risk = results.get('risk_metrics', {})
        scenarios = results.get('scenarios', [])
        recommendations = results.get('recommendations', [])
        concerns = results.get('top_concerns', [])

        def draw_block(title: str, lines: list[str], y: float) -> float:
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(50, y, title)
            y -= 18
            pdf.setFont("Helvetica", 10)
            for line in lines:
                pdf.drawString(60, y, line[:110])
                y -= 14
            return y - 6

        y = height - 50
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, y, f"GenesiX Risk Report - {self.portfolio_name}")
        y -= 26
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Generated: {datetime.now().isoformat()}")
        y -= 14
        pdf.drawString(50, y, f"Investment: EUR {investment:,.2f}")
        y -= 14
        pdf.drawString(50, y, f"Assets: {', '.join(sorted(portfolio_weights.keys())) or 'N/A'}")
        y -= 24

        y = draw_block(
            "Executive Summary",
            [
                f"Expected return: {pred.get('expected_return_pct', results.get('expected_return', 0)):+.2f}%",
                f"Probability positive: {pred.get('probability_positive', 0):.1%}",
                f"Worst case: {pred.get('worst_case_pct', 0):+.2f}%",
                f"Best case: {pred.get('best_case_pct', 0):+.2f}%",
                f"Annual volatility: {risk.get('volatility_annualized', 0):.1%}",
                f"VaR 95: {risk.get('var_95', 0):.2%}",
                f"CVaR 95: {risk.get('cvar_95', 0):.2%}",
                f"Sharpe ratio: {risk.get('sharpe_ratio', 0):.2f}",
            ],
            y,
        )
        y = draw_block(
            "Portfolio Composition",
            [f"{asset}: {weight:.1%} / EUR {investment * weight:,.2f}" for asset, weight in sorted(portfolio_weights.items())],
            y,
        )

        if y < 180:
            pdf.showPage()
            y = height - 50

        scenario_lines = [
            f"{item.get('name', 'Scenario')}: p={item.get('probability', 0):.0%}, return={item.get('return_pct', 0):+.2f}%, final={item.get('final_value', 0):,.2f}"
            for item in scenarios
        ] or ["No scenarios available"]
        y = draw_block("Scenario Analysis", scenario_lines, y)

        concern_lines = [str(item) for item in concerns] or ["No major concern flagged"]
        y = draw_block("Top Concerns", concern_lines[:8], y)

        if y < 140:
            pdf.showPage()
            y = height - 50

        recommendation_lines = [str(item) for item in recommendations] or ["No recommendation supplied"]
        y = draw_block("Recommendations", recommendation_lines[:10], y)

        raw_json = json.dumps(results, indent=2, default=str)
        json_lines = []
        for raw_line in raw_json.splitlines():
            if len(raw_line) <= 96:
                json_lines.append(raw_line)
            else:
                for start in range(0, len(raw_line), 96):
                    json_lines.append(raw_line[start:start + 96])

        pdf.showPage()
        y = height - 50
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "Appendix - Serialized Results")
        y -= 20
        pdf.setFont("Courier", 8)
        for line in json_lines[:140]:
            if y < 45:
                pdf.showPage()
                y = height - 45
                pdf.setFont("Courier", 8)
            pdf.drawString(40, y, line)
            y -= 9

        pdf.save()
        return buffer.getvalue()
    
    def _add_cover_page(self, investment: float):
        """Full-page cover."""
        self.add_page()
        self.set_font('Helvetica', 'B', 40)
        self.set_text_color(30, 30, 100)
        self.ln(70)
        self.cell(0, 25, 'GenesiX', align='C', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('Helvetica', '', 20)
        self.set_text_color(60, 60, 60)
        self.cell(0, 12, 'Risk Intelligence Report', align='C', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.ln(30)
        self.set_font('Helvetica', '', 14)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, f'Portfolio: {self.portfolio_name}', align='C', border=0, new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 10, f'Investment: €{investment:,.2f}', align='C', border=0, new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 10, f'Date: {datetime.now().strftime("%B %d, %Y")}', 
                  align='C', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.ln(20)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, 
            'This report is generated by GenesiX and provides risk analytics, scenario analysis, '
            'and predictions based on machine learning. It is for educational purposes only and does not '
            'constitute financial advice.'
        )
    
    def _add_executive_summary(self, results: dict, investment: float):
        """Key metrics summary page."""
        self.add_page()
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'Executive Summary', border=0, new_x='LMARGIN', new_y='NEXT')
        self.ln(5)
        
        pred = results.get('prediction', {})
        rm = results.get('risk_metrics', {})
        
        self.set_font('Helvetica', '', 11)
        rows = [
            ('Expected Value', f"€{investment * (1 + pred.get('expected_return_pct', 0)/100):,.2f}"),
            ('Expected Return', f"{pred.get('expected_return_pct', 0):+.2f}%"),
            ('Probability of Profit', f"{pred.get('probability_positive', 0):.1%}"),
            ('P(5th percentile)', f"€{investment * (1 + pred.get('worst_case_pct', 0)/100):,.2f}"),
            ('P(95th percentile)', f"€{investment * (1 + pred.get('best_case_pct', 0)/100):,.2f}"),
            ('', ''),
            ('Annual Volatility', f"{rm.get('volatility_annualized', 0):.1%}"),
            ('VaR 95% (1-day)', f"{rm.get('var_95', 0):.2%}"),
            ('CVaR 95% (Expected Shortfall)', f"{rm.get('cvar_95', 0):.2%}"),
            ('Sharpe Ratio', f"{rm.get('sharpe_ratio', 0):.2f}"),
        ]
        
        for label, value in rows:
            if label == '':
                self.ln(2)
            else:
                self.set_font('Helvetica', '', 11)
                self.cell(120, 7, label, border=0)
                self.set_font('Helvetica', 'B', 11)
                self.cell(70, 7, value, align='R', border=0, new_x='LMARGIN', new_y='NEXT')
        
        # Top concerns
        concerns = results.get('top_concerns', [])
        if concerns:
            self.ln(8)
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 8, 'Key Concerns', border=0, new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', '', 10)
            for concern in concerns[:5]:
                self.cell(0, 6, f'• {concern}', border=0, new_x='LMARGIN', new_y='NEXT')
    
    def _add_portfolio_composition(self, weights: dict, investment: float):
        """Portfolio composition and weights."""
        self.add_page()
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'Portfolio Composition', border=0, new_x='LMARGIN', new_y='NEXT')
        self.ln(5)
        
        # Weights table
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(230, 230, 230)
        self.cell(80, 7, 'Asset', border=1, fill=True)
        self.cell(40, 7, 'Weight', align='R', border=1, fill=True)
        self.cell(50, 7, 'Amount (€)', align='R', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('Helvetica', '', 10)
        total_amount = 0
        for asset, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            amount = investment * weight
            total_amount += amount
            
            self.cell(80, 6, asset, border=1)
            self.cell(40, 6, f'{weight:.1%}', align='R', border=1)
            self.cell(50, 6, f'€{amount:,.2f}', align='R', border=1, new_x='LMARGIN', new_y='NEXT')
        
        # Total row
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(80, 7, 'TOTAL', border=1, fill=True)
        self.cell(40, 7, '100.0%', align='R', border=1, fill=True)
        self.cell(50, 7, f'€{total_amount:,.2f}', align='R', border=1, fill=True, 
                  new_x='LMARGIN', new_y='NEXT')
    
    def _add_risk_analysis(self, results: dict, investment: float):
        """Risk metrics and analysis."""
        self.add_page()
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'Risk Analysis', border=0, new_x='LMARGIN', new_y='NEXT')
        self.ln(5)
        
        rm = results.get('risk_metrics', {})
        
        # Risk summary
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Value at Risk (VaR)', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('Helvetica', '', 10)
        var_1day = rm.get('var_95', 0)
        var_5day = rm.get('var_95_5d', 0)
        var_21day = rm.get('var_95_21d', 0)
        
        rows = [
            (f'1-day loss (95% confidence)', f'€{investment * var_1day:,.2f} ({var_1day:.2%})'),
            (f'5-day loss (95% confidence)', f'€{investment * var_5day:,.2f} ({var_5day:.2%})'),
            (f'21-day loss (95% confidence)', f'€{investment * var_21day:,.2f} ({var_21day:.2%})'),
        ]
        
        for label, value in rows:
            self.cell(120, 6, label, border=0)
            self.cell(70, 6, value, align='R', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Volatility Metrics', border=0, new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('Helvetica', '', 10)
        vol_rows = [
            ('Annualized Volatility', f"{rm.get('volatility_annualized', 0):.1%}"),
            ('Maximum Drawdown', f"{rm.get('max_drawdown', 0):.1%}"),
            ('Diversification Ratio', f"{rm.get('diversification_ratio', 1):.2f}"),
        ]
        
        for label, value in vol_rows:
            self.cell(120, 6, label, border=0)
            self.cell(70, 6, value, align='R', border=0, new_x='LMARGIN', new_y='NEXT')
    
    def _add_scenario_analysis(self, results: dict, investment: float):
        """Scenario outcomes."""
        self.add_page()
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'Scenario Analysis', border=0, new_x='LMARGIN', new_y='NEXT')
        self.ln(5)
        
        scenarios = results.get('scenarios', [])
        if not scenarios:
            self.set_font('Helvetica', '', 10)
            self.cell(0, 8, 'No scenario data available.', border=0)
            return
        
        # Scenarios table
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(230, 230, 230)
        self.cell(35, 7, 'Scenario', border=1, fill=True)
        self.cell(35, 7, 'Probability', align='C', border=1, fill=True)
        self.cell(40, 7, 'Return', align='C', border=1, fill=True)
        self.cell(60, 7, 'Final Value (€)', align='R', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('Helvetica', '', 10)
        for scenario in scenarios:
            name = scenario.get('name', 'Unknown')
            prob = scenario.get('probability', 0)
            ret = scenario.get('return_pct', 0)
            final = scenario.get('final_value', 0)
            
            self.cell(35, 6, name, border=1)
            self.cell(35, 6, f'{prob:.1%}', align='C', border=1)
            self.cell(40, 6, f'{ret:+.1f}%', align='C', border=1)
            self.cell(60, 6, f'€{final:,.2f}', align='R', border=1, new_x='LMARGIN', new_y='NEXT')
    
    def _add_recommendations(self, results: dict):
        """Actionable recommendations."""
        self.add_page()
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'Recommendations', border=0, new_x='LMARGIN', new_y='NEXT')
        self.ln(5)
        
        recommendations = results.get('recommendations', [])
        if not recommendations:
            recommendations = [
                'Review portfolio allocation regularly (at least quarterly)',
                'Monitor macro-economic indicators and news flow',
                'Rebalance when asset weights drift >5% from targets',
                'Consider portfolio volatility and VaR limits',
                'Evaluate new assets using GenesiX analysis before adding',
            ]
        
        self.set_font('Helvetica', '', 10)
        for i, rec in enumerate(recommendations[:6], 1):
            self.multi_cell(0, 5, f'{i}. {rec}', new_x='LMARGIN', new_y='NEXT')
            self.ln(2)
    
    def _add_disclaimer(self):
        """Legal disclaimer."""
        self.add_page()
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Disclaimer', border=0, new_x='LMARGIN', new_y='NEXT')
        self.set_font('Helvetica', '', 9)
        
        disclaimer_text = (
            "This report is generated by GenesiX, a module of Ravinala, for educational and research "
            "purposes only. It does NOT constitute financial advice, investment recommendation, or "
            "solicitation to buy or sell any financial instrument.\n\n"
            
            "Past performance is not indicative of future results. All predictions and scenarios are "
            "based on statistical models and historical data, which may not accurately reflect future "
            "market conditions.\n\n"
            
            "Machine Learning Models: GenesiX uses ensemble methods including XGBoost, LightGBM, "
            "Random Forest, GARCH, and LSTM. Model accuracy varies by market regime and asset class. "
            "Out-of-sample backtest accuracy is typically 48-58% for directional predictions.\n\n"
            
            "Risk Models: VaR (Value at Risk) is computed using historical simulation, parametric "
            "method, Cornish-Fisher expansion, and Monte Carlo. Each method has limitations and may "
            "underestimate risk during regime changes.\n\n"
            
            "Data Sources and Quality:\n"
            "• yfinance (free, delays possible)\n"
            "• FRED (US macro, delayed)\n"
            "• World Bank (quarterly updates)\n"
            "• Google Trends (11-month lag)\n"
            "• News API (headlines only, sentiment varies)\n\n"
            
            "No guarantees: GenesiX provides analytical outputs only. Investment decisions should "
            "incorporate your own risk tolerance, investment horizon, and financial situation.\n\n"
            
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            "© 2026 GenesiX by Ravinala — Educational Use Only"
        )
        
        self.multi_cell(0, 4, disclaimer_text)
