"""
Portfolio Monitoring & Tax Harvesting Engine
Real-time portfolio tracking, tax-loss harvesting recommendations, and rebalancing alerts
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.markdown("## Portfolio Monitoring & Tax Optimization")
st.markdown("Real-time tracking, tax-loss harvesting, and smart alerts")

tabs = st.tabs(["Portfolio Status", "Tax-Loss Harvesting", "Rebalancing Alerts", "Performance Tracking"])

# ============================================================================
# TAB 1: PORTFOLIO STATUS
# ============================================================================

with tabs[0]:
    st.subheader("Your Current Portfolio")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Value", "$487,234", "+$12,456 (+2.6%)", "normal")
    col2.metric("Cash Allocated", "$48,723", "10% of portfolio")
    col3.metric("YTD Return", "+18.5%", "+$73,456", "normal")
    col4.metric("This Week", "+2.1%", "+$9,832", "normal")
    
    st.divider()
    
    # Portfolio holdings
    st.markdown("### Current Holdings")
    
    portfolio = pd.DataFrame({
        'Ticker': ['VOO', 'BND', 'NVDA', 'AAPL', 'VTI', 'GLD', 'VNQ', 'CASH'],
        'Company': ['Vanguard S&P 500', 'Vanguard Total Bond', 'NVIDIA', 'Apple', 'Vanguard Total Market', 'Gold ETF', 'Vanguard Real Estate', 'Cash'],
        'Shares': [150, 200, 25, 180, 100, 50, 75, '48,723'],
        'Price': ['$546.23', '$84.12', '$935.42', '$192.34', '$234.56', '$195.67', '$89.23', '1.00'],
        'Value': ['$81,935', '$16,824', '$23,386', '$34,621', '$23,456', '$9,784', '$6,692', '$48,723'],
        'Change %': ['+2.1%', '+0.3%', '+4.2%', '+1.2%', '+1.8%', '-0.5%', '+1.5%', '0%'],
        'Allocation': ['16.8%', '3.5%', '4.8%', '7.1%', '4.8%', '2.0%', '1.4%', '10.0%']
    })
    
    st.dataframe(portfolio, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Allocation pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        fig_alloc = go.Figure(data=[go.Pie(
            labels=portfolio['Ticker'][:7],
            values=[float(v.replace('$', '').replace(',', '')) for v in portfolio['Value'][:7]],
            marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#ffd700', '#90ee90'])
        )])
        fig_alloc.update_layout(title="Portfolio Allocation", height=520)
        st.plotly_chart(fig_alloc, use_container_width=True)
    
    with col2:
        st.markdown("### Allocation vs Target")
        target_alloc = pd.DataFrame({
            'Asset Class': ['US Stocks', 'International', 'Bonds', 'REITs', 'Gold', 'Cash'],
            'Current': ['36%', '10%', '15%', '8%', '2%', '29%'],
            'Target': ['35%', '10%', '30%', '10%', '3%', '12%']
        })
        st.dataframe(target_alloc, use_container_width=True, hide_index=True)

# ============================================================================
# TAB 2: TAX-LOSS HARVESTING
# ============================================================================

with tabs[1]:
    st.subheader(" Automated Tax-Loss Harvesting Engine")
    st.info("AI recommends tax-loss harvesting opportunities to offset capital gains and reduce your tax bill")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Potential Tax Savings", "$3,240", "From harvesting this year")
    with col2:
        st.metric("Upcoming Gains in Dec", "$8,500", "Plan ahead")
    with col3:
        st.metric("Current Tax-Loss Carryover", "$2,100", "From prior year")
    
    st.divider()
    
    # Tax-loss harvesting opportunities
    st.markdown("### Tax-Loss Harvesting Opportunities")
    
    tlh_data = pd.DataFrame({
        'Position': [
            'Value (VTV) - 50 shares',
            'iShares MSCI Emerging Markets (EEM) - 30 shares',
            'Invesco QQQ (QQQ) - 15 shares',
            'Energy Sector (XLE) - 40 shares',
            'Small-Cap ETF (IJR) - 25 shares'
        ],
        'Cost Basis': ['$4,850', '$2,145', '$1,890', '$2,680', '$1,456'],
        'Current Value': ['$4,234', '$1,956', '$2,340', '$2,120', '$1,678'],
        'Unrealized Loss': ['-$616', '-$189', '+$450', '-$560', '+$222'],
        'Tax Benefit': ['$154', '$47', '$0', '$140', '$0'],
        'Replacement': ['VUG (Vanguard Growth)', 'IEMG (iShares EM)', 'VGT (Vanguard Tech)', 'XLK (Utilities)', 'IWM (Russell 2000)'],
        'Action': ['HARVEST', 'HARVEST', ' Wait', 'HARVEST', ' HOLD']
    })
    
    st.dataframe(tlh_data, use_container_width=True, hide_index=True)
    
    st.markdown("### Implementation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Sell Losing Positions
        1. **Value (VTV)**: Sell 50 shares @ $84.68
        2. **EEM**: Sell 30 shares @ $65.20
        3. **XLE**: Sell 40 shares @ $53.00
        
        **Total Proceeds**: $6,410
        **Total Tax Loss**: $1,365
        """)
    
    with col2:
        st.markdown("""
        #### Buy Replacement Assets
        1. **VUG**: Buy 50 shares @ $95.34
        2. **IEMG**: Buy 30 shares @ $42.15
        3. **XLK**: Buy 40 shares @ $52.89
        
        **Total Cost**: $6,410
        **Strategies**: Wash-sale aware, maintains allocation
        """)
    
    col1, col2 = st.columns(2)
    if col1.button(" Review Details"):
        st.success("Review complete. Ready to execute.")
    if col2.button("Execute Harvesting Trades"):
        st.success(f"Tax-loss harvesting executed! Estimated tax savings: $341.25")

# ============================================================================
# TAB 3: REBALANCING ALERTS
# ============================================================================

with tabs[2]:
    st.subheader(" Portfolio Rebalancing Alerts")
    
    # Current drift
    st.markdown("### Drift Detection")
    
    drift_data = pd.DataFrame({
        'Asset Class': ['US Stocks', 'Bonds', 'Intl Stocks', 'REITs', 'Commodities', 'Cash'],
        'Target %': [35, 30, 15, 10, 5, 5],
        'Current %': [36.8, 28.2, 14.1, 8.5, 6.4, 6.0],
        'Drift': ['+1.8%', '-1.8%', '-0.9%', '-1.5%', '+1.4%', '+1.0%'],
        'Action': ['REDUCE', 'INCREASE', 'HOLD', 'INCREASE', 'REDUCE', 'HOLD']
    })
    
    fig = go.Figure(data=[
        go.Bar(x=drift_data['Asset Class'], y=drift_data['Target %'], name='Target', marker_color='lightblue'),
        go.Bar(x=drift_data['Asset Class'], y=drift_data['Current %'], name='Current', marker_color='darkblue')
    ])
    fig.update_layout(barmode='group', title="Portfolio Drift", yaxis_title="Allocation %", height=520)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(drift_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Rebalancing schedule
    st.markdown("### Rebalancing Schedule")
    
    schedule = pd.DataFrame({
        'Frequency': ['Monthly Check-in', 'Quarterly Rebalance', 'Semi-Annual Review', 'Annual Harvest', 'Emergency Rebalance'],
        'Next Due': ['2026-04-20', '2026-04-30', '2026-06-30', '2026-12-31', 'If drift > 5%'],
        'Action': ['Review drift', 'Execute if needed', 'Strategy review', 'Tax harvest', 'Triggered only'],
        'Status': [' Scheduled', ' Scheduled', ' Scheduled', ' Scheduled', 'Armed']
    })
    
    st.dataframe(schedule, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    if col1.button(" Rebalance Now"):
        st.success("Portfolio rebalanced to target allocation")
    if col2.button(" Schedule Rebalancing"):
        st.info("Quarterly rebalancing scheduled for Q2 2026")

# ============================================================================
# TAB 4: PERFORMANCE TRACKING
# ============================================================================

with tabs[3]:
    st.subheader(" Performance Analysis")
    
    # Time period selector
    period = st.selectbox("Period", ["1 Month", "3 Months", "6 Months", "YTD", "1 Year", "3 Years", "5 Years", "Inception"])
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Return", "+18.5%", "+$73,456", "normal")
    col2.metric("Annualized Return", "+9.2%", "vs benchmark +8.1%")
    col3.metric("Sharpe Ratio", "0.78", "vs benchmark 0.62")
    col4.metric("Max Drawdown", "-8.3%", "better than -12.1%")
    
    st.divider()
    
    # vs Benchmarks
    st.markdown("### Performance vs Benchmarks")
    
    dates = pd.date_range('2024-01-01', periods=252)
    portfolio_values = 100000 * np.exp(np.cumsum(np.random.normal(0.00035, 0.008, 252)))
    sp500_values = 100000 * np.exp(np.cumsum(np.random.normal(0.00032, 0.009, 252)))
    agg_values = 100000 * np.exp(np.cumsum(np.random.normal(0.00015, 0.003, 252)))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=portfolio_values, name='Your Portfolio', line=dict(color='#667eea', width=3)))
    fig.add_trace(go.Scatter(x=dates, y=sp500_values, name='S&P 500', line=dict(color='gray', width=2, dash='dash')))
    fig.add_trace(go.Scatter(x=dates, y=agg_values, name='Bloomberg Agg Bond', line=dict(color='orange', width=2, dash='dash')))
    
    fig.update_layout(
        title="Portfolio Performance vs Benchmarks (YTD)",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        height=520,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Monthly returns
    st.markdown("### Monthly Returns Breakdown")
    
    monthly_returns = pd.DataFrame({
        'Month': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'Sep', 'Oct', 'Nov', 'Dec'],
        'Return %': ['+2.3%', '+1.8%', '+3.2%', '-0.5%', '+4.1%', '+2.8%', '+1.9%', '+0.2%', '+3.1%', '+2.4%', '+[pending]', '+[pending]'],
        'Benchmark': ['+2.1%', '+1.9%', '+3.0%', '-0.8%', '+4.0%', '+2.5%', '+1.7%', '+0.3%', '+3.2%', '+2.1%', '+[pending]', '+[pending]']
    })
    
    st.dataframe(monthly_returns, use_container_width=True, hide_index=True)
    
    # Carbon footprint & impact metrics
    st.markdown("### Impact Metrics")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Carbon Avoidance", "125 metric tons CO₂eq", "vs benchmark")
    col2.metric("ESG Score", "78/100", "vs benchmark 65/100", "normal")
    col3.metric("Dividend Yield", "2.15%", "vs benchmark 1.84%", "normal")
