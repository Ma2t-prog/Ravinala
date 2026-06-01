"""
GenesiX Portfolio Allocation UI — v2.1
UI helper module for portfolio construction with dynamic universe selection
Streamlit components for universe selector, constraint builder, optimizer runner
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple

from genesix.universe_explorer import get_pipeline
from genesix.portfolio_config_engine import (
    PortfolioOptimizer,
    PortfolioConstraints,
    AllocationResult,
    get_optimization_models
)

# ============================================================================
# UNIVERSE SELECTOR COMPONENT
# ============================================================================

def render_universe_selector() -> Tuple[List, str]:
    """
    Render UI for selecting instruments (manual, screener, or preset).
    
    Returns:
        (instruments_list, selection_method): Selected instruments and how they were selected
    """
    st.markdown("### Define Your Investment Universe")
    st.markdown("Choose your approach to building the portfolio instrument universe:")
    
    selection_method = st.radio(
        "Universe Selection Method",
        options=[
            "Manual Selection (Search & Pick)",
            "Pre-Built Screen (Use Screener)",
            "Risk Matrix Universe (Classic)",
        ],
        horizontal=True,
        help="Select how to define your investment universe"
    )
    
    pipeline = get_pipeline()
    pipeline.ensure_universe_loaded()
    all_instruments = pipeline.get_all()
    
    if selection_method == "Manual Selection (Search & Pick)":
        st.markdown("**Search & select individual instruments:**")
        
        # Search for instruments
        search_query = st.text_input(
            "Search instruments",
            placeholder="e.g., AAPL, Technology, US",
            key="universe_search"
        )
        
        found_instruments = []
        if search_query:
            found_instruments = pipeline.search_instruments(search_query, limit=50)
            st.info(f"Found {len(found_instruments)} instruments")
        
        # Multi-select from found results
        if found_instruments:
            selected_tickers = st.multiselect(
                "Select instruments to include",
                options=[f"{inst.ticker} ({inst.name})" for inst in found_instruments],
                key="universe_manual_select",
                help="Select instruments to include in portfolio universe"
            )
            
            # Filter to selected
            selected_inst = [
                inst for inst in found_instruments
                if f"{inst.ticker} ({inst.name})" in selected_tickers
            ]
            
            if selected_inst:
                st.success(f"Selected {len(selected_inst)} instruments")
                return selected_inst, "manual"
            else:
                st.warning("Select at least 2 instruments")
                return [], "manual"
        else:
            st.info("Enter a search query above")
            return [], "manual"
    
    elif selection_method == "Pre-Built Screen (Use Screener)":
        st.markdown("**Choose a pre-built screener or load saved criteria:**")
        
        screen_type = st.selectbox(
            "Select Screen",
            [
                "High Dividend Yield",
                "Growth Stocks",
                "Value Opportunity",
                "Large-Cap Blue Chips",
                "Momentum Plays",
                "Low Volatility",
                "ESG Leaders",
                "Custom Criteria",
            ],
            key="universe_screener_sel"
        )
        
        from genesix.universe_explorer import ScreenerEngine
        screener = ScreenerEngine(all_instruments)
        
        # Apply pre-built screen
        if screen_type == "High Dividend Yield":
            result = screener.screen_high_dividend(min_yield=0.02)
        elif screen_type == "Growth Stocks":
            result = screener.screen_growth()
        elif screen_type == "Value Opportunity":
            result = screener.screen_value()
        elif screen_type == "Large-Cap Blue Chips":
            result = screener.screen_large_cap()
        elif screen_type == "Momentum Plays":
            result = screener.screen_momentum()
        elif screen_type == "Low Volatility":
            result = screener.screen_low_volatility()
        elif screen_type == "ESG Leaders":
            result = screener.screen_esg_leaders()
        else:
            result = None
        
        if result:
            st.success(f"✓ Screen returned {result.total_count} instruments")
            
            # Show top matches
            with st.expander("View Screen Results", expanded=True):
                df_results = pd.DataFrame([
                    {
                        "Ticker": inst.ticker,
                        "Name": inst.name[:30],
                        "Sector": inst.sector or "-",
                        "Price": f"${inst.price:.2f}",
                        "P/E": f"{inst.pe_ratio:.1f}" if inst.pe_ratio else "-",
                        "Div Yield": f"{inst.dividend_yield * 100:.2f}%" if inst.dividend_yield else "-",
                    }
                    for inst in result.instruments[:20]
                ])
                st.dataframe(df_results, use_container_width=True, hide_index=True)
            
            return result.instruments, "screener"
        else:
            st.error("Screen execution failed")
            return [], "screener"
    
    else:  # Risk Matrix Universe
        st.markdown("**Using institutional risk matrix universe (classic):**")
        st.info("Portfolio will be allocated across major asset classes per risk matrix")
        
        # Return top 30 instruments from major sectors
        from genesix.universe_explorer import ScreenerEngine
        screener = ScreenerEngine(all_instruments)
        
        # Select mix of sectors
        sectors = st.multiselect(
            "Include sectors",
            options=["Technology", "Financials", "Healthcare", "Energy", "Consumer", "Industrials"],
            default=["Technology", "Financials", "Healthcare"],
            key="universe_sectors"
        )
        
        selected_insts = []
        for sector in sectors:
            sector_insts = pipeline.get_by_sector(sector)
            selected_insts.extend(sector_insts[:5])  # 5 per sector
        
        if selected_insts:
            st.success(f"✓ Selected {len(selected_insts)} instruments from {len(sectors)} sectors")
            return selected_insts[:30], "risk_matrix"  # Limit to 30
        else:
            st.warning("No instruments found for selected sectors")
            return [], "risk_matrix"


# ============================================================================
# CONSTRAINT BUILDER COMPONENT
# ============================================================================

def render_constraint_builder() -> PortfolioConstraints:
    """Render UI for portfolio constraints configuration."""
    st.markdown("### Portfolio Constraints")
    
    with st.expander("Constraint Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Position Limits**")
            min_pos = st.slider(
                "Min weight per instrument",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.5,
                help="Minimum % for any single position",
                format="%.1f%%"
            )
            max_pos = st.slider(
                "Max weight per instrument",
                min_value=5.0,
                max_value=50.0,
                value=15.0,
                step=1.0,
                help="Maximum % for any single position",
                format="%.1f%%"
            )
        
        with col2:
            st.markdown("**Sector Limits**")
            min_sector = st.slider(
                "Min sector allocation",
                min_value=0.0,
                max_value=10.0,
                value=2.0,
                step=0.5,
                help="Minimum % total allocation per sector",
                format="%.1f%%"
            )
            max_sector = st.slider(
                "Max sector allocation",
                min_value=10.0,
                max_value=100.0,
                value=40.0,
                step=5.0,
                help="Maximum % total allocation per sector",
                format="%.1f%%"
            )
    
    return PortfolioConstraints(
        min_sector_allocation=min_sector / 100,
        max_sector_allocation=max_sector / 100,
        min_weight_per_instrument=min_pos / 100,
        max_weight_per_instrument=max_pos / 100,
    )


# ============================================================================
# OPTIMIZATION RUNNER COMPONENT
# ============================================================================

def render_optimization_selector() -> Tuple[str, Dict]:
    """Render UI for selecting optimization model and parameters."""
    st.markdown("### Optimization Model")
    
    models = get_optimization_models()
    
    model_choice = st.radio(
        "Select optimization model",
        options=list(models.keys()),
        format_func=lambda k: f"{models[k].name} — {models[k].description}",
        horizontal=True,
        help="Different optimization approaches for portfolio construction"
    )
    
    params = {}
    
    if model_choice == "mvo":
        col1, col2 = st.columns(2)
        with col1:
            params['target_return'] = st.slider(
                "Target Annual Return %",
                min_value=0.0,
                max_value=20.0,
                value=8.0,
                step=0.5,
                help="Portfolio must achieve this return or higher"
            )
        with col2:
            params['max_volatility'] = st.slider(
                "Max Volatility % (optional)",
                min_value=0.0,
                max_value=50.0,
                value=25.0,
                step=1.0,
                help="Optional: constrain portfolio volatility",
                format="%.1f%%"
            )
    
    elif model_choice == "inverse_vol":
        st.info("Inverse Volatility — Automatically weights instruments by their risk")
    
    else:  # equal_weight
        st.info("Equal Weight — Simple 1/N diversification across all instruments")
    
    return model_choice, params


# ============================================================================
# RESULTS DISPLAY COMPONENT
# ============================================================================

def render_allocation_results(
    result: AllocationResult,
    investment_amount: float,
    currency: str
) -> None:
    """Render portfolio optimization results."""
    
    st.markdown("### Portfolio Allocation Results")
    st.markdown(f"**Model Used:** {result.model_used}")
    st.caption(f"Optimization executed in {result.execution_time_ms:.1f}ms")
    
    if result.warnings:
        for warning in result.warnings:
            st.warning(f"{warning}")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Expected Return", f"{result.expected_return:.2f}%")
    with col2:
        st.metric("Expected Volatility", f"{result.expected_volatility:.2f}%")
    with col3:
        st.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
    with col4:
        st.metric("Instruments", len(result.weights))
    
    st.divider()
    
    # Allocation table
    st.markdown("### Position Sizing")
    
    allocation_data = []
    for ticker, weight in sorted(result.weights.items(), key=lambda x: x[1], reverse=True):
        amount = investment_amount * weight
        allocation_data.append({
            "Ticker": ticker,
            "Weight %": f"{weight * 100:.2f}%",
            f"Amount ({currency})": f"{amount:,.0f}",
        })
    
    df_allocation = pd.DataFrame(allocation_data)
    st.dataframe(
        df_allocation,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Weight %": st.column_config.TextColumn(),
            f"Amount ({currency})": st.column_config.TextColumn(),
        }
    )
    
    # Pie chart
    st.markdown("### Allocation Breakdown")
    
    labels = list(result.weights.keys())
    values = [w * 100 for w in result.weights.values()]
    
    import plotly.graph_objects as go
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        textposition='auto',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>%{value:.2f}%<extra></extra>'
    )])
    
    fig.update_layout(
        height=500,
        template="plotly_dark",
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# MAIN PORTFOLIO BUILDER WORKFLOW
# ============================================================================

def run_portfolio_builder_workflow():
    """Complete workflow: Select universe → Configure constraints → Run optimizer → Show results."""
    
    st.markdown("## Advanced Portfolio Builder")
    st.markdown("Build optimized portfolios from any universe of instruments")
    
    # Step 1: Universe Selection
    st.markdown("**Step 1 of 4: Select Investment Universe**")
    selected_instruments, method = render_universe_selector()
    
    if not selected_instruments:
        st.warning("Select at least 2 instruments to proceed")
        st.stop()
    
    st.success(f"Universe selected: {len(selected_instruments)} instruments ({method})")
    
    # Step 2: Constraints
    st.markdown("---")
    st.markdown("**Step 2 of 4: Define Constraints**")
    constraints = render_constraint_builder()
    st.success("Constraints configured")
    
    # Step 3: Optimization
    st.markdown("---")
    st.markdown("**Step 3 of 4: Choose Optimization Model**")
    model_choice, model_params = render_optimization_selector()
    st.success(f"Model selected: {model_choice}")
    
    # Step 4: Run optimizer
    st.markdown("---")
    st.markdown("**Step 4 of 4: Build Portfolio**")
    
    col_amt, col_cur = st.columns([2, 1])
    with col_amt:
        investment_amount = st.number_input(
            "Investment Amount",
            min_value=1000,
            max_value=10_000_000,
            value=100_000,
            step=10_000
        )
    with col_cur:
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CHF"], index=0)
    
    if st.button("Build & Optimize Portfolio", use_container_width=True, type="primary"):
        with st.spinner("Running optimization..."):
            try:
                optimizer = PortfolioOptimizer(selected_instruments)
                
                if model_choice == "mvo":
                    result = optimizer.optimize_mvo(
                        target_return=model_params.get('target_return', 8.0),
                        max_volatility=model_params.get('max_volatility'),
                        constraints_cfg=constraints
                    )
                elif model_choice == "inverse_vol":
                    result = optimizer.optimize_inverse_volatility(constraints_cfg=constraints)
                else:  # equal_weight
                    result = optimizer.optimize_equal_weight(constraints_cfg=constraints)
                
                if result:
                    render_allocation_results(result, investment_amount, currency)
                    st.success("Portfolio optimization complete!")
                else:
                    st.error("Optimization failed. Check universe data quality")
            
            except Exception as e:
                st.error(f"Error during optimization: {str(e)}")
                import traceback
                st.write("```\n" + traceback.format_exc() + "\n```")
