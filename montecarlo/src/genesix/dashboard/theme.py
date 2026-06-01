"""Consistent Plotly theme and styling for GenesiX dashboard."""

import plotly.io as pio
import plotly.graph_objects as go

GENESIX_COLORS = {
    'green': '#69f0ae',
    'red': '#ff5252',
    'blue': '#448aff',
    'yellow': '#ffd600',
    'orange': '#ff9100',
    'purple': '#b388ff',
    'cyan': '#18ffff',
    'white': '#ffffff',
    'muted': '#888888',
    'bg_dark': '#0e1117',
    'bg_card': '#1e1e2e',
    'bg_positive': '#1b2d1b',
    'bg_negative': '#2d1b1b',
    'bg_neutral': '#1b2d3d',
    'grid': '#2a2a3a',
    'border': '#333355',
}

GENESIX_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, system-ui, sans-serif', color='#ffffff', size=13),
        title=dict(font=dict(size=16, color='#ffffff'), x=0, xanchor='left'),
        xaxis=dict(
            gridcolor=GENESIX_COLORS['grid'], gridwidth=0.5,
            zerolinecolor=GENESIX_COLORS['grid'],
            tickfont=dict(size=11, color=GENESIX_COLORS['muted']),
        ),
        yaxis=dict(
            gridcolor=GENESIX_COLORS['grid'], gridwidth=0.5,
            zerolinecolor=GENESIX_COLORS['grid'],
            tickfont=dict(size=11, color=GENESIX_COLORS['muted']),
        ),
        colorway=[
            GENESIX_COLORS['blue'], GENESIX_COLORS['green'], GENESIX_COLORS['red'],
            GENESIX_COLORS['yellow'], GENESIX_COLORS['purple'], GENESIX_COLORS['cyan'],
        ],
        margin=dict(l=40, r=20, t=40, b=30),
        legend=dict(
            bgcolor='rgba(0,0,0,0)', borderwidth=0,
            font=dict(size=12, color=GENESIX_COLORS['muted']),
        ),
        hoverlabel=dict(
            bgcolor=GENESIX_COLORS['bg_card'], bordercolor=GENESIX_COLORS['border'],
            font=dict(size=13, color='#ffffff'),
        ),
    )
)

def apply_theme():
    """Call once at app startup to set global Plotly theme."""
    pio.templates['genesix'] = GENESIX_TEMPLATE
    pio.templates.default = 'genesix'

def style_figure(fig: go.Figure, height: int = 400) -> go.Figure:
    """Apply consistent styling to any figure."""
    fig.update_layout(height=height, template='genesix')
    return fig
