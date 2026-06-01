"""GenesiX Dashboard Components Library.

Reusable Streamlit + Plotly components for dashboard pages.
"""

from .kpi_cards import (
    render_kpi_row,
    render_scenario_cards,
    render_alert_badge,
)

from .distribution import (
    plot_return_distribution,
    plot_scenario_waterfall,
    plot_investment_cone,
    plot_drawdown_series,
    plot_rolling_volatility,
)

from .heatmap import (
    plot_correlation_matrix,
    plot_performance_heatmap,
    plot_macro_sensitivity_heatmap,
    plot_regime_heatmap,
    plot_volatility_term_structure,
    plot_asset_class_heatmap,
)

from .scenario import (
    plot_stress_test_results,
    plot_impact_chain,
    render_stress_sliders,
    plot_shap_waterfall,
    plot_confusion_model_backtest,
    plot_feature_importance_bars,
    plot_feature_interaction,
)

__all__ = [
    # KPI Cards
    'render_kpi_row',
    'render_scenario_cards',
    'render_alert_badge',
    # Distribution
    'plot_return_distribution',
    'plot_scenario_waterfall',
    'plot_investment_cone',
    'plot_drawdown_series',
    'plot_rolling_volatility',
    # Heatmaps
    'plot_correlation_matrix',
    'plot_performance_heatmap',
    'plot_macro_sensitivity_heatmap',
    'plot_regime_heatmap',
    'plot_volatility_term_structure',
    'plot_asset_class_heatmap',
    # Scenario & SHAP
    'plot_stress_test_results',
    'plot_impact_chain',
    'render_stress_sliders',
    'plot_shap_waterfall',
    'plot_confusion_model_backtest',
    'plot_feature_importance_bars',
    'plot_feature_interaction',
]
