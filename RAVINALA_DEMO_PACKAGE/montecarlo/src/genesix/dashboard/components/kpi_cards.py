"""Reusable KPI card components for GenesiX dashboard."""

import streamlit as st
from ..theme import GENESIX_COLORS

def render_kpi_row(kpis: list[dict]):
    """
    Render a row of KPI cards with dark theme styling.
    
    Args:
        kpis: list of dicts with keys:
            - label: str
            - value: float or str
            - format: str (e.g. '.1f', '.2%')
            - prefix: str (e.g. '$', '€')
            - suffix: str (e.g. '%', 'pts')
            - delta: float (optional)
            - delta_suffix: str (optional)
            - delta_inverse: bool (inverse color logic)
            - color: str or None (override)
    """
    cols = st.columns(len(kpis))
    
    for col, kpi in zip(cols, kpis):
        with col:
            label = kpi.get('label', 'Unknown')
            value = kpi.get('value', 0)
            format_str = kpi.get('format', '.1f')
            prefix = kpi.get('prefix', '')
            suffix = kpi.get('suffix', '')
            delta = kpi.get('delta')
            delta_suffix = kpi.get('delta_suffix', '')
            delta_inverse = kpi.get('delta_inverse', False)
            color_override = kpi.get('color')
            
            # Format value
            if isinstance(value, str):
                formatted_value = f"{prefix}{value}{suffix}"
            else:
                try:
                    if format_str == '.2%' or format_str == '.1%' or format_str == '.0%':
                        formatted_value = f"{prefix}{value:{format_str}}{suffix}"
                    else:
                        formatted_value = f"{prefix}{value:{format_str}}{suffix}"
                except:
                    formatted_value = f"{prefix}{value}{suffix}"
            
            # Determine delta color
            delta_color = '#888'
            if delta is not None:
                if delta_inverse:
                    delta_color = GENESIX_COLORS['green'] if delta < 0 else GENESIX_COLORS['red']
                else:
                    delta_color = GENESIX_COLORS['green'] if delta > 0 else GENESIX_COLORS['red']
            
            # Override color
            if color_override == 'green':
                border_color = GENESIX_COLORS['green']
            elif color_override == 'red':
                border_color = GENESIX_COLORS['red']
            elif color_override == 'yellow':
                border_color = GENESIX_COLORS['yellow']
            else:
                border_color = GENESIX_COLORS['blue']
            
            # Format delta
            delta_str = ''
            if delta is not None:
                delta_str = f"<div style='color: {delta_color}; font-size: 13px;'>{delta:+.2f}{delta_suffix}</div>"
            
            st.markdown(f"""
            <div style="background: {GENESIX_COLORS['bg_card']}; border-radius: 8px; padding: 12px 16px; 
                        border-left: 3px solid {border_color}; margin-bottom: 8px;">
                <div style="color: {GENESIX_COLORS['muted']}; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">{label}</div>
                <div style="color: #fff; font-size: 24px; font-weight: 600; margin-bottom: 4px;">{formatted_value}</div>
                {delta_str}
            </div>
            """, unsafe_allow_html=True)


def render_scenario_cards(scenarios: list[dict], investment: float = 100.0):
    """
    Render 5 scenario cards (Crash, Bear, Base, Bull, Extreme Bull).
    
    Args:
        scenarios: list of dicts with:
            - name: str
            - probability: float (0-1)
            - return_pct: float (percentage)
            - final_value: float (in €)
    """
    scenario_colors = {
        'Crash': GENESIX_COLORS['red'],
        'Bear': '#ff5252',
        'Base': GENESIX_COLORS['blue'],
        'Bull': GENESIX_COLORS['green'],
        'Extreme bull': GENESIX_COLORS['green'],
    }
    
    cols = st.columns(5)
    for col, scenario in zip(cols, scenarios):
        with col:
            name = scenario.get('name', 'Unknown')
            prob = scenario.get('probability', 0)
            ret_pct = scenario.get('return_pct', 0)
            final_val = scenario.get('final_value', 0)
            
            color = scenario_colors.get(name, GENESIX_COLORS['blue'])
            ret_color = GENESIX_COLORS['green'] if ret_pct > 0 else GENESIX_COLORS['red']
            
            st.markdown(f"""
            <div style="background: {GENESIX_COLORS['bg_card']}; border-radius: 8px; padding: 12px; border-top: 3px solid {color}; margin-bottom: 8px;">
                <div style="color: {color}; font-size: 13px; font-weight: 600; margin-bottom: 8px;">{name.upper()}</div>
                <div style="text-align: center; margin-bottom: 8px;">
                    <div style="color: {GENESIX_COLORS['muted']}; font-size: 11px; margin-bottom: 4px;">Probability</div>
                    <div style="background: {GENESIX_COLORS['border']}; border-radius: 4px; padding: 4px; color: #fff; font-size: 14px; font-weight: 600;">{prob:.0%}</div>
                </div>
                <div style="font-size: 18px; font-weight: 600; color: {ret_color}; margin-bottom: 4px; text-align: center;">{ret_pct:+.2f}%</div>
                <div style="color: {GENESIX_COLORS['muted']}; font-size: 11px; text-align: center;">⇒ {final_val:.2f}€</div>
            </div>
            """, unsafe_allow_html=True)


def render_alert_badge(level: str, score: int):
    """Render alert level badge."""
    level_colors = {
        'green': '#00c853',
        'yellow': '#ffd600',
        'orange': '#ff9100',
        'red': '#ff1744',
        'black': '#b71c1c',
    }
    
    level_labels = {
        'green': 'GREEN — Calm',
        'yellow': 'YELLOW — Caution',
        'orange': 'ORANGE — Elevated',
        'red': 'RED — High risk',
        'black': 'BLACK — Extreme',
    }
    
    color = level_colors.get(level, '#448aff')
    label = level_labels.get(level, 'UNKNOWN')
    
    st.markdown(f"""
    <div style="background: {color}20; border: 2px solid {color}; border-radius: 8px; padding: 16px; text-align: center;">
        <div style="color: {color}; font-size: 14px; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">{label}</div>
        <div style="color: {color}; font-size: 32px; font-weight: 700;">{score}</div>
        <div style="color: {GENESIX_COLORS['muted']}; font-size: 12px;">out of 100</div>
    </div>
    """, unsafe_allow_html=True)
