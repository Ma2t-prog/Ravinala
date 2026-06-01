"""Distribution and scenario visualization components."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from ..theme import GENESIX_COLORS, style_figure

def plot_return_distribution(returns: np.ndarray, title: str = "Return Distribution", height: int = 400):
    """
    Plot return distribution with KDE, normal overlay, VaR/CVaR markers.
    
    Args:
        returns: 1D array of returns (as decimals, e.g., -0.02 for -2%)
        title: chart title
        height: chart height in pixels
    """
    returns_pct = returns * 100  # Convert to percentages for display
    
    # Calculate statistics
    mean = np.mean(returns_pct)
    std = np.std(returns_pct)
    var_95 = np.percentile(returns_pct, 5)
    cvar_95 = returns_pct[returns_pct <= var_95].mean()
    
    # Create figure
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=returns_pct,
        nbinsx=50,
        name='Returns',
        marker=dict(color=GENESIX_COLORS['blue'], opacity=0.6),
        showlegend=True
    ))
    
    # KDE
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(returns_pct)
    x_range = np.linspace(returns_pct.min(), returns_pct.max(), 200)
    kde_values = kde(x_range) * len(returns_pct) * (returns_pct.max() - returns_pct.min()) / 50
    fig.add_trace(go.Scatter(
        x=x_range,
        y=kde_values,
        name='KDE',
        line=dict(color=GENESIX_COLORS['cyan'], width=2),
        fill='tozeroy',
        fillcolor='rgba(24, 255, 255, 0.15)',
        showlegend=True
    ))
    
    # Normal overlay
    normal_values = stats.norm.pdf(x_range, mean, std) * len(returns_pct) * (returns_pct.max() - returns_pct.min()) / 50
    fig.add_trace(go.Scatter(
        x=x_range,
        y=normal_values,
        name='Normal (Expected)',
        line=dict(color=GENESIX_COLORS['yellow'], width=2, dash='dash'),
        showlegend=True
    ))
    
    # VaR and CVaR lines
    fig.add_vline(x=var_95, line_dash='dash', line_color=GENESIX_COLORS['orange'],
                  annotation_text=f'VaR 95% = {var_95:.2f}%', annotation_position='top left')
    fig.add_vline(x=cvar_95, line_dash='dot', line_color=GENESIX_COLORS['red'],
                  annotation_text=f'CVaR 95% = {cvar_95:.2f}%', annotation_position='top right')
    
    # Layout
    fig.update_layout(
        title=title,
        xaxis_title='Return (%)',
        yaxis_title='Frequency',
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified',
        height=height
    )
    
    return style_figure(fig, height=height)


def plot_scenario_waterfall(scenarios: list[dict], base_value: float = 100.0, 
                             title: str = "Scenario Outcomes", height: int = 400):
    """
    Plot waterfall chart showing impact of each scenario on initial investment.
    
    Args:
        scenarios: list of dicts with 'name' and 'final_value'
        base_value: initial investment
        title: chart title
        height: chart height
    """
    scenario_names = [s['name'] for s in scenarios]
    scenario_values = [s['final_value'] - base_value for s in scenarios]
    
    fig = go.Figure(go.Waterfall(
        name='P&L',
        orientation='v',
        x=scenario_names,
        textposition='outside',
        y=scenario_values,
        connector={'line': {'color': GENESIX_COLORS['muted']}},
        increasing=dict(marker=dict(color=GENESIX_COLORS['green'], line=dict(color='white', width=1))),
        decreasing=dict(marker=dict(color=GENESIX_COLORS['red'], line=dict(color='white', width=1)))
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='P&L (€)',
        height=height,
        hovermode='x'
    )
    
    return style_figure(fig, height=height)


def plot_investment_cone(scenarios: list[dict], time_periods: list[int] = None,
                         title: str = "Investment Cone (Confidence Intervals)", height: int = 400):
    """
    Plot investment cone showing percentile bands over time.
    
    Args:
        scenarios: list of dicts with 'name', 'probability', 'return_pct', and 'paths' (2D array)
        time_periods: time steps to show (days/weeks/months)
        title: chart title
        height: chart height
    """
    # Synthetic data if not provided
    if time_periods is None:
        time_periods = list(range(1, 254))  # ~252 trading days
    
    # Create cone from percentiles (assume uniform distribution across scenarios for simplicity)
    # In real usage, would compute from actual simulation paths
    
    fig = go.Figure()
    
    # Add percentile bands
    percentiles = [10, 25, 50, 75, 90]
    colors_pct = [
        GENESIX_COLORS['red'],
        GENESIX_COLORS['orange'],
        GENESIX_COLORS['blue'],
        GENESIX_COLORS['cyan'],
        GENESIX_COLORS['green']
    ]
    
    # Synthetic cone (in practice, would bootstrap from actual paths)
    base_return = 0.01  # 1% per period
    
    for i, (pct, color) in enumerate(zip(percentiles, colors_pct)):
        volatility_factor = (pct - 50) / 50  # -1 to +1 scale
        cone_values = [100 * (1 + base_return * np.sqrt(t) * (1 + 0.3 * volatility_factor/100)) ** 1 
                       for t in time_periods]
        
        fig.add_trace(go.Scatter(
            x=time_periods,
            y=cone_values,
            name=f'P{pct}',
            line=dict(color=color, width=1 if pct != 50 else 3),
            hovertemplate='<b>Day %{x}</b><br>Value: €%{y:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Days',
        yaxis_title='Portfolio Value (€)',
        hovermode='x unified',
        legend=dict(x=0.02, y=0.98),
        height=height
    )
    
    return style_figure(fig, height=height)


def plot_drawdown_series(returns: np.ndarray, title: str = "Drawdown Over Time", height: int = 300):
    """Plot running drawdown (underwater plot)."""
    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=drawdown,
        fill='tozeroy',
        name='Drawdown',
        line=dict(color=GENESIX_COLORS['red'], width=1),
        fillcolor='rgba(255, 0, 0, 0.25)',
        hovertemplate='Day %{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Days',
        yaxis_title='Drawdown (%)',
        height=height
    )
    
    return style_figure(fig, height=height)


def plot_rolling_volatility(returns: np.ndarray, window: int = 21, 
                             title: str = "Rolling Volatility (21-day)", height: int = 300):
    """Plot rolling volatility over time."""
    rolling_vol = np.array([
        np.std(returns[max(0, i-window):i]) * 100 * np.sqrt(252)
        for i in range(len(returns))
    ])
    
    mean_vol = np.nanmean(rolling_vol)
    std_vol = np.nanstd(rolling_vol)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=rolling_vol,
        name='21-Day Vol',
        line=dict(color=GENESIX_COLORS['blue'], width=1),
        fill='tozeroy',
        fillcolor='rgba(68, 138, 255, 0.15)',
        hovertemplate='Day %{x}<br>Vol: %{y:.1f}%<extra></extra>'
    ))
    
    # Add mean level
    fig.add_hline(y=mean_vol, line_dash='dash', line_color=GENESIX_COLORS['yellow'],
                  annotation_text=f'Mean = {mean_vol:.1f}%')
    
    # Add ±1σ bands
    fig.add_hline(y=mean_vol + std_vol, line_dash='dot', line_color=GENESIX_COLORS['muted'], opacity=0.5)
    fig.add_hline(y=mean_vol - std_vol, line_dash='dot', line_color=GENESIX_COLORS['muted'], opacity=0.5)
    
    fig.update_layout(
        title=title,
        xaxis_title='Days',
        yaxis_title='Annualized Volatility (%)',
        height=height
    )
    
    return style_figure(fig, height=height)
