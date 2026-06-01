"""
Ravinala by TSIVAHINY Matthias - Utilities: PDF generation, data helpers, and market data integration.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import io
import base64
from scipy.stats import norm

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# Legacy functions maintained for compatibility
def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d1 parameter for Black-Scholes formula."""
    return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def d2(d1_val: float, sigma: float, T: float) -> float:
    """Calculate d2 parameter for Black-Scholes formula."""
    return d1_val - sigma * np.sqrt(T)


def validate_inputs(S: float, K: float, T: float, r: float, sigma: float) -> None:
    """Validate input parameters for option pricing."""
    if S <= 0:
        raise ValueError("Spot price (S) must be positive")
    if K <= 0:
        raise ValueError("Strike price (K) must be positive")
    if T <= 0:
        raise ValueError("Time to expiration (T) must be positive")
    if sigma <= 0:
        raise ValueError("Volatility (sigma) must be positive")


def vanna(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Vanna (d/dS d/dsigma): sensitivity of Delta to volatility changes."""
    validate_inputs(S, K, T, r, sigma)
    d1_val = d1(S, K, T, r, sigma)
    d2_val = d2(d1_val, sigma, T)
    return -norm.pdf(d1_val) * d2_val / sigma


def volga(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Volga (d²/dsigma²): sensitivity of Vega to volatility changes."""
    validate_inputs(S, K, T, r, sigma)
    d1_val = d1(S, K, T, r, sigma)
    d2_val = d2(d1_val, sigma, T)
    return S * norm.pdf(d1_val) * np.sqrt(T) * d1_val * d2_val / (100 * sigma)


# === Ravinala Enhanced Functions ===

def generate_term_sheet_pdf(
    product_name: str,
    parameters: Dict,
    greeks: Dict,
    price: float,
    filename: Optional[str] = None,
) -> Optional[bytes]:
    """
    Generate a professional Term Sheet PDF for a structured product.

    Returns PDF as bytes if reportlab available, else None.
    """
    if not HAS_REPORTLAB:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#16213e'),
        spaceAfter=8,
        spaceBefore=10,
    )

    elements = []

    elements.append(Paragraph(f"<b>{product_name}</b>", title_style))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("<b>TERM SHEET</b>", heading_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 0.1*inch))

    elements.append(Paragraph("<b>Market Parameters</b>", heading_style))
    param_data = [['Parameter', 'Value']]
    for key, value in parameters.items():
        if isinstance(value, float):
            param_data.append([str(key), f"{value:.4f}"])
        else:
            param_data.append([str(key), str(value)])

    param_table = Table(param_data, colWidths=[2.5*inch, 2.5*inch])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(param_table)
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("<b>Valuation Results</b>", heading_style))
    price_text = f"<b>Fair Value (Par = 100): {price:.2f}</b>"
    elements.append(Paragraph(price_text, ParagraphStyle('Price', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#e94560'))))
    elements.append(Spacer(1, 0.1*inch))

    if greeks:
        elements.append(Paragraph("<b>Risk Greeks</b>", heading_style))
        greek_data = [['Greek', 'Value', 'Interpretation']]

        interpretations = {
            'delta': 'Sensitivity to spot price change',
            'gamma': 'Convexity / Delta acceleration',
            'vega': 'Sensitivity to volatility (per 1%)',
            'theta': 'Time decay (per day)',
            'rho': 'Interest rate sensitivity (per 1%)',
            'vanna': 'Spot-Vol cross correlation',
            'volga': 'Volatility-of-volatility sensitivity',
        }

        for greek_name, greek_value in greeks.items():
            if isinstance(greek_value, float):
                interp = interpretations.get(greek_name, 'N/A')
                greek_data.append([greek_name.upper(), f"{greek_value:.6f}", interp])

        greek_table = Table(greek_data, colWidths=[1.2*inch, 1.2*inch, 3.1*inch])
        greek_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        elements.append(greek_table)

    elements.append(Spacer(1, 0.3*inch))

    elements.append(Paragraph("<b>Risk Disclosure</b>", heading_style))
    disclaimer_text = """
    This term sheet is for illustrative purposes only. Actual structured products carry substantial risks including credit risk of issuer,
    market risk, liquidity risk, and correlation risk. Past performance does not guarantee future results. Investors should consult with
    a financial advisor before investing in structured products.
    """
    elements.append(Paragraph(disclaimer_text, styles['Normal']))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if filename:
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def format_greeks_table(greeks: Dict) -> pd.DataFrame:
    """Format Greeks dictionary into a clean DataFrame."""
    greek_symbols = {
        'delta': 'Δ',
        'gamma': 'Γ',
        'vega': 'ν',
        'theta': 'Θ',
        'rho': 'ρ',
        'vanna': 'Vanna',
        'volga': 'Volga',
    }

    data = []
    for key, value in greeks.items():
        symbol = greek_symbols.get(key, key)
        meaning = {
            'delta': 'Spot sensitivity',
            'gamma': 'Delta acceleration',
            'vega': 'Vol sensitivity (per 1%)',
            'theta': 'Time decay (per day)',
            'rho': 'Rate sensitivity (per 1%)',
            'vanna': 'Spot-Vol correlation',
            'volga': 'Vol-of-Vol sensitivity',
        }.get(key, 'N/A')

        data.append({
            'Greek': symbol,
            'Value': f"{value:.6f}",
            'Meaning': meaning,
        })

    return pd.DataFrame(data)


def create_correlation_matrix(
    n_assets: int,
    target_corr: float = 0.5,
    force_positive_definite: bool = True,
) -> np.ndarray:
    """Create a correlation matrix with approximate target correlation."""
    corr = np.ones((n_assets, n_assets)) * target_corr
    np.fill_diagonal(corr, 1.0)

    if force_positive_definite:
        eigenvalues = np.linalg.eigvalsh(corr)
        if np.any(eigenvalues <= 0):
            corr += np.eye(n_assets) * 0.1
            corr = (corr + corr.T) / 2

    return corr


def format_number(value: float, decimal_places: int = 2, percentage: bool = False) -> str:
    """Format a number for display."""
    if percentage:
        return f"{value * 100:.{decimal_places}f}%"
    else:
        return f"{value:.{decimal_places}f}"


def get_market_data_yfinance(tickers: List[str], period: str = '5y') -> Optional[pd.DataFrame]:
    """Fetch historical market data using yfinance."""
    try:
        import yfinance as yf
        data = yf.download(tickers, period=period, progress=False)
        if len(tickers) == 1:
            return pd.DataFrame({tickers[0]: data['Adj Close']})
        else:
            return data['Adj Close']
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def compute_historical_volatility(
    price_series: pd.Series,
    periods: int = 252,
) -> float:
    """Compute annualized historical volatility from price series."""
    returns = price_series.pct_change().dropna()
    return returns.std() * np.sqrt(periods)


def compute_rolling_correlation(
    price_df: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """Compute rolling correlation matrix."""
    returns = price_df.pct_change().dropna()
    return returns.rolling(window).corr()
