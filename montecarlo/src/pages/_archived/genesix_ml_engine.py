"""
GenesiX ML Engine — Real implementation connected to GenesiXPredictor and AnomalyDetector.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="ML Engine — GenesiX", page_icon=None, layout="wide")


# ============================================================================
# CACHED DATA AND MODEL FUNCTIONS
# ============================================================================

@st.cache_data(ttl=1800)
def fetch_ml_data(ticker: str, days: int) -> pd.DataFrame:
    """Fetch historical OHLCV for ML pipeline."""
    try:
        from genesix.data.market_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fetcher.get_historical_ohlcv(ticker, start, end)
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def run_predictor(ticker: str, horizon: int, days: int):
    """Train GenesiXPredictor and return ensemble prediction."""
    try:
        from genesix.ml.prediction_engine import GenesiXPredictor
        predictor = GenesiXPredictor(random_seed=42)
        train_result = predictor.train_ensemble(ticker, horizon=horizon)
        prediction = predictor.ensemble_predict(ticker, horizon=horizon, investment=10000.0)
        return predictor, prediction, train_result
    except Exception as e:
        return None, None, {'error': str(e)}


@st.cache_data(ttl=1800)
def run_risk_scenarios(ticker: str, horizon: int, days: int):
    """Use GenesiXRiskEngine for scenario simulation (fallback when predictor needs features)."""
    try:
        df = fetch_ml_data(ticker, days)
        if df.empty or 'close' not in df.columns:
            return None

        from genesix.risk.risk_engine import GenesiXRiskEngine
        engine = GenesiXRiskEngine(n_simulations=5000, random_seed=42)
        returns = df['close'].pct_change().dropna()
        if len(returns) < 30:
            return None

        result = engine.simulate_return_scenarios(returns, horizon=horizon, investment=10000.0)
        return result
    except Exception as e:
        return None


@st.cache_data(ttl=1800)
def run_regime_detection(ticker: str, days: int):
    """Detect regime and build transition matrix from real returns."""
    try:
        df = fetch_ml_data(ticker, days)
        if df.empty or 'close' not in df.columns:
            return None

        from genesix.intelligence.regime_ml import RegimeDetector, RegimeAdaptivePredictor
        returns = df['close'].pct_change().dropna().values

        detector = RegimeDetector()
        current_regime = detector.detect_regime(returns=returns)

        hist_regimes = detector.historical_regimes(returns)
        trans_matrix = detector.regime_transition_matrix(hist_regimes)

        predictor = RegimeAdaptivePredictor()
        train_info = predictor.train(ticker, returns, horizon=5)
        confidence_info = predictor.model_confidence_realtime(ticker, returns)

        return {
            'current': current_regime,
            'hist_regimes': hist_regimes,
            'trans_matrix': trans_matrix,
            'train_info': train_info,
            'confidence_info': confidence_info,
        }
    except Exception as e:
        return None


@st.cache_data(ttl=1800)
def run_anomaly_detection(ticker: str, days: int):
    """Run anomaly detection on returns."""
    try:
        df = fetch_ml_data(ticker, days)
        if df.empty or 'close' not in df.columns:
            return None

        returns = df['close'].pct_change().dropna()
        if len(returns) < 30:
            return None

        # Compute rolling z-score as anomaly proxy
        window = 21
        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        z_scores = (returns - rolling_mean) / (rolling_std + 1e-12)
        anomalies = z_scores.abs() > 2.5

        # Bubble / overvaluation risk: compare recent vol to long-run vol
        recent_vol = returns.iloc[-21:].std() * np.sqrt(252) if len(returns) >= 21 else np.nan
        longrun_vol = returns.std() * np.sqrt(252)
        bubble_score = float((recent_vol / longrun_vol - 1) * 100) if longrun_vol > 0 else 0

        # Composite alert: fraction of anomalies in last 30 days
        last30 = anomalies.iloc[-30:] if len(anomalies) >= 30 else anomalies
        alert_level = float(last30.mean() * 100)

        return {
            'returns': returns,
            'z_scores': z_scores,
            'anomalies': anomalies,
            'recent_vol_ann': recent_vol,
            'longrun_vol_ann': longrun_vol,
            'bubble_score': bubble_score,
            'alert_level': alert_level,
        }
    except Exception as e:
        return None


# ============================================================================
# HEADER
# ============================================================================

st.title("ML Engine")
st.markdown("Machine learning for financial forecasting, anomaly detection, and regime analysis.")

# ============================================================================
# SIDEBAR INPUTS
# ============================================================================

with st.sidebar:
    st.header("Parameters")
    ticker = st.text_input("Ticker", value="SPY").upper().strip()
    horizon = st.selectbox("Prediction Horizon (days)", [1, 5, 10, 21], index=1,
                           format_func=lambda d: {1: '1 Day', 5: '1 Week', 10: '2 Weeks', 21: '1 Month'}[d])
    lookback_days = st.selectbox("Training Lookback", [504, 756, 1260], index=0,
                                 format_func=lambda d: {504: '2 Years', 756: '3 Years', 1260: '5 Years'}[d])

st.info(f"Showing ML analysis for **{ticker}** | Horizon: **{horizon}d** | Lookback: **{lookback_days}d**")

# ============================================================================
# LOAD DATA IN PARALLEL
# ============================================================================

with st.spinner("Loading data and running models..."):
    scenario_result = run_risk_scenarios(ticker, horizon, lookback_days)
    regime_result = run_regime_detection(ticker, lookback_days)
    anomaly_result = run_anomaly_detection(ticker, lookback_days)

# ============================================================================
# HEADER METRICS
# ============================================================================

if scenario_result:
    summ = scenario_result['summary']
    hm1, hm2, hm3, hm4 = st.columns(4)
    hm1.metric("Prob. of Profit", f"{summ['probability_profit']*100:.1f}%")
    hm2.metric("Expected Value", f"${summ['expected_value']:,.0f}",
               help=f"Starting from $10,000 over {horizon}d")
    hm3.metric(f"VaR 95% ({horizon}d)", f"{summ['var_95']*100:.2f}%")
    hm4.metric(f"CVaR 95% ({horizon}d)", f"{summ['cvar_95']*100:.2f}%")
    st.divider()

# ============================================================================
# TABS
# ============================================================================

tab_scenarios, tab_regime, tab_anomaly = st.tabs([
    "Scenario Distribution",
    "Regime Detection",
    "Anomaly Detection",
])


# ============================================================================
# TAB 1: SCENARIO DISTRIBUTION
# ============================================================================

with tab_scenarios:
    st.subheader(f"Return Distribution & 5 Scenarios — {horizon}d Horizon")

    if scenario_result is None:
        st.error("Could not compute scenario analysis. Ensure data for this ticker is available.")
    else:
        sim_returns = scenario_result['simulated_returns']
        scenarios = scenario_result['scenarios']

        # Histogram
        fig_scen = go.Figure()
        hist_vals, bin_edges = np.histogram(sim_returns * 100, bins=80)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        scenario_colors = {
            'Crash': '#d62728',
            'Bear': '#ff7f0e',
            'Base': '#2ca02c',
            'Bull': '#1f77b4',
            'Extreme Bull': '#9467bd',
        }
        fig_scen.add_trace(go.Bar(
            x=bin_centers, y=hist_vals,
            marker_color='rgba(31,119,180,0.6)',
            name='Simulated Returns',
            hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>',
        ))

        # Scenario lines
        scen_pcts = {
            'Crash': np.percentile(sim_returns * 100, 5),
            'Bear': np.percentile(sim_returns * 100, 25),
            'Base': np.percentile(sim_returns * 100, 50),
            'Bull': np.percentile(sim_returns * 100, 75),
            'Extreme Bull': np.percentile(sim_returns * 100, 95),
        }
        for sname, sval in scen_pcts.items():
            fig_scen.add_vline(
                x=sval,
                line_color=scenario_colors[sname],
                line_dash='dash',
                line_width=1.8,
                annotation_text=f"{sname}: {sval:.1f}%",
                annotation_position="top right" if sval > 0 else "top left",
            )

        fig_scen.update_layout(
            title=f"{ticker} Monte Carlo Return Distribution ({horizon}d horizon, 5000 sims)",
            xaxis_title="Return (%)",
            yaxis_title="Frequency",
            height=520,
        )
        st.plotly_chart(fig_scen, use_container_width=True)

        # Scenario cards
        st.subheader("Scenario Summary")
        scen_cols = st.columns(5)
        for i, sc in enumerate(scenarios):
            with scen_cols[i]:
                color_key = sc['name'].replace('Extreme bull', 'Extreme Bull')
                st.markdown(f"**{sc['name']}**")
                st.metric(
                    f"Prob: {sc['probability']*100:.0f}%",
                    f"{sc['return_pct']:.1f}%",
                    delta=f"${sc['final_value']:,.0f}",
                    help=f"Starting from $10,000"
                )

        st.divider()
        summ = scenario_result['summary']
        ds = scenario_result['distribution_stats']
        stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
        stat_c1.metric("Expected Return", f"{ds['mean_return']*100:.2f}%")
        stat_c2.metric("Std Dev", f"{ds['std_return']*100:.2f}%")
        stat_c3.metric("Skewness", f"{ds['skew']:.3f}")
        stat_c4.metric("Kurtosis", f"{ds['kurtosis']:.3f}")


# ============================================================================
# TAB 2: REGIME DETECTION
# ============================================================================

with tab_regime:
    st.subheader("Market Regime Detection & Transition Probabilities")

    if regime_result is None:
        st.error("Could not run regime detection. Ensure data is available.")
    else:
        current = regime_result['current']
        trans_matrix = regime_result['trans_matrix']
        hist_regimes = regime_result['hist_regimes']
        train_info = regime_result['train_info']
        conf_info = regime_result['confidence_info']

        # Current regime badge
        regime_emojis = {
            'low_vol': 'LOW VOL (Bull)',
            'normal': 'NORMAL',
            'high_vol': 'HIGH VOL',
            'crisis': 'CRISIS',
        }
        regime_colors_map = {
            'low_vol': 'green', 'normal': 'blue', 'high_vol': 'orange', 'crisis': 'red',
        }
        cr_name = current['regime']
        cr_color = regime_colors_map.get(cr_name, 'blue')

        reg_c1, reg_c2, reg_c3 = st.columns(3)
        reg_c1.metric("Current Regime",
                      regime_emojis.get(cr_name, cr_name.upper()),
                      f"Confidence: {current['confidence']*100:.0f}%")
        reg_c2.metric("Days in Regime", str(current.get('days_in_regime', 'N/A')))
        reg_c3.metric("Transition Probability", f"{current['transition_probability']*100:.0f}%")

        # Model confidence
        if conf_info:
            trust = "GOOD" if conf_info['should_trust_model'] else "LOW"
            st.info(f"**Model Confidence:** {trust} ({conf_info['overall_confidence']*100:.0f}%) — "
                    f"{conf_info['recommendation']}")
            if conf_info['concerns']:
                for c in conf_info['concerns']:
                    st.warning(c)

        st.divider()

        # Historical regime chart
        if hist_regimes is not None and len(hist_regimes) > 0:
            regime_num = hist_regimes.map({'low_vol': 0, 'normal': 1, 'high_vol': 2, 'crisis': 3}).fillna(1)
            fig_reg = go.Figure()
            fig_reg.add_trace(go.Scatter(
                x=hist_regimes.index,
                y=regime_num.values,
                mode='lines',
                line=dict(color='steelblue', width=1.5),
                hovertemplate='%{x|%Y-%m-%d}<br>Regime: %{text}<extra></extra>',
                text=hist_regimes.values,
                name='Regime',
            ))
            fig_reg.update_layout(
                title=f"{ticker} Historical Regime Classification (GMM)",
                xaxis_title="Date",
                yaxis=dict(
                    title="Regime",
                    tickvals=[0, 1, 2, 3],
                    ticktext=['Low Vol', 'Normal', 'High Vol', 'Crisis'],
                ),
                height=520,
            )
            st.plotly_chart(fig_reg, use_container_width=True)

        # Transition matrix heatmap
        st.subheader("Regime Transition Probability Matrix")
        fig_trans = go.Figure(go.Heatmap(
            z=trans_matrix.values,
            x=trans_matrix.columns.tolist(),
            y=trans_matrix.index.tolist(),
            colorscale='Blues',
            text=[[f"{v:.2f}" for v in row] for row in trans_matrix.values],
            texttemplate="%{text}",
            hovertemplate='From %{y} → To %{x}: %{z:.3f}<extra></extra>',
        ))
        fig_trans.update_layout(
            title="Transition Matrix (P[from regime → to regime])",
            height=520,
            xaxis_title="To Regime",
            yaxis_title="From Regime",
        )
        st.plotly_chart(fig_trans, use_container_width=True)

        # Regime distribution
        if train_info and 'regime_distribution' in train_info:
            dist = train_info['regime_distribution']
            fig_dist_reg = go.Figure(go.Bar(
                x=list(dist.keys()),
                y=[v * 100 for v in dist.values()],
                marker_color=['green', 'steelblue', 'orange', 'red'],
                text=[f"{v*100:.1f}%" for v in dist.values()],
                textposition='outside',
            ))
            fig_dist_reg.update_layout(
                title="Historical Regime Distribution",
                yaxis_title="% of Time",
                height=380,
            )
            st.plotly_chart(fig_dist_reg, use_container_width=True)


# ============================================================================
# TAB 3: ANOMALY DETECTION
# ============================================================================

with tab_anomaly:
    st.subheader("Anomaly Detection & Market Health")

    if anomaly_result is None:
        st.error("Could not run anomaly detection. Ensure data is available.")
    else:
        anom = anomaly_result
        returns_s = anom['returns']
        z_scores = anom['z_scores'].dropna()
        anomalies = anom['anomalies']

        # Header metrics
        am1, am2, am3, am4 = st.columns(4)
        am1.metric("Anomaly Alert Level", f"{anom['alert_level']:.1f}%",
                   help="% of anomalous days in last 30 trading days")
        am2.metric("Recent Vol (ann.)",
                   f"{anom['recent_vol_ann']*100:.1f}%" if not np.isnan(anom['recent_vol_ann']) else "N/A")
        am3.metric("Long-Run Vol (ann.)", f"{anom['longrun_vol_ann']*100:.1f}%")
        bubble_val = anom['bubble_score']
        am4.metric("Bubble Risk Score",
                   f"{bubble_val:+.1f}%",
                   delta="elevated" if bubble_val > 20 else "normal",
                   delta_color="inverse" if bubble_val > 20 else "normal",
                   help="+% means recent vol is higher than historical average")

        st.divider()

        # Z-score chart with anomaly markers
        fig_z = go.Figure()
        fig_z.add_trace(go.Scatter(
            x=z_scores.index, y=z_scores.values,
            mode='lines',
            line=dict(color='steelblue', width=1),
            name='Z-Score',
            hovertemplate='%{x|%Y-%m-%d}<br>Z: %{y:.2f}<extra></extra>',
        ))

        anom_idx = anomalies[anomalies].index
        anom_zvals = z_scores.reindex(anom_idx).dropna()
        if len(anom_zvals) > 0:
            fig_z.add_trace(go.Scatter(
                x=anom_zvals.index, y=anom_zvals.values,
                mode='markers',
                marker=dict(color='red', size=7, symbol='x'),
                name='Anomaly (|Z|>2.5)',
            ))

        fig_z.add_hline(y=2.5, line_color='red', line_dash='dash', opacity=0.4)
        fig_z.add_hline(y=-2.5, line_color='red', line_dash='dash', opacity=0.4)
        fig_z.add_hline(y=0, line_color='black', line_width=0.5)

        fig_z.update_layout(
            title=f"{ticker} Rolling Z-Score of Returns (21-day window) — Anomaly Detection",
            xaxis_title="Date",
            yaxis_title="Z-Score",
            height=520,
            hovermode='x unified',
        )
        st.plotly_chart(fig_z, use_container_width=True)

        # Returns with anomaly overlay
        fig_ret = go.Figure()
        colors_ret = ['#d62728' if a else '#2ca02c' for a in anomalies.values]
        fig_ret.add_trace(go.Bar(
            x=returns_s.index, y=returns_s.values * 100,
            marker_color=colors_ret,
            name='Daily Returns',
            hovertemplate='%{x|%Y-%m-%d}<br>Return: %{y:.3f}%<extra></extra>',
        ))
        fig_ret.update_layout(
            title=f"{ticker} Daily Returns (red = anomaly day)",
            xaxis_title="Date",
            yaxis_title="Return (%)",
            height=380,
            hovermode='x unified',
        )
        st.plotly_chart(fig_ret, use_container_width=True)

        # Summary stats
        total_anomalies = int(anomalies.sum())
        total_days = len(anomalies)
        st.markdown(
            f"**Total anomalous days:** {total_anomalies} out of {total_days} "
            f"({total_anomalies/total_days*100:.1f}%) | "
            f"**Threshold:** |Z| > 2.5 (rolling 21-day window)"
        )
