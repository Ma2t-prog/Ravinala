"""Scenario, stress testing, and SHAP explainability components."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from ..theme import GENESIX_COLORS, style_figure

def plot_stress_test_results(base_case: float, scenarios: dict, title: str = "Stress Test Results", height: int = 400):
    """
    Plot stress test scenario impacts as bar chart.
    
    Args:
        base_case: base case value (float)
        scenarios: dict with scenario names (str) as keys and impact values (float) as values
        title: chart title
        height: chart height
    """
    scenario_names = list(scenarios.keys())
    scenario_impacts = list(scenarios.values())
    scenario_colors = [
        GENESIX_COLORS['red'] if impact < 0 else GENESIX_COLORS['green']
        for impact in scenario_impacts
    ]
    
    fig = go.Figure()
    
    # Add base case line
    fig.add_hline(y=0, line_dash='dash', line_color=GENESIX_COLORS['muted'],
                  annotation_text='Base Case')
    
    # Add bars
    fig.add_trace(go.Bar(
        x=scenario_names,
        y=scenario_impacts,
        marker=dict(color=scenario_colors, line=dict(color='white', width=1)),
        text=[f'{impact:+.2f}€' for impact in scenario_impacts],
        textposition='outside',
        hovertemplate='%{x}<br>Impact: %{y:+.2f}€<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='P&L Impact (€)',
        height=height,
        showlegend=False
    )
    
    return style_figure(fig, height=height)


def plot_impact_chain(event: str, chain: list[dict], title: str = None, height: int = 350):
    """
    Plot Sankey diagram of macro event impact chain.
    
    Args:
        event: event name (e.g., 'Fed Hikes')
        chain: list of impact dicts with 'from', 'to', 'strength'
        title: chart title
        height: chart height
    """
    if title is None:
        title = f"Impact Chain: {event}"
    
    # Extract unique nodes
    nodes = set()
    for link in chain:
        nodes.add(link['from'])
        nodes.add(link['to'])
    nodes = sorted(list(nodes))
    
    # Create node-to-index mapping
    node_dict = {node: i for i, node in enumerate(nodes)}
    
    # Extract Sankey data
    source = [node_dict[link['from']] for link in chain]
    target = [node_dict[link['to']] for link in chain]
    value = [link['strength'] for link in chain]
    
    # Color links by strength
    link_colors = [
        f'rgba(255, 69, 0, {min(str_/100, 0.8)})' if str_ > 0 else f'rgba(76, 175, 80, {min(-str_/100, 0.8)})'
        for str_ in value
    ]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='white', width=1),
            label=nodes,
            color=[GENESIX_COLORS['blue']] * len(nodes)
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=link_colors,
            hovertemplate='%{source.label} → %{target.label}<br>Strength: %{value:.1f}<extra></extra>'
        )
    )])
    
    fig.update_layout(
        title=title,
        height=height
    )
    
    return style_figure(fig, height=height)


def render_stress_sliders(shocks: dict) -> dict:
    """
    Render interactive sliders for stress test parameter inputs.
    
    Args:
        shocks: dict with shock names and default values
    
    Returns:
        dict of updated shock values from user input
    """
    st.subheader(' Adjust Stress Shocks')
    
    results = {}
    cols = st.columns(2)
    
    for i, (shock_name, default_value) in enumerate(shocks.items()):
        col = cols[i % 2]
        with col:
            if shock_name == 'Equity':
                value = col.slider(
                    f'{shock_name} Return (%)',
                    min_value=-30.0,
                    max_value=30.0,
                    value=default_value,
                    step=0.5,
                    key=f'shock_{shock_name}'
                )
            elif shock_name == 'Rates':
                value = col.slider(
                    f'{shock_name} Change (bps)',
                    min_value=-200.0,
                    max_value=200.0,
                    value=default_value,
                    step=5.0,
                    key=f'shock_{shock_name}'
                )
            elif shock_name == 'Vol':
                value = col.slider(
                    f'{shock_name} (VIX Δ)',
                    min_value=-10.0,
                    max_value=30.0,
                    value=default_value,
                    step=0.5,
                    key=f'shock_{shock_name}'
                )
            else:
                value = col.slider(
                    f'{shock_name} (%)',
                    min_value=-20.0,
                    max_value=20.0,
                    value=default_value,
                    step=0.5,
                    key=f'shock_{shock_name}'
                )
            
            results[shock_name] = value
    
    return results


def plot_shap_waterfall(feature_names: list, shap_values: list, base_value: float = 0.0,
                         title: str = "SHAP Feature Contributions", height: int = 400):
    """
    Plot SHAP waterfall showing feature contributions to prediction.
    
    Args:
        feature_names: list of feature names
        shap_values: list of SHAP values (contributions)
        base_value: base prediction value
        title: chart title
        height: chart height
    """
    # Sort by absolute value
    sorted_indices = np.argsort(np.abs(shap_values))[::-1]
    
    sorted_features = [feature_names[i] for i in sorted_indices]
    sorted_values = [shap_values[i] for i in sorted_indices]
    
    # Calculate cumulative values
    cumulative = [base_value]
    for val in sorted_values[:-1]:
        cumulative.append(cumulative[-1] + val)
    
    # Create waterfall
    colors = [
        GENESIX_COLORS['green'] if v > 0 else GENESIX_COLORS['red']
        for v in sorted_values
    ]
    
    fig = go.Figure(go.Waterfall(
        name='SHAP',
        orientation='v',
        x=['Base'] + sorted_features,
        textposition='outside',
        y=[0] + sorted_values,
        base=base_value,
        connector={'line': {'color': GENESIX_COLORS['muted']}},
        increasing=dict(marker=dict(color=GENESIX_COLORS['green'], line=dict(color='white', width=1))),
        decreasing=dict(marker=dict(color=GENESIX_COLORS['red'], line=dict(color='white', width=1))),
        hovertemplate='%{x}<br>Contribution: %{customdata:.3f}<extra></extra>',
        customdata=[base_value] + sorted_values
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='Cumulative Impact on Prediction',
        height=height,
        hovermode='x'
    )
    
    return style_figure(fig, height=height)


def plot_confusion_model_backtest(predictions: np.ndarray, actuals: np.ndarray,
                                   title: str = "Model Backtest: Predictions vs Actuals", height: int = 400):
    """
    Plot scatter of predictions vs actual returns with R² and MAE.
    
    Args:
        predictions: array of model predictions
        actuals: array of actual values
        title: chart title
        height: chart height
    """
    from sklearn.metrics import r2_score, mean_absolute_error
    
    r2 = r2_score(actuals, predictions)
    mae = mean_absolute_error(actuals, predictions)
    
    fig = go.Figure()
    
    # Scatter plot
    fig.add_trace(go.Scatter(
        x=actuals,
        y=predictions,
        mode='markers',
        name='Predictions',
        marker=dict(
            size=6,
            color=GENESIX_COLORS['blue'],
            opacity=0.6,
            line=dict(color='white', width=1)
        ),
        hovertemplate='Actual: %{x:.3f}<br>Predicted: %{y:.3f}<extra></extra>'
    ))
    
    # Perfect prediction line
    min_val, max_val = min(actuals.min(), predictions.min()), max(actuals.max(), predictions.max())
    fig.add_trace(go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode='lines',
        name='Perfect Fit',
        line=dict(color=GENESIX_COLORS['green'], width=2, dash='dash'),
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        title=f'{title}<br><sub>R² = {r2:.3f} | MAE = {mae:.4f}</sub>',
        xaxis_title='Actual Return',
        yaxis_title='Predicted Return',
        height=height,
        hovermode='closest',
        legend=dict(x=0.02, y=0.98)
    )
    
    return style_figure(fig, height=height)


def plot_feature_importance_bars(features: list, importances: list,
                                  title: str = "Feature Importance (Global)", height: int = 350):
    """
    Plot horizontal bar chart of feature importance.
    
    Args:
        features: list of feature names
        importances: list of importance scores
        title: chart title
        height: chart height
    """
    # Sort by importance
    sorted_pairs = sorted(zip(features, importances), key=lambda x: abs(x[1]), reverse=True)
    sorted_features, sorted_importances = zip(*sorted_pairs)
    
    # Color by positive/negative importance
    colors = [
        GENESIX_COLORS['green'] if imp > 0 else GENESIX_COLORS['red']
        for imp in sorted_importances
    ]
    
    fig = go.Figure(go.Bar(
        x=sorted_importances,
        y=sorted_features,
        orientation='h',
        marker=dict(color=colors),
        text=[f'{imp:.3f}' for imp in sorted_importances],
        textposition='outside',
        hovertemplate='%{y}<br>Importance: %{x:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Importance Score',
        height=height,
        showlegend=False,
        margin=dict(l=150)
    )
    
    return style_figure(fig, height=height)


def plot_feature_interaction(feature1: str, feature2: str, interaction_matrix: np.ndarray,
                              title: str = "Feature Interaction Effect", height: int = 400):
    """
    Plot interaction effect between two features as heatmap.
    
    Args:
        feature1: name of feature 1
        feature2: name of feature 2
        interaction_matrix: 2D array of interaction effects
        title: chart title
        height: chart height
    """
    fig = go.Figure(data=go.Heatmap(
        z=interaction_matrix,
        colorscale=[
            [0.0, GENESIX_COLORS['red']],
            [0.5, GENESIX_COLORS['bg_page']],
            [1.0, GENESIX_COLORS['green']]
        ],
        colorbar=dict(title='Interaction', tickformat='.3f'),
        hovertemplate=f'{feature1}: %{{x}}<br>{feature2}: %{{y}}<br>Effect: %{{z:.3f}}<extra></extra>',
        zmid=0
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=feature1,
        yaxis_title=feature2,
        height=height
    )
    
    return style_figure(fig, height=height)
