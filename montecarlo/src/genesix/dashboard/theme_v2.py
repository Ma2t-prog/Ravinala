"""
GenesiX visual system — Bloomberg meets modern fintech.

Every component in GenesiX uses this theme. No exceptions.
No element renders without going through this system.

Philosophy: Data density + clarity. Every pixel is data. Every color is signal.
Dark theme (Bloomberg DNA) + smooth fintech interactions.
"""

import plotly.graph_objects as go
import plotly.io as pio

# ============================================================
# COLOR SYSTEM
# ============================================================

COLORS = {
    # Backgrounds (darkest to lightest)
    'bg_void': '#06080d',       # deepest background (behind everything)
    'bg_primary': '#0a0e17',    # main app background
    'bg_card': '#111827',       # card/panel background
    'bg_elevated': '#1a2235',   # elevated elements (dropdowns, tooltips)
    'bg_hover': '#1e293b',      # hover state on rows/cards
    'bg_active': '#253349',     # active/selected state
    
    # Borders
    'border_subtle': 'rgba(255,255,255,0.04)',   # barely visible structure
    'border_default': 'rgba(255,255,255,0.07)',  # standard borders
    'border_strong': 'rgba(255,255,255,0.12)',   # emphasized borders
    'border_focus': 'rgba(59,130,246,0.5)',      # focus rings
    
    # Text
    'text_primary': '#f1f5f9',     # primary content (white-ish)
    'text_secondary': '#94a3b8',   # secondary labels
    'text_tertiary': '#475569',    # hints, disabled, metadata
    'text_muted': '#334155',       # very subtle (borders, rules)
    
    # Signal colors (ONLY for meaning, never decoration)
    'positive': '#22c55e',         # up, profit, bullish, good
    'positive_muted': '#166534',   # subtle positive background
    'positive_bg': 'rgba(34,197,94,0.08)',
    'negative': '#ef4444',         # down, loss, bearish, bad
    'negative_muted': '#7f1d1d',   # subtle negative background
    'negative_bg': 'rgba(239,68,68,0.08)',
    'warning': '#f59e0b',          # caution, elevated risk
    'warning_bg': 'rgba(245,158,11,0.08)',
    'info': '#3b82f6',             # neutral info, selected
    'info_bg': 'rgba(59,130,246,0.08)',
    'critical': '#dc2626',         # extreme risk, alerts
    'critical_bg': 'rgba(220,38,38,0.12)',
    
    # Asset class colors (consistent across all views)
    'asset_equity': '#3b82f6',
    'asset_crypto': '#f59e0b',
    'asset_commodity': '#eab308',
    'asset_bond': '#06b6d4',
    'asset_fx': '#8b5cf6',
    'asset_index': '#64748b',
    
    # Alert level colors
    'alert_green': '#22c55e',
    'alert_yellow': '#fbbf24',
    'alert_orange': '#f97316',
    'alert_red': '#ef4444',
    'alert_black': '#dc2626',
    
    # Chart colors (ordered for multi-series)
    'chart_1': '#3b82f6',
    'chart_2': '#22c55e',
    'chart_3': '#f59e0b',
    'chart_4': '#ef4444',
    'chart_5': '#8b5cf6',
    'chart_6': '#06b6d4',
    'chart_7': '#ec4899',
    'chart_8': '#84cc16',
}

# ============================================================
# TYPOGRAPHY
# ============================================================

FONTS = {
    'display': "'DM Sans', system-ui, -apple-system, sans-serif",
    'body': "'DM Sans', system-ui, -apple-system, sans-serif",
    'mono': "'JetBrains Mono', 'Fira Code', 'IBM Plex Mono', monospace",
    'data': "'JetBrains Mono', 'Fira Code', monospace",  # alias for numbers
}

# ============================================================
# GLOBAL CSS (inject at top of every page)
# ============================================================

GENESIX_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700&family=JetBrains+Mono:ital,wght@0,400;0,500;0,700&display=swap');

/* Reset Streamlit defaults */
.stApp {{
    background: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: {FONTS['body']};
}}
.stApp header {{
    background: {COLORS['bg_void']} !important;
    border-bottom: 1px solid {COLORS['border_default']} !important;
}}
section[data-testid="stSidebar"] {{
    background: {COLORS['bg_void']} !important;
    border-right: 1px solid {COLORS['border_default']} !important;
}}
section[data-testid="stSidebar"] .stMarkdown p {{
    color: {COLORS['text_secondary']};
}}

/* Custom scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {COLORS['border_strong']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.2); }}

/* Data numbers — always monospace */
.gx-num {{
    font-family: {FONTS['mono']};
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
}}

/* Signal colors */
.gx-pos {{ color: {COLORS['positive']} !important; }}
.gx-neg {{ color: {COLORS['negative']} !important; }}
.gx-warn {{ color: {COLORS['warning']} !important; }}
.gx-info {{ color: {COLORS['info']} !important; }}
.gx-crit {{ color: {COLORS['critical']} !important; }}

/* Cards */
.gx-card {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 4px;
    padding: 16px;
    transition: border-color 0.15s ease;
}}
.gx-card:hover {{
    border-color: {COLORS['border_strong']};
}}

/* Data tables (Bloomberg style) */
.gx-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.gx-table th {{
    text-align: left;
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {COLORS['text_tertiary']};
    border-bottom: 1px solid {COLORS['border_strong']};
    background: {COLORS['bg_void']};
    position: sticky;
    top: 0;
    z-index: 1;
    cursor: pointer;
    user-select: none;
}}
.gx-table th:hover {{
    color: {COLORS['text_secondary']};
}}
.gx-table td {{
    padding: 7px 12px;
    border-bottom: 1px solid {COLORS['border_subtle']};
    font-family: {FONTS['mono']};
    font-size: 13px;
    color: {COLORS['text_primary']};
}}
.gx-table tr:hover td {{
    background: {COLORS['bg_hover']};
}}
.gx-table tr:nth-child(even) td {{
    background: rgba(255,255,255,0.01);
}}
.gx-table .td-label {{
    font-family: {FONTS['body']};
    font-weight: 500;
    color: {COLORS['text_secondary']};
}}
.gx-table .td-ticker {{
    font-family: {FONTS['mono']};
    font-weight: 700;
    color: {COLORS['text_primary']};
}}

/* KPI metric cards */
.gx-metric {{
    padding: 12px 16px;
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_default']};
    border-radius: 4px;
    border-left: 3px solid;
}}
.gx-metric-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {COLORS['text_tertiary']};
    margin-bottom: 4px;
}}
.gx-metric-value {{
    font-family: {FONTS['mono']};
    font-size: 22px;
    font-weight: 700;
    color: {COLORS['text_primary']};
    line-height: 1.2;
}}
.gx-metric-delta {{
    font-family: {FONTS['mono']};
    font-size: 12px;
    margin-top: 2px;
}}

/* Tags/Badges */
.gx-tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: {FONTS['mono']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
}}

/* Status bar (market ticker) */
.gx-status-bar {{
    display: flex;
    gap: 24px;
    padding: 6px 16px;
    background: {COLORS['bg_void']};
    border-bottom: 1px solid {COLORS['border_default']};
    font-family: {FONTS['mono']};
    font-size: 12px;
    overflow-x: auto;
    white-space: nowrap;
}}
.gx-status-item {{
    display: flex;
    align-items: center;
    gap: 6px;
}}
.gx-status-ticker {{
    color: {COLORS['text_tertiary']};
    font-weight: 600;
}}

/* Sparkline */
.gx-sparkline {{
    display: inline-block;
    vertical-align: middle;
    margin-left: 8px;
}}

/* Animations */
@keyframes gx-fade-in {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes gx-shimmer {{
    0% {{ background-position: -200px 0; }}
    100% {{ background-position: 200px 0; }}
}}
.gx-animate {{
    animation: gx-fade-in 0.3s ease-out both;
}}
.gx-skeleton {{
    background: linear-gradient(90deg, {COLORS['bg_card']} 25%, {COLORS['bg_elevated']} 50%, {COLORS['bg_card']} 75%);
    background-size: 400px 100%;
    animation: gx-shimmer 1.5s ease-in-out infinite;
    border-radius: 4px;
}}
"""

# ============================================================
# HTML COMPONENT BUILDERS
# ============================================================

def inject_theme():
    """Call at the top of every GenesiX page."""
    import streamlit as st
    st.markdown(f"<style>{GENESIX_CSS}</style>", unsafe_allow_html=True)


def market_status_bar(data: dict) -> str:
    """
    Render the top market ticker bar.
    
    Args:
        data: {
            'SPY': {'price': 540.23, 'change_pct': +0.08},
            'VIX': {'price': 18.50, 'change_pct': -6.09},
        }
    
    Returns: HTML string
    """
    items = []
    for ticker, d in data.items():
        pct = d.get('change_pct', 0)
        color = COLORS['positive'] if pct >= 0 else COLORS['negative']
        arrow = '▲' if pct >= 0 else '▼'
        items.append(
            f'<div class="gx-status-item">'
            f'<span class="gx-status-ticker">{ticker}</span>'
            f'<span class="gx-num" style="color:{COLORS["text_primary"]}">{d["price"]:,.2f}</span>'
            f'<span class="gx-num" style="color:{color};font-size:11px">{arrow} {abs(pct):.2f}%</span>'
            f'</div>'
        )
    return f'<div class="gx-status-bar">{"".join(items)}</div>'


def metric_card(label: str, value: str, delta: str = "", 
                delta_color: str = "", border_color: str = "",
                sparkline_svg: str = "") -> str:
    """Render a KPI metric card."""
    bc = border_color or COLORS['border_default']
    dc = delta_color or COLORS['text_tertiary']
    spark = f'<span class="gx-sparkline">{sparkline_svg}</span>' if sparkline_svg else ''
    delta_html = f'<div class="gx-metric-delta" style="color:{dc}">{delta}</div>' if delta else ''
    return (
        f'<div class="gx-metric" style="border-left-color:{bc}">'
        f'<div class="gx-metric-label">{label}</div>'
        f'<div class="gx-metric-value">{value}{spark}</div>'
        f'{delta_html}</div>'
    )


def data_table(columns: list[dict], rows: list[dict], max_height: int = 400) -> str:
    """Render a Bloomberg-style data table."""
    header = '<tr>' + ''.join(
        f'<th style="text-align:{c.get("align","left")}">{c["label"]}</th>'
        for c in columns
    ) + '</tr>'
    
    row_html = []
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col['key'], '')
            align = col.get('align', 'left')
            ctype = col.get('type', 'text')
            
            if ctype == 'number':
                cell = f'<td style="text-align:{align};font-family:{FONTS["mono"]}">{val:,.2f}</td>'
            elif ctype == 'delta':
                color = COLORS['positive'] if val >= 0 else COLORS['negative']
                arrow = '▲' if val >= 0 else '▼'
                cell = f'<td style="text-align:{align};color:{color}">{arrow} {abs(val):.2f}%</td>'
            else:
                cell = f'<td style="text-align:{align}">{val}</td>'
            cells.append(cell)
        row_html.append(f'<tr>{"".join(cells)}</tr>')
    
    return (
        f'<div style="max-height:{max_height}px;overflow-y:auto">'
        f'<table class="gx-table"><thead>{header}</thead><tbody>{"".join(row_html)}</tbody></table></div>'
    )


def sparkline_svg(values: list[float], width: int = 60, height: int = 18,
                   color: str | None = None) -> str:
    """Generate inline SVG sparkline."""
    if not values or len(values) < 2:
        return ''
    
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    n = len(values)
    
    auto_color = color or (COLORS['positive'] if values[-1] >= values[0] else COLORS['negative'])
    
    points = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - mn) / rng) * (height - 2) - 1
        points.append(f'{x:.1f},{y:.1f}')
    
    polyline = ' '.join(points)
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="display:inline-block;vertical-align:middle">'
        f'<polyline points="{polyline}" fill="none" stroke="{auto_color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def alert_banner(level: str, score: int, message: str) -> str:
    """Full-width alert banner."""
    color_map = {
        'green': (COLORS['alert_green'], 'rgba(34,197,94,0.06)'),
        'yellow': (COLORS['alert_yellow'], 'rgba(251,191,36,0.06)'),
        'orange': (COLORS['alert_orange'], 'rgba(249,115,22,0.06)'),
        'red': (COLORS['alert_red'], 'rgba(239,68,68,0.08)'),
        'black': (COLORS['alert_black'], 'rgba(220,38,38,0.12)'),
    }
    fg, bg = color_map.get(level, color_map['green'])
    
    return (
        f'<div style="display:flex;align-items:center;gap:16px;padding:10px 16px;'
        f'background:{bg};border:1px solid {fg}33;border-radius:4px;margin-bottom:16px">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{fg};'
        f'box-shadow:0 0 8px {fg}88;flex-shrink:0"></div>'
        f'<div style="flex:1"><span style="font-weight:700;color:{fg};font-size:13px;'
        f'text-transform:uppercase;letter-spacing:0.06em">{level}</span>'
        f'<span style="color:{COLORS["text_secondary"]};font-size:13px;margin-left:12px">{message}</span></div>'
        f'<span class="gx-num" style="color:{fg};font-size:18px;font-weight:700">{score}</span></div>'
    )


def section_header(title: str, subtitle: str = "") -> str:
    """Section header with optional subtitle."""
    sub = f'<span style="color:{COLORS["text_tertiary"]};font-size:12px;margin-left:12px">{subtitle}</span>' if subtitle else ''
    return (
        f'<div style="display:flex;align-items:baseline;margin-bottom:12px;padding-bottom:8px;'
        f'border-bottom:1px solid {COLORS["border_default"]}">'
        f'<span style="font-size:15px;font-weight:700;color:{COLORS["text_primary"]}">{title}</span>{sub}</div>'
    )


# ============================================================
# PLOTLY TEMPLATE (Bloomberg dark)
# ============================================================

GENESIX_PLOTLY = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONTS['body'], color=COLORS['text_secondary'], size=12),
        title=dict(font=dict(size=14, color=COLORS['text_primary']), x=0, y=0.98),
        xaxis=dict(
            gridcolor=COLORS['border_subtle'], gridwidth=0.5, griddash='dot',
            zerolinecolor=COLORS['border_default'], zerolinewidth=0.5,
            tickfont=dict(size=11, color=COLORS['text_tertiary'], family=FONTS['mono']),
            linecolor=COLORS['border_default'], linewidth=0.5,
        ),
        yaxis=dict(
            gridcolor=COLORS['border_subtle'], gridwidth=0.5, griddash='dot',
            zerolinecolor=COLORS['border_default'], zerolinewidth=0.5,
            tickfont=dict(size=11, color=COLORS['text_tertiary'], family=FONTS['mono']),
            linecolor=COLORS['border_default'], linewidth=0.5,
            side='right',
        ),
        colorway=[COLORS[f'chart_{i}'] for i in range(1, 9)],
        margin=dict(l=8, r=50, t=32, b=28),
        legend=dict(
            bgcolor='rgba(0,0,0,0)', borderwidth=0, orientation='h',
            font=dict(size=11, color=COLORS['text_tertiary']),
            yanchor='bottom', y=1.02, xanchor='right', x=1,
        ),
        hoverlabel=dict(
            bgcolor=COLORS['bg_elevated'], bordercolor=COLORS['border_strong'],
            font=dict(size=12, color=COLORS['text_primary'], family=FONTS['mono']),
        ),
        hovermode='x unified',
    )
)

def apply_plotly_theme():
    """Register GenesiX theme globally."""
    pio.templates['genesix'] = GENESIX_PLOTLY
    pio.templates.default = 'genesix'

def styled_chart(fig: go.Figure, height: int = 350) -> go.Figure:
    """Apply GenesiX styling to any Plotly figure."""
    fig.update_layout(height=height, template='genesix')
    fig.update_traces(hovertemplate=None)
    return fig
