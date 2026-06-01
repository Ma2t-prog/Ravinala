"""
GENESIX Design System — Quantum Dark Theme
Professional, institutional-grade UI framework for Streamlit
"""

import streamlit as st

# ============================================================================
# QUANTUM DARK PALETTE
# ============================================================================

QUANTUM_DARK = {
    # Backgrounds
    "bg_0": "#08080C",     # Main background
    "bg_1": "#0E0E14",     # Cards/panels
    "bg_2": "#14141C",     # Elevated surfaces
    "bg_3": "#1A1A24",     # Hover/inputs
    "bg_4": "#22222E",     # Active states
    
    # Text
    "text_0": "#F0F0F5",   # Primary text (headings)
    "text_1": "#B8B8C8",   # Secondary text (body)
    "text_2": "#7878A0",   # Tertiary text (labels)
    "text_3": "#4E4E6A",   # Placeholder/disabled
    
    # Accents (SEMANTIC)
    "accent_positive": "#00E676",   # Green (gains, success)
    "accent_negative": "#FF5252",   # Red (losses, errors)
    "accent_primary": "#448AFF",    # Blue (primary actions, links)
    "accent_warning": "#FFD740",    # Yellow (alerts, attention)
    "accent_info": "#40C4FF",       # Cyan (information, neutral)
    "accent_premium": "#D4AF37",    # Gold (GENESIX branding)
    
    # Borders
    "border_subtle": "rgba(255, 255, 255, 0.06)",
    "border_medium": "rgba(255, 255, 255, 0.10)",
    "border_strong": "rgba(255, 255, 255, 0.16)",
    
    # Surfaces
    "surface_glass": "rgba(255, 255, 255, 0.03)",
    "surface_hover": "rgba(255, 255, 255, 0.05)",
    "surface_active": "rgba(255, 255, 255, 0.08)",
}


def apply_quantum_dark():
    """
    Apply Quantum Dark design system to Streamlit app.
    Call this in your page's st.set_page_config section.
    """
    st.markdown(f"""
    <style>
    /* ================================================================ */
    /* QUANTUM DARK — GENESIX Theme */
    /* ================================================================ */
    
    :root {{
        --bg-0: {QUANTUM_DARK['bg_0']};
        --bg-1: {QUANTUM_DARK['bg_1']};
        --bg-2: {QUANTUM_DARK['bg_2']};
        --bg-3: {QUANTUM_DARK['bg_3']};
        --bg-4: {QUANTUM_DARK['bg_4']};
        
        --text-0: {QUANTUM_DARK['text_0']};
        --text-1: {QUANTUM_DARK['text_1']};
        --text-2: {QUANTUM_DARK['text_2']};
        --text-3: {QUANTUM_DARK['text_3']};
        
        --accent-positive: {QUANTUM_DARK['accent_positive']};
        --accent-negative: {QUANTUM_DARK['accent_negative']};
        --accent-primary: {QUANTUM_DARK['accent_primary']};
        --accent-warning: {QUANTUM_DARK['accent_warning']};
        --accent-info: {QUANTUM_DARK['accent_info']};
        --accent-premium: {QUANTUM_DARK['accent_premium']};
        
        --border-subtle: {QUANTUM_DARK['border_subtle']};
        --border-medium: {QUANTUM_DARK['border_medium']};
        --border-strong: {QUANTUM_DARK['border_strong']};
    }}
    
    /* Main app background */
    [data-testid="stAppViewContainer"] {{
        background: var(--bg-0);
        color: var(--text-1);
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: var(--bg-1);
    }}
    
    /* Main content */
    .main {{
        background: var(--bg-0);
    }}
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--text-0) !important;
        font-weight: 600;
    }}
    
    /* Body text */
    p, span, div {{
        color: var(--text-1);
    }}
    
    /* Labels & captions */
    label, caption {{
        color: var(--text-2) !important;
    }}
    
    /* Inputs */
    input, textarea, [data-testid="textInputRootElement"] {{
        background: var(--bg-3) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-0) !important;
        border-radius: 8px;
    }}
    
    input:focus {{
        border: 1px solid var(--accent-primary) !important;
        box-shadow: 0 0 0 2px rgba(68, 138, 255, 0.15) !important;
    }}
    
    /* ================================================================ */
    /* PREMIUM BUTTON SYSTEM — All button types */
    /* ================================================================ */
    
    /* BUTTON TYPOGRAPHY — Universal rules */
    .stButton > button,
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-secondary"],
    button,
    .btn {{
        font-family: 'DM Sans', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        letter-spacing: 0.02em !important;
        transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        min-height: 44px !important;
        padding: 12px 24px !important;
    }}
    
    /* ── PRIMARY BUTTONS (default Streamlit buttons) ── */
    .stButton > button,
    [data-testid="baseButton-primary"] {{
        /* Gradient argenté/platine subtil */
        background: linear-gradient(
            135deg,
            rgba(192, 192, 200, 0.12) 0%,
            rgba(212, 212, 220, 0.18) 50%,
            rgba(192, 192, 200, 0.12) 100%
        ) !important;
        
        border: 1px solid rgba(192, 192, 210, 0.25) !important;
        color: #F0F0F5 !important;
        font-size: 0.9rem !important;
        box-shadow: 
            0 1px 2px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
    }}
    
    .stButton > button:hover,
    [data-testid="baseButton-primary"]:hover {{
        background: linear-gradient(
            135deg,
            rgba(192, 192, 200, 0.18) 0%,
            rgba(220, 220, 230, 0.25) 50%,
            rgba(192, 192, 200, 0.18) 100%
        ) !important;
        border-color: rgba(192, 192, 210, 0.40) !important;
        color: #FFFFFF !important;
        
        /* Silver glow */
        box-shadow: 
            0 2px 8px rgba(192, 192, 210, 0.15),
            0 1px 2px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        
        transform: translateY(-1px) !important;
    }}
    
    .stButton > button:active,
    [data-testid="baseButton-primary"]:active {{
        transform: translateY(0px) scale(0.98) !important;
        box-shadow: 
            0 1px 2px rgba(0, 0, 0, 0.4),
            inset 0 1px 3px rgba(0, 0, 0, 0.2) !important;
    }}
    
    /* ── PREMIUM/GOLD BUTTONS (for premium products & CTA) ── */
    .btn-premium,
    .stButton > button.premium,
    button.premium {{
        background: linear-gradient(
            135deg,
            rgba(212, 175, 55, 0.08) 0%,
            rgba(212, 175, 55, 0.14) 40%,
            rgba(192, 168, 80, 0.10) 100%
        ) !important;
        
        border: 1px solid rgba(212, 175, 55, 0.25) !important;
        color: #F0ECE0 !important;
        font-size: 0.9rem !important;
        box-shadow: 
            0 1px 2px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(212, 175, 55, 0.08) !important;
    }}
    
    .btn-premium:hover,
    .stButton > button.premium:hover,
    button.premium:hover {{
        background: linear-gradient(
            135deg,
            rgba(212, 175, 55, 0.14) 0%,
            rgba(220, 185, 65, 0.22) 40%,
            rgba(200, 175, 85, 0.16) 100%
        ) !important;
        border-color: rgba(212, 175, 55, 0.45) !important;
        color: #FFFFFF !important;
        
        /* Gold glow */
        box-shadow: 
            0 2px 12px rgba(212, 175, 55, 0.12),
            0 1px 2px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(212, 175, 55, 0.12) !important;
        
        transform: translateY(-1px) !important;
    }}
    
    .btn-premium:active,
    .stButton > button.premium:active,
    button.premium:active {{
        background: linear-gradient(
            135deg,
            rgba(212, 175, 55, 0.18) 0%,
            rgba(212, 175, 55, 0.12) 100%
        ) !important;
        transform: translateY(0px) scale(0.98) !important;
    }}
    
    /* ── SECONDARY BUTTONS (ghost style) ── */
    .btn-secondary,
    [data-testid="baseButton-secondary"] {{
        background: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        color: #B8B8C8 !important;
        font-size: 0.85rem !important;
        padding: 10px 20px !important;
        min-height: 40px !important;
    }}
    
    .btn-secondary:hover,
    [data-testid="baseButton-secondary"]:hover {{
        background: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(255, 255, 255, 0.20) !important;
        color: #E0E0F0 !important;
    }}
    
    .btn-secondary:active,
    [data-testid="baseButton-secondary"]:active {{
        background: rgba(255, 255, 255, 0.06) !important;
        transform: scale(0.98) !important;
    }}
    
    /* ── DANGER BUTTONS (destructive actions) ── */
    .btn-danger,
    button.danger {{
        background: rgba(255, 82, 82, 0.08) !important;
        border: 1px solid rgba(255, 82, 82, 0.25) !important;
        color: #FF8A80 !important;
        font-size: 0.85rem !important;
        padding: 10px 20px !important;
        min-height: 40px !important;
    }}
    
    .btn-danger:hover,
    button.danger:hover {{
        background: rgba(255, 82, 82, 0.14) !important;
        border-color: rgba(255, 82, 82, 0.40) !important;
        color: #FF5252 !important;
        box-shadow: 0 2px 8px rgba(255, 82, 82, 0.10) !important;
    }}
    
    .btn-danger:active,
    button.danger:active {{
        transform: scale(0.98) !important;
    }}
    
    /* ── SUCCESS BUTTONS (positive actions) ── */
    .btn-success,
    button.success {{
        background: rgba(0, 230, 118, 0.08) !important;
        border: 1px solid rgba(0, 230, 118, 0.25) !important;
        color: #69F0AE !important;
        font-size: 0.85rem !important;
        padding: 10px 20px !important;
        min-height: 40px !important;
    }}
    
    .btn-success:hover,
    button.success:hover {{
        background: rgba(0, 230, 118, 0.14) !important;
        border-color: rgba(0, 230, 118, 0.40) !important;
        color: #00E676 !important;
        box-shadow: 0 2px 8px rgba(0, 230, 118, 0.10) !important;
    }}
    
    .btn-success:active,
    button.success:active {{
        transform: scale(0.98) !important;
    }}
    
    /* ── COMPACT BUTTONS (toolbars, filters) ── */
    .btn-compact,
    button.compact {{
        padding: 6px 14px !important;
        min-height: 32px !important;
        font-size: 0.8rem !important;
        border-radius: 6px !important;
    }}
    
    /* ── BUTTON GROUPS ── */
    .btn-group {{
        display: inline-flex;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.10);
    }}
    
    .btn-group-item {{
        padding: 8px 16px;
        font-size: 0.8rem;
        font-weight: 400;
        color: #7878A0;
        background: transparent;
        border: none;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
        cursor: pointer;
        transition: all 150ms ease;
        font-family: 'DM Sans', 'Geist', -apple-system, sans-serif;
        -webkit-font-smoothing: antialiased;
    }}
    
    .btn-group-item:last-child {{
        border-right: none;
    }}
    
    .btn-group-item:hover {{
        background: rgba(255, 255, 255, 0.04);
        color: #B8B8C8;
    }}
    
    .btn-group-item.active {{
        background: rgba(192, 192, 210, 0.12);
        color: #F0F0F5;
        font-weight: 500;
    }}
    
    /* ── PILL BUTTONS ── */
    .btn-pill {{
        padding: 6px 16px !important;
        font-size: 0.8rem !important;
        font-weight: 400 !important;
        color: #7878A0 !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 100px !important;
        cursor: pointer !important;
        transition: all 150ms ease !important;
    }}
    
    .btn-pill:hover {{
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
        color: #B8B8C8 !important;
    }}
    
    .btn-pill.selected {{
        background: rgba(212, 175, 55, 0.10) !important;
        border-color: rgba(212, 175, 55, 0.30) !important;
        color: #F0ECE0 !important;
        font-weight: 500 !important;
    }}
    
    /* Cards & containers */
    [data-testid="element-container"] {{
        background: transparent;
    }}
    
    /* Metrics */
    [data-testid="metric-container"] {{
        background: var(--bg-1);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 20px;
    }}
    
    /* Tables */
    [data-testid="dataFrameContainer"] {{
        background: var(--bg-1);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        overflow: hidden;
    }}
    
    /* Status badges */
    .success {{
        color: var(--accent-positive) !important;
    }}
    
    .error {{
        color: var(--accent-negative) !important;
    }}
    
    .warning {{
        color: var(--accent-warning) !important;
    }}
    
    .info {{
        color: var(--accent-info) !important;
    }}
    
    /* Misc */
    [data-testid="stDivider"] {{
        border-color: var(--border-subtle);
    }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def metric_card(label: str, value: str, change: str = None, color: str = None):
    """
    Render a professional metric card.
    
    Args:
        label: Metric label (e.g., "NAV")
        value: Main value (e.g., "$1,234,567")
        change: Optional change indicator (e.g., "+2.3%")
        color: Optional color ('positive', 'negative', 'warning', None)
    """
    color_class = ""
    if color:
        color_class = f"class='{color}'"
    
    html = f"""
    <div style="
        background: var(--bg-1);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    ">
        <div style="color: var(--text-2); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
            {label}
        </div>
        <div style="color: var(--text-0); font-size: 1.75rem; font-weight: 600; font-family: 'Courier New', monospace;">
            {value}
        </div>
    """
    
    if change:
        change_color = "var(--accent-positive)" if change.startswith("+") else "var(--accent-negative)"
        html += f"""
        <div style="color: {change_color}; font-size: 0.85rem; font-family: 'Courier New', monospace; margin-top: 8px;">
            {change}
        </div>
        """
    
    html += "</div>"
    
    st.markdown(html, unsafe_allow_html=True)
