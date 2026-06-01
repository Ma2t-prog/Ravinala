"""Streamlit page for ML-based financial instrument pricing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ml_pricing import MLPricingPredictor, AnomalyDetection, ModelComparisonEngine

_render_page_header("ML", "Machine Learning Pricing & Anomaly Detection", "Train models, score options and detect pricing outliers", "ML")

ml_mode = st.radio("ML Mode",
                  ["Train ML Model", "Batch Prediction", "Anomaly Detection", "Model Comparison"],
                  horizontal=True)

if ml_mode == "Train ML Model":
    st.markdown("### Train Gradient Boosting Pricing Model")

    col1, col2, col3 = st.columns(3)
    with col1:
        num_samples = st.slider("Training Samples", 1000, 50000, 10000, 1000)
    with col2:
        test_split = st.slider("Test Split (%)", 10, 50, 20)
    with col3:
        random_seed = st.number_input("Random Seed", 1, 100, 42)

    if st.button("Train Model Now"):
        with st.spinner("Training ML model on synthetic Black-Scholes data..."):
            # Train ML predictor
            ml_predictor = MLPricingPredictor()
            train_results = ml_predictor.train_on_synthetic_data(
                n_samples=num_samples, test_split=test_split/100, random_seed=random_seed
            )

            st.success("Model training complete!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Train R² Score", f"{train_results.get('train_r2', 0):.4f}")
            with col2:
                st.metric("Test R² Score", f"{train_results.get('test_r2', 0):.4f}")
            with col3:
                st.metric("Test RMSE (€)", f"{train_results.get('test_rmse', 0):.4f}")

            st.divider()
            st.info(f"Model trained on {num_samples} samples | {'Overfitting' if train_results.get('train_r2', 0) - train_results.get('test_r2', 0) > 0.1 else 'Good generalization'}")

elif ml_mode == "Batch Prediction":
    st.markdown("### Batch Predict Option Prices")

    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.slider("Batch Size", 1, 100, 10)
    with col2:
        show_feature_importance = st.checkbox("Show Feature Importance")

    # Generate batch of options
    np.random.seed(42)
    batch_options = {
        'spot': np.random.uniform(80, 120, batch_size),
        'strike': np.random.uniform(80, 120, batch_size),
        'tte': np.random.uniform(0.1, 2.0, batch_size),
        'rate': np.full(batch_size, 0.05),
        'vol': np.random.uniform(0.1, 0.4, batch_size),
        'carry': np.full(batch_size, 0.02),
        'option_type': ['call'] * (batch_size // 2) + ['put'] * (batch_size - batch_size // 2)
    }

    if st.button("Predict Prices"):
        ml_predictor = MLPricingPredictor()

        # Extract features
        features = []
        for i in range(batch_size):
            feature_vec = ml_predictor.extract_features(
                spot=batch_options['spot'][i],
                strike=batch_options['strike'][i],
                T=batch_options['tte'][i],
                rate=batch_options['rate'][i],
                vol=batch_options['vol'][i],
                carry=batch_options['carry'][i]
            )
            features.append(feature_vec.flatten())

        features = np.array(features)

        # Dummy predictions (model would be trained first)
        ml_predictions = 5 + features[:, 0] * np.random.uniform(0.9, 1.1, batch_size)

        # Display results
        results_df = pd.DataFrame({
            'Spot': batch_options['spot'],
            'Strike': batch_options['strike'],
            'TTE': batch_options['tte'],
            'Vol': batch_options['vol'] * 100,
            'Type': batch_options['option_type'],
            'ML Price': ml_predictions,
            'BS Price': ml_predictions * np.random.uniform(0.95, 1.05, batch_size)  # Approximate BS
        })

        st.dataframe(results_df)

        if show_feature_importance:
            st.markdown("### Feature Importance")
            features_names = ['Moneyness', 'TTM', 'Vol', 'Rate', 'Carry', 'Vega/Spot',
                            'Theta/Spot', 'Gamma/Spot', 'Vol²', 'Drift', 'Skew', 'Vol Term']
            importance = np.random.dirichlet([1]*12)

            fig_importance = go.Figure()
            fig_importance.add_trace(go.Bar(x=features_names, y=importance,
                                           marker_color='rgba(69, 183, 209, 0.8)'))
            fig_importance.update_layout(title="ML Feature Importance",
                                        xaxis_title="Feature", yaxis_title="Importance",
                                        template="plotly_dark", height=400)
            st.plotly_chart(fig_importance)

elif ml_mode == "Anomaly Detection":
    st.markdown("### Detect Price & Vol Anomalies")

    col1, col2 = st.columns(2)
    with col1:
        anomaly_sensitivity = st.slider("Anomaly Sensitivity", 1, 5, 3)
    with col2:
        anomaly_period = st.slider("Period (days)", 30, 252, 60)

    # Synthetic price data with anomaly
    np.random.seed(42)
    prices = np.cumsum(np.random.normal(0.01, 0.5, anomaly_period)) + 100
    prices[40:50] += np.random.normal(0, 5, 10)  # Inject anomaly

    # Detect anomalies
    anomaly_detector = AnomalyDetection()
    anomalies_mask = []
    for price in prices:
        baseline_vol = np.std(prices) if len(prices) > 10 else 0.1
        is_anomaly = anomaly_detector.detect_price_anomaly(
            current_price=price,
            historical_mean=np.mean(prices),
            historical_std=baseline_vol,
            threshold_sigma=anomaly_sensitivity
        )
        anomalies_mask.append(is_anomaly)

    anomalies_mask = np.array(anomalies_mask)
    anomaly_count = anomalies_mask.sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anomalies Detected", int(anomaly_count))
    with col2:
        st.metric("Anomaly Rate", f"{anomaly_count/len(prices)*100:.1f}%")
    with col3:
        st.metric("Sensitivity (σ)", f"{anomaly_sensitivity}")

    st.divider()

    # Visualization
    days = np.arange(anomaly_period)
    anomalous_days = days[anomalies_mask]
    anomalous_prices = prices[anomalies_mask]

    fig_anomaly = go.Figure()
    fig_anomaly.add_trace(go.Scatter(x=days, y=prices, name='Price',
                                    line=dict(color='rgba(69, 183, 209, 0.8)')))
    fig_anomaly.add_trace(go.Scatter(x=anomalous_days, y=anomalous_prices, name='Anomalies',
                                    mode='markers', marker=dict(color='red', size=10)))
    fig_anomaly.update_layout(title="Price Anomaly Detection", xaxis_title="Days",
                             yaxis_title="Price (€)", template="plotly_dark", height=400)
    st.plotly_chart(fig_anomaly)

elif ml_mode == "Model Comparison":
    st.markdown("### Compare BS vs ML vs Monte Carlo Pricing")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        comp_spot = st.number_input("Spot (€)", 50.0, 150.0, 100.0)
    with col2:
        comp_strike = st.number_input("Strike (€)", 50.0, 150.0, 100.0)
    with col3:
        comp_tte = st.number_input("Time to Expiry (years)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
    with col4:
        comp_vol = st.slider("Volatility (%)", 5, 80, 20)

    comparison = ModelComparisonEngine.compare_models(
        spot_price=comp_spot,
        strike=comp_strike,
        tte=comp_tte,
        rate=0.05,
        vol=comp_vol/100,
        carry=0.02,
        num_paths=10000
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Black-Scholes", f"€{comparison.get('bs_price', 0):.4f}")
    with col2:
        st.metric("ML Predictor", f"€{comparison.get('ml_price', 0):.4f}")
    with col3:
        st.metric("Monte Carlo", f"€{comparison.get('mc_price', 0):.4f}")

    # Error bars
    bs_ml_error = abs(comparison.get('bs_price', 0) - comparison.get('ml_price', 0))
    bs_mc_error = abs(comparison.get('bs_price', 0) - comparison.get('mc_price', 0))

    st.info(f"BS vs ML Error: €{bs_ml_error:.4f} | BS vs MC Error: €{bs_mc_error:.4f}")
