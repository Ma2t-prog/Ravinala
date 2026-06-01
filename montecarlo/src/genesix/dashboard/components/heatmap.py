"""Heatmap visualization components."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ..theme import GENESIX_COLORS, style_figure

def plot_correlation_matrix(correlation_matrix: pd.DataFrame | np.ndarray, 
                             title: str = "Correlation Matrix", height: int = 500):
    """
    Plot correlation heatmap with diverging colorscale.
    
    Args:
        correlation_matrix: pandas DataFrame or numpy array with correlations
        title: chart title
        height: chart height
    """
    if isinstance(correlation_matrix, np.ndarray):
        correlation_matrix = pd.DataFrame(correlation_matrix)
    
    # Ensure square matrix
    if correlation_matrix.shape[0] == correlation_matrix.shape[1]:
        labels = correlation_matrix.index.tolist() if hasattr(correlation_matrix, 'index') else \
                 [f'Asset {i}' for i in range(len(correlation_matrix))]
    else:
        labels = [f'Asset {i}' for i in range(correlation_matrix.shape[0])]
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=labels,
        y=labels,
        colorscale=[
            [0.0, GENESIX_COLORS['red']],      # -1.0 (strong negative)
            [0.25, '#ff6b6b'],                  # -0.5
            [0.5, '#444444'],                   # 0.0 (neutral)
            [0.75, '#6bff6b'],                  # +0.5
            [1.0, GENESIX_COLORS['green']]     # +1.0 (strong positive)
        ],
        colorbar=dict(title='Correlation', tickformat='.2f'),
        hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.3f}<extra></extra>',
        zmin=-1,
        zmax=1
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Assets',
        yaxis_title='Assets',
        height=height,
        xaxis={'side': 'bottom'},
        yaxis={'autorange': 'reversed'}
    )
    
    return style_figure(fig, height=height)


def plot_performance_heatmap(returns_matrix: pd.DataFrame | np.ndarray,
                              title: str = "Asset Performance Heatmap", height: int = 400):
    """
    Plot daily/weekly returns heatmap across assets.
    
    Args:
        returns_matrix: DataFrame with assets as columns, time periods as rows
        title: chart title
        height: chart height
    """
    if isinstance(returns_matrix, np.ndarray):
        returns_matrix = pd.DataFrame(returns_matrix)
    
    # Clip extreme values for better visualization
    z_values = np.clip(returns_matrix.values * 100, -5, 5)  # ±5% display range
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=returns_matrix.columns if hasattr(returns_matrix, 'columns') else \
          [f'Asset {i}' for i in range(returns_matrix.shape[1])],
        y=returns_matrix.index if hasattr(returns_matrix, 'index') else \
          [f'Day {i}' for i in range(returns_matrix.shape[0])],
        colorscale=[
            [0.0, GENESIX_COLORS['red']],
            [0.5, '#444444'],
            [1.0, GENESIX_COLORS['green']]
        ],
        colorbar=dict(title='Return (%)', tickformat='.1f'),
        hovertemplate='%{y}<br>%{x}<br>Return: %{z:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Assets',
        yaxis_title='Time Period',
        height=height
    )
    
    return style_figure(fig, height=height)


def plot_macro_sensitivity_heatmap(sensitivity_matrix: pd.DataFrame | np.ndarray,
                                    title: str = "Macro Sensitivity", height: int = 450):
    """
    Plot sensitivity of assets to macro factors (Equity, Rates, Inflation, FX, Commodities, Vol).
    
    Args:
        sensitivity_matrix: DataFrame with assets as rows, macro factors as columns
        title: chart title
        height: chart height
    """
    if isinstance(sensitivity_matrix, np.ndarray):
        sensitivity_matrix = pd.DataFrame(sensitivity_matrix)
    
    factors = ['Equity', 'Rates', 'Inflation', 'FX', 'Commodities', 'Vol']
    
    fig = go.Figure(data=go.Heatmap(
        z=sensitivity_matrix.values,
        x=factors[:sensitivity_matrix.shape[1]],
        y=sensitivity_matrix.index if hasattr(sensitivity_matrix, 'index') else \
          [f'Asset {i}' for i in range(sensitivity_matrix.shape[0])],
        colorscale=[
            [0.0, GENESIX_COLORS['red']],      # Hedge
            [0.5, '#444444'],                   # Neutral
            [1.0, GENESIX_COLORS['green']]     # Amplify
        ],
        colorbar=dict(title='Sensitivity (β)', tickformat='.2f'),
        hovertemplate='%{y}<br>%{x}<br>Beta: %{z:.2f}<extra></extra>',
        zmid=0,
        zmin=-1,
        zmax=2
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Macro Factors',
        yaxis_title='Assets',
        height=height
    )
    
    return style_figure(fig, height=height)


def plot_regime_heatmap(regime_scores: dict, title: str = "Risk Regime Matrix", height: int = 350):
    """
    Plot market regime heatmap (Volatility, Trend, Liquidity, Correlation).
    
    Args:
        regime_scores: dict with regime names as keys and scores (0-100) as values
        title: chart title
        height: chart height
    """
    regimes = list(regime_scores.keys())
    scores = list(regime_scores.values())
    
    # Normalize to 0-1 for colorscale
    normalized = [s / 100 for s in scores]
    
    # Color based on score
    colors = [
        GENESIX_COLORS['green'] if score < 25 else
        GENESIX_COLORS['yellow'] if score < 50 else
        GENESIX_COLORS['orange'] if score < 75 else
        GENESIX_COLORS['red']
        for score in scores
    ]
    
    fig = go.Figure(data=go.Bar(
        x=regimes,
        y=scores,
        marker=dict(color=colors),
        text=[f'{s:.0f}' for s in scores],
        textposition='outside',
        hovertemplate='%{x}<br>Score: %{y:.0f}/100<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='Regime Score (0-100)',
        height=height,
        showlegend=False,
        xaxis_tickangle=0
    )
    
    return style_figure(fig, height=height)


def plot_volatility_term_structure(tenor_labels: list, volatilities: list,
                                     title: str = "Volatility Term Structure", height: int = 350):
    """
    Plot volatility curve across tenors (1M, 3M, 6M, 1Y, 2Y, 5Y).
    
    Args:
        tenor_labels: list of tenors (e.g., ['1M', '3M', '6M', '1Y', '2Y', '5Y'])
        volatilities: list of volatilities (as percentages)
        title: chart title
        height: chart height
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=tenor_labels,
        y=volatilities,
        mode='lines+markers',
        name='Volatility',
        line=dict(color=GENESIX_COLORS['blue'], width=3),
        marker=dict(size=10, color=GENESIX_COLORS['cyan']),
        fill='tozeroy',
        fillcolor='rgba(68, 138, 255, 0.15)',
        hovertemplate='%{x}<br>Vol: %{y:.1f}%<extra></extra>'
    ))
    
    # Add average line
    mean_vol = np.mean(volatilities)
    fig.add_hline(y=mean_vol, line_dash='dash', line_color=GENESIX_COLORS['yellow'],
                  annotation_text=f'Mean = {mean_vol:.1f}%')
    
    fig.update_layout(
        title=title,
        xaxis_title='Tenor',
        yaxis_title='Volatility (%)',
        height=height,
        hovermode='x unified'
    )
    
    return style_figure(fig, height=height)


def plot_asset_class_heatmap(asset_classes: dict, title: str = "Asset Class Returns YTD", height: int = 350):
    """
    Plot year-to-date returns grid for asset classes.
    
    Args:
        asset_classes: dict with asset class names and returns (as decimals)
        title: chart title
        height: chart height
    """
    names = list(asset_classes.keys())
    returns = [v * 100 for v in asset_classes.values()]
    colors = [
        GENESIX_COLORS['green'] if r > 0 else GENESIX_COLORS['red']
        for r in returns
    ]
    
    fig = go.Figure(data=go.Bar(
        x=names,
        y=returns,
        marker=dict(color=colors),
        text=[f'{r:+.1f}%' for r in returns],
        textposition='outside',
        hovertemplate='%{x}<br>YTD Return: %{y:+.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='YTD Return (%)',
        height=height,
        showlegend=False
    )
    
    return style_figure(fig, height=height)
