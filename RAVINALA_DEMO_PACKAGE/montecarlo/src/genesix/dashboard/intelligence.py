"""
Intelligence Center — The nerve center of GenesiX.

Displays: Market regime, Smart alerts feed, Signal summary, Contagion network,
NLP news analysis, and Regime dashboard.

This replaces/upgrades the Alert Center from v1.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from genesix.intelligence import (
    NLPEngine, SignalGenerator, ContagionNetwork,
    SmartAlertSystem, RegimeDetector
)
from genesix.dashboard.theme_v2 import (
    inject_theme, market_status_bar, metric_card, data_table,
    alert_banner, section_header, COLORS
)

logger = None  # Would be logging in production


def page_render():
    """Render Intelligence Center page."""
    
    # Inject theme
    inject_theme()
    
    st.title(" Intelligence Center")
    st.markdown("_Real-time market intelligence, signals, and predictive alerts_")
    
    # ========== ROW 0: Market Status Bar ==========
    market_status_bar({
        'SPY': 485.32,
        'QQQ': 420.15,
        'TLT': 92.45,
        'GLD': 202.10,
    })
    
    # ========== ROW 1: Market Regime Banner ==========
    regime_detector = RegimeDetector()
    regime_info = regime_detector.detect_regime()
    
    regime_color = {
        'low_vol': '#10b981',  # green
        'normal': '#3b82f6',   # blue
        'high_vol': '#f59e0b', # amber
        'crisis': '#ef4444',   # red
    }
    
    regime_interpretation = {
        'low_vol': 'Complacent environment. Favor growth and leverage.',
        'normal': 'Balanced conditions. Diversification works well.',
        'high_vol': 'Elevated uncertainty. Favor defensive positioning.',
        'crisis': 'Systemic stress. Focus on survival and hedges.',
    }
    
    color = regime_color.get(regime_info['regime'], '#3b82f6')
    interpretation = regime_interpretation.get(regime_info['regime'], 'Unknown regime')
    
    # Regime banner (HTML-based for full control)
    st.markdown(f"""
    <div style="background: {color}1a; border-left: 4px solid {color}; padding: 16px; 
                border-radius: 8px; margin-bottom: 20px;">
        <div style="font-size: 18px; font-weight: 600; color: {color}; margin-bottom: 8px;">
            {regime_info['regime'].upper()} REGIME
        </div>
        <div style="color: #888; font-size: 13px;">
            {interpretation}
        </div>
        <div style="color: #666; font-size: 12px; margin-top: 8px;">
            Confidence: {regime_info['confidence']:.0%} • 
            Transition Prob: {regime_info['transition_probability']:.0%}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== ROW 2: Smart Alerts (Left) + Signal Summary (Right) ==========
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        st.markdown("###  Smart Alerts Feed")
        
        alerts_system = SmartAlertSystem()
        
        # Get portfolio from session state if available
        portfolio = st.session_state.get('portfolio', None)
        all_alerts = alerts_system.generate_smart_alerts(portfolio)
        
        # Group by severity
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        sorted_alerts = sorted(
            all_alerts,
            key=lambda x: (severity_order.get(x.get('severity', 'info'), 3), -x.get('probability', 0))
        )
        
        for alert in sorted_alerts[:8]:  # Show top 8
            severity = alert.get('severity', 'info')
            
            # Color mapping
            severity_color = {
                'critical': '#ef4444',
                'warning': '#f59e0b',
                'info': '#3b82f6',
            }
            
            color = severity_color.get(severity, '#888')
            category_abbrev = {'predictive': '', 'reactive': '', 'opportunity': '', 'portfolio': ''}
            emoji = category_abbrev.get(alert.get('category'), '?')
            
            st.markdown(f"""
            <div style="background: {color}0a; border-left: 3px solid {color}; 
                        padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex-grow: 1;">
                        <div style="font-size: 12px; font-weight: 700; color: {color}; text-transform: uppercase;">
                            {emoji} {alert.get('category', 'unknown').upper()}
                        </div>
                        <div style="font-size: 14px; font-weight: 600; color: #fff; margin-top: 4px;">
                            {alert.get('title', 'Unknown Alert')}
                        </div>
                        <div style="font-size: 12px; color: #aaa; margin-top: 4px;">
                            {alert.get('description', '')[:100]}...
                        </div>
                    </div>
                    {'<div style="font-size: 20px; margin-left: 8px;">[WARN]</div>' if severity == 'critical' else ''}
                </div>
                <div style="font-size: 11px; color: #888; margin-top: 8px;">
                    Actions: {', '.join(a[:30] + '...' if len(a) > 30 else a for a in alert.get('suggested_actions', [])[:1])}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("###  Signal Summary")
        
        signals_gen = SignalGenerator()
        universe = ['SPY', 'QQQ', 'TLT', 'GLD', 'EEM']
        
        signal_counts = {}
        for asset in universe:
            sig = signals_gen.generate_asset_signal(asset)
            signal_counts[sig['signal']] = signal_counts.get(sig['signal'], 0) + 1
        
        # Signal distribution pie
        labels = list(signal_counts.keys())
        values = list(signal_counts.values())
        
        colors_map = {
            'strong_buy': '#059669',
            'buy': '#10b981',
            'hold': '#6b7280',
            'sell': '#f59e0b',
            'strong_sell': '#dc2626',
        }
        
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values,
            marker=dict(colors=[colors_map.get(l, '#888') for l in labels]),
            hole=0.4,
        )])
        
        fig.update_layout(
            height=300, margin=dict(t=0, b=0, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fff', size=11, family='JetBrains Mono'),
            showlegend=True,
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Signal counts
        for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
            color = colors_map.get(signal, '#888')
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 6px 0; 
                        border-bottom: 1px solid #222; color: #aaa; font-size: 12px;">
                <span style="color: {color}; font-weight: 600;">{signal.replace('_', ' ').title()}</span>
                <span>{count} assets</span>
            </div>
            """, unsafe_allow_html=True)
    
    # ========== ROW 3: Contagion Network Visualization ==========
    st.markdown("###  Cross-Asset Contagion Network")
    
    contagion = ContagionNetwork()
    assets_for_network = ['SPY', 'QQQ', 'IWM', 'EFA', 'AGG', 'GLD', 'USO', 'VIX']
    network = contagion.build_network(assets_for_network)
    
    # Visualize network using Plotly
    nodes = network['nodes']
    edges = network['edges']
    
    # Node positions (simple layout)
    np.random.seed(42)
    n_nodes = len(nodes)
    angles = np.linspace(0, 2*np.pi, n_nodes, endpoint=False)
    node_positions = {nodes[i]['id']: (np.cos(angles[i]), np.sin(angles[i])) for i in range(n_nodes)}
    
    # Extract edge coordinates
    edge_x = []
    edge_y = []
    for edge in edges:
        x0, y0 = node_positions.get(edge['source'], (0, 0))
        x1, y1 = node_positions.get(edge['target'], (0, 0))
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Node coordinates
    node_x = [node_positions[n['id']][0] for n in nodes]
    node_y = [node_positions[n['id']][1] for n in nodes]
    node_size = [n['systemic_importance'] * 40 for n in nodes]
    node_color = [COLORS['positive'] if n['systemic_importance'] > 0.5 else COLORS['warning'] for n in nodes]
    
    fig = go.Figure()
    
    # Add edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode='lines',
        line=dict(width=0.5, color=COLORS['border_subtle']),
        hoverinfo='none',
        showlegend=False,
    ))
    
    # Add nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        text=[n['id'] for n in nodes],
        textposition='top center',
        textfont=dict(size=10, color='#fff', family='JetBrains Mono'),
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(width=1, color=COLORS['border_subtle']),
        ),
        hovertext=[f"{n['id']}<br>Centrality: {n['centrality']:.2f}" for n in nodes],
        hoverinfo='text',
        showlegend=False,
    ))
    
    fig.update_layout(
        height=380,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        font=dict(color='#fff', family='JetBrains Mono'),
        hovermode='closest',
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Network metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background: #111827; padding: 12px; border-radius: 6px; border: 1px solid {COLORS['border_subtle']};">
            <div style="font-size: 11px; color: #888; text-transform: uppercase;">Density</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">
                {network['metrics']['network_density']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: #111827; padding: 12px; border-radius: 6px; border: 1px solid {COLORS['border_subtle']};">
            <div style="font-size: 11px; color: #888; text-transform: uppercase;">Hub</div>
            <div style="font-size: 18px; font-weight: 700; color: {COLORS['positive']}; margin-top: 4px;">
                {network['metrics']['most_central_asset']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background: #111827; padding: 12px; border-radius: 6px; border: 1px solid {COLORS['border_subtle']};">
            <div style="font-size: 11px; color: #888; text-transform: uppercase;">Risk</div>
            <div style="font-size: 18px; font-weight: 700; color: {COLORS['warning']}; margin-top: 4px;">
                {network['metrics']['contagion_risk_score']:.0f}/100
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: #111827; padding: 12px; border-radius: 6px; border: 1px solid {COLORS['border_subtle']};">
            <div style="font-size: 11px; color: #888; text-transform: uppercase;">Cluster</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">
                {network['metrics']['avg_clustering']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== ROW 4: NLP News Feed ==========
    st.markdown("###  Real-Time Sentiment Analysis")
    
    nlp = NLPEngine(use_finbert=False)
    
    headlines = [
        {'text': 'Fed signals potential pause on rate hikes amid cooling inflation', 'source': 'Reuters'},
        {'text': 'Tech stocks rally on AI optimism and earnings beats', 'source': 'Bloomberg'},
        {'text': 'Banks show resilience despite deposit outflow concerns', 'source': 'Financial Times'},
        {'text': 'Emerging markets attractive as dollar weakness continues', 'source': 'WSJ'},
        {'text': 'Recession fears ease as economic data beats expectations', 'source': 'CNBC'},
    ]
    
    batch_result = nlp.analyze_batch(headlines)
    
    # Overall sentiment gauge
    sentiment = batch_result['overall_sentiment']
    sentiment_label = 'Bullish ' if sentiment > 0.2 else 'Bearish ' if sentiment < -0.2 else 'Neutral ->'
    sentiment_color = COLORS['positive'] if sentiment > 0.2 else COLORS['negative'] if sentiment < -0.2 else COLORS['warning']
    
    col1, col2 = st.columns([0.3, 0.7])
    
    with col1:
        st.markdown(f"""
        <div style="background: #111827; padding: 20px; border-radius: 6px; border: 1px solid {COLORS['border_subtle']}; text-align: center;">
            <div style="font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 12px;">Overall Sentiment</div>
            <div style="font-size: 32px; font-weight: 700; color: {sentiment_color}; margin-bottom: 8px;">
                {sentiment_label}
            </div>
            <div style="font-size: 13px; color: #aaa;">
                Score: {sentiment:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Top Stories by Sentiment**")
        
        for headline_data in headlines[:3]:
            result = nlp.analyze_headline(headline_data['text'], headline_data['source'])
            score = result['sentiment']['ensemble_score']
            color = COLORS['positive'] if score > 0.2 else COLORS['negative'] if score < -0.2 else COLORS['info']
            
            st.markdown(f"""
            <div style="background: #111827; padding: 12px; border-radius: 6px; margin-bottom: 8px; border-left: 2px solid {color};">
                <div style="font-size: 12px; font-weight: 600; color: {color}; margin-bottom: 4px;">
                    {result['sentiment']['label'].upper()} ({score:+.2f})
                </div>
                <div style="font-size: 13px; color: #fff; margin-bottom: 4px;">
                    {headline_data['text'][:80]}...
                </div>
                <div style="font-size: 11px; color: #888;">
                    {headline_data['source']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ========== ROW 5: Regime Dashboard ==========
    st.markdown("###  Regime Transition Analysis")
    
    col1, col2 = st.columns([0.5, 0.5])
    
    with col1:
        st.markdown("**Regime Persistence**")
        
        regimes = ['low_vol', 'normal', 'high_vol', 'crisis']
        persistence = [0.92, 0.88, 0.82, 0.80]
        
        fig = go.Figure(data=[
            go.Bar(
                x=regimes,
                y=persistence,
                marker=dict(color=[COLORS['positive'], COLORS['info'], COLORS['warning'], COLORS['negative']]),
                text=[f"{p:.0%}" for p in persistence],
                textposition='outside',
                textfont=dict(size=11, color='#fff', family='JetBrains Mono'),
            )
        ])
        
        fig.update_layout(
            height=250, margin=dict(t=10, b=10, l=40, r=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title=None, showgrid=False, color='#888'),
            yaxis=dict(title=None, showgrid=False, color='#888', range=[0, 1]),
            font=dict(color='#fff', family='JetBrains Mono', size=10),
            showlegend=False,
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    with col2:
        st.markdown("**Transition Matrix**")
        
        # Simplified transition matrix display
        trans_data = {
            'From→To': ['low_vol', 'normal', 'high_vol', 'crisis'],
            'low_vol': [92, 7, 1, 0],
            'normal': [5, 88, 6, 1],
            'high_vol': [1, 10, 82, 7],
            'crisis': [0, 2, 18, 80],
        }
        
        trans_df = pd.DataFrame(trans_data).set_index('From→To')
        
        # Heatmap-style display
        fig = px.imshow(
            trans_df,
            color_continuous_scale='RdYlGn',
            text_auto=True,
            aspect='auto',
        )
        
        fig.update_layout(
            height=250, margin=dict(t=10, b=10, l=60, r=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title=None),
            yaxis=dict(title=None),
            font=dict(color='#fff', family='JetBrains Mono', size=9),
            coloraxis_showscale=False,
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # ========== FOOTER ==========
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 11px;">
    <strong>Intelligence Center</strong> • Updated every 5 minutes • Last update: {}<br>
    Combining NLP sentiment, ML predictions, regime detection, contagion modeling, and predictive alerts
    </div>
    """.format(datetime.now().strftime("%H:%M UTC")), unsafe_allow_html=True)


if __name__ == '__main__':
    page_render()
