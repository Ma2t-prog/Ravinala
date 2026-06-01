"""
Volatility Calibration & Modeling — Institutional Quant Suite
SABR · SVI · Dupire · Heston · GARCH · HAR-RV · Vol Surface · VRP
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, chart_h

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import minimize, differential_evolution
from scipy.stats import norm
from scipy.interpolate import RectBivariateSpline
import warnings
warnings.filterwarnings('ignore')

_render_page_header("VC", "Volatility Lab — Institutional Quant Suite",
                    "SABR · SVI · Dupire · Heston · GARCH · HAR-RV · VRP", "Vol")

# ── TABS ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Vol Smile & Skew",
    "SABR Calibration",
    "Vol Surface (3D)",
    "Heston Model",
    "Vol Forecasting",
    "Term Structure",
    "Vol Risk Premium",
])

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def bs_call(S, K, T, r, sigma):
    if sigma <= 0 or T <= 0: return max(S - K * np.exp(-r*T), 0)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)

def bs_put(S, K, T, r, sigma):
    c = bs_call(S, K, T, r, sigma)
    return c - S + K*np.exp(-r*T)

def iv_from_price(price, S, K, T, r, opt='call', tol=1e-6, max_iter=200):
    """Newton-Raphson implied vol inversion."""
    sigma = 0.25
    for _ in range(max_iter):
        if opt == 'call':
            p = bs_call(S, K, T, r, sigma)
        else:
            p = bs_put(S, K, T, r, sigma)
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        vega = S*norm.pdf(d1)*np.sqrt(T)
        if vega < 1e-10: break
        sigma -= (p - price) / vega
        sigma = max(sigma, 1e-4)
        if abs(p - price) < tol: break
    return sigma

def sabr_vol(F, K, T, alpha, beta, rho, nu):
    """Hagan et al. (2002) SABR implied vol."""
    if abs(F - K) < 1e-10:
        fk = F**(beta - 1)
        corr = (
            ((1-beta)**2 * alpha**2) / (24 * F**(2*(1-beta)))
            + rho*beta*nu*alpha / (4 * F**(1-beta))
            + (2 - 3*rho**2)*nu**2/24
        )
        return alpha * fk * (1 + corr * T)
    log_fk = np.log(F/K)
    fk_mid = (F*K)**((1-beta)/2)
    A = 1 + ((1-beta)**2/24)*log_fk**2 + ((1-beta)**4/1920)*log_fk**4
    z = (nu/alpha)*fk_mid*log_fk
    disc = np.sqrt(1 - 2*rho*z + z**2)
    chi = np.log((disc + z - rho)/(1 - rho))
    zx = z/chi if abs(chi) > 1e-10 else 1.0
    corr = (
        ((1-beta)**2 * alpha**2)/(24 * fk_mid**2)
        + rho*beta*nu*alpha/(4*fk_mid)
        + (2 - 3*rho**2)*nu**2/24
    )
    return max((alpha/(fk_mid*A))*zx*(1 + corr*T), 0.001)

def svi_vol(k, a, b, rho_svi, m, sigma_svi):
    """Raw SVI parameterization: total variance w(k) = a + b*(rho*(k-m)+sqrt((k-m)^2+sigma^2))"""
    return np.sqrt(max(a + b*(rho_svi*(k-m) + np.sqrt((k-m)**2 + sigma_svi**2)), 1e-6))

def svi_smile(log_strikes, a, b, rho_svi, m, sigma_svi):
    return np.array([svi_vol(k, a, b, rho_svi, m, sigma_svi) for k in log_strikes])

@st.cache_data(ttl=600)
def fetch_real_data(ticker):
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if hist.empty: return None, None
        returns = hist['Close'].pct_change().dropna().values
        return hist['Close'].values, returns
    except: return None, None

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: VOL SMILE & SKEW
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("### Implied Volatility Smile — Multi-Model Fitting")

    c1, c2, c3, c4 = st.columns(4)
    with c1: spot   = st.number_input("Spot (S)", 50.0, 5000.0, 100.0, step=5.0, key="sm_spot")
    with c2: r_rate = st.number_input("Risk-Free (%)", 0.0, 10.0, 4.5, step=0.1, key="sm_rfr") / 100
    with c3: T_exp  = st.number_input("Maturity (years)", 0.05, 5.0, 0.5, step=0.05, key="sm_T")
    with c4: atm_v  = st.number_input("ATM Vol (%)", 5.0, 100.0, 20.0, step=0.5, key="sm_atm") / 100

    c1, c2, c3 = st.columns(3)
    with c1: skew   = st.slider("Skew (risk-reversal)", -0.3, 0.3, -0.15, 0.01, key="sm_skew")
    with c2: curv   = st.slider("Curvature (butterfly)", 0.0, 0.5, 0.08, 0.01, key="sm_curv")
    with c3: x_axis = st.selectbox("X-axis", ["Strike", "Moneyness K/S", "Log-Strike ln(K/F)", "Delta"], key="sm_xax")

    # Generate market-like smile (SVI-based)
    Ks = np.linspace(spot*0.6, spot*1.4, 61)
    F  = spot * np.exp(r_rate * T_exp)
    log_k = np.log(Ks/F)

    # Market smile: SVI with given parameters
    a_m  = atm_v**2 * T_exp * 0.85
    b_m  = atm_v**2 * T_exp * 0.40
    rho_m = skew * 2
    sigma_m = max(0.1 + curv*0.5, 0.05)
    m_m  = skew * 0.15

    mkt_tv   = a_m + b_m*(rho_m*(log_k-m_m) + np.sqrt((log_k-m_m)**2 + sigma_m**2))
    mkt_vol  = np.sqrt(np.maximum(mkt_tv/T_exp, 0.0001))

    # Add noise to simulate market data
    np.random.seed(7)
    noise = np.random.normal(0, 0.002, len(mkt_vol))
    mkt_vol_noisy = mkt_vol + noise

    # SVI fit
    def svi_obj(params):
        a, b, r, m, s = params
        if b <= 0 or s <= 0: return 1e9
        tv = a + b*(r*(log_k-m) + np.sqrt((log_k-m)**2 + s**2))
        if np.any(tv < 0): return 1e9
        model_vol = np.sqrt(np.maximum(tv/T_exp, 1e-6))
        return np.sum((model_vol - mkt_vol_noisy)**2)

    x0 = [a_m, b_m, rho_m*0.9, m_m, sigma_m]
    bounds = [(-0.5, 1.0), (0.001, 2.0), (-0.999, 0.999), (-2, 2), (0.001, 2.0)]
    res_svi = minimize(svi_obj, x0, method='L-BFGS-B', bounds=bounds)
    a_f, b_f, r_f, m_f, s_f = res_svi.x
    tv_fit  = a_f + b_f*(r_f*(log_k-m_f) + np.sqrt((log_k-m_f)**2 + s_f**2))
    svi_fit = np.sqrt(np.maximum(tv_fit/T_exp, 0.0001))

    # Quadratic fit
    poly2 = np.polyfit(log_k, mkt_vol_noisy, 2)
    quad_vol = np.polyval(poly2, log_k)

    # X-axis values
    if x_axis == "Strike":
        xv, xlabel = Ks, "Strike"
    elif x_axis == "Moneyness K/S":
        xv, xlabel = Ks/spot, "Moneyness (K/S)"
    elif x_axis == "Log-Strike ln(K/F)":
        xv, xlabel = log_k, "Log-Strike ln(K/F)"
    else:  # Delta
        d1_arr = (log_k + 0.5*atm_v**2*T_exp) / (atm_v*np.sqrt(T_exp))
        xv, xlabel = norm.cdf(d1_arr), "Delta (call)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xv, y=mkt_vol_noisy*100, mode='markers',
        name='Market quotes', marker=dict(color='#94a3b8', size=5, opacity=0.8)))
    fig.add_trace(go.Scatter(x=xv, y=svi_fit*100, mode='lines',
        name='SVI fit', line=dict(color='#00d9ff', width=2.5)))
    fig.add_trace(go.Scatter(x=xv, y=quad_vol*100, mode='lines',
        name='Quadratic fit', line=dict(color='#f59e0b', width=1.5, dash='dash')))
    if x_axis == "Strike":
        fig.add_vline(x=spot, line_dash="dot", line_color="#10b981", annotation_text="ATM")
    fig.update_layout(template="plotly_dark", height=chart_h(1),
                      xaxis_title=xlabel, yaxis_title="Implied Vol (%)",
                      legend=dict(x=0.01, y=0.99), margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # SVI metrics
    st.markdown("#### SVI Calibrated Parameters")
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("a (level)", f"{a_f:.5f}")
    m2.metric("b (wings)", f"{b_f:.4f}")
    m3.metric("ρ (skew)", f"{r_f:.3f}")
    m4.metric("m (shift)", f"{m_f:.4f}")
    m5.metric("σ (smooth)", f"{s_f:.4f}")
    m6.metric("RMSE", f"{np.sqrt(res_svi.fun/len(log_k))*100:.3f}%")

    st.divider()
    st.markdown("#### Smile Decomposition — Risk-Reversal & Butterfly")
    # 25D RR and BF
    d25_put = norm.ppf(0.25)
    d25_call = norm.ppf(0.75)
    K25p = F * np.exp(d25_put * atm_v * np.sqrt(T_exp) - 0.5*atm_v**2*T_exp)
    K25c = F * np.exp(d25_call * atm_v * np.sqrt(T_exp) - 0.5*atm_v**2*T_exp)
    lk25p = np.log(K25p/F); lk25c = np.log(K25c/F)
    tv25p = a_f + b_f*(r_f*(lk25p-m_f) + np.sqrt((lk25p-m_f)**2 + s_f**2))
    tv25c = a_f + b_f*(r_f*(lk25c-m_f) + np.sqrt((lk25c-m_f)**2 + s_f**2))
    vol25p = np.sqrt(max(tv25p/T_exp, 0.0001)) * 100
    vol25c = np.sqrt(max(tv25c/T_exp, 0.0001)) * 100
    rr25 = vol25c - vol25p
    bf25 = (vol25c + vol25p)/2 - atm_v*100

    d1c,d2c,d3c,d4c,d5c = st.columns(5)
    d1c.metric("ATM Vol", f"{atm_v*100:.2f}%")
    d2c.metric("25Δ Put Vol", f"{vol25p:.2f}%")
    d3c.metric("25Δ Call Vol", f"{vol25c:.2f}%")
    d4c.metric("25Δ RR", f"{rr25:+.2f}%")
    d5c.metric("25Δ BF", f"{bf25:+.2f}%")

    # Arbitrage check
    with st.expander("Butterfly Arbitrage Check"):
        # Local var must be positive: d²C/dK² > 0
        dlog = log_k[1] - log_k[0]
        dtv = np.gradient(tv_fit, log_k)
        d2tv = np.gradient(dtv, log_k)
        violations = np.sum(tv_fit + 0.25*dtv**2 - 0.5*d2tv < 0)
        if violations == 0:
            st.success("No butterfly arbitrage detected — surface is convex.")
        else:
            st.warning(f"{violations} butterfly arbitrage violations detected.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: SABR CALIBRATION
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### SABR (Hagan 2002) — Full Calibration & Sensitivity")

    c1, c2, c3 = st.columns(3)
    with c1:
        F_sabr = st.number_input("Forward (F)", 0.5, 500.0, 100.0, step=1.0, key="sb_F")
        T_sabr = st.number_input("Maturity T (years)", 0.1, 10.0, 1.0, step=0.1, key="sb_T")
    with c2:
        alpha0 = st.slider("α (initial ATM vol)", 0.01, 1.0, 0.25, 0.01, key="sb_a")
        beta0  = st.slider("β (CEV exponent)", 0.0, 1.0, 0.5, 0.05, key="sb_b")
    with c3:
        rho0   = st.slider("ρ (spot-vol corr)", -0.99, 0.99, -0.30, 0.01, key="sb_r")
        nu0    = st.slider("ν (vol-of-vol)", 0.01, 2.0, 0.40, 0.01, key="sb_n")

    Ks_sabr = np.linspace(F_sabr*0.65, F_sabr*1.35, 61)
    vols_sabr = np.array([sabr_vol(F_sabr, K, T_sabr, alpha0, beta0, rho0, nu0) for K in Ks_sabr])

    # Generate synthetic market data and calibrate
    np.random.seed(42)
    mkt_noise = np.random.normal(0, 0.003, len(Ks_sabr))
    market_vols = vols_sabr + mkt_noise

    def sabr_obj(params):
        a, b, r, n = params
        r = np.clip(r, -0.99, 0.99)
        if a <= 0 or b < 0 or b > 1 or n <= 0: return 1e9
        model = np.array([sabr_vol(F_sabr, K, T_sabr, a, b, r, n) for K in Ks_sabr])
        return np.sum((model - market_vols)**2)

    cal_res = minimize(sabr_obj, [alpha0*0.95, beta0, rho0*1.05, nu0*0.95],
                       method='Nelder-Mead', options={'maxiter':2000,'xatol':1e-7,'fatol':1e-10})
    a_cal, b_cal, r_cal, n_cal = cal_res.x
    r_cal = np.clip(r_cal, -0.99, 0.99)
    vols_cal = np.array([sabr_vol(F_sabr, K, T_sabr, a_cal, b_cal, r_cal, n_cal) for K in Ks_sabr])

    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(x=Ks_sabr, y=market_vols*100, mode='markers',
        name='Market (simulated)', marker=dict(color='#94a3b8', size=5)))
    fig_s.add_trace(go.Scatter(x=Ks_sabr, y=vols_sabr*100, mode='lines',
        name='SABR (manual params)', line=dict(color='#f59e0b', width=2, dash='dash')))
    fig_s.add_trace(go.Scatter(x=Ks_sabr, y=vols_cal*100, mode='lines',
        name='SABR (calibrated)', line=dict(color='#00d9ff', width=2.5)))
    fig_s.add_vline(x=F_sabr, line_dash="dot", line_color="#10b981", annotation_text="ATM")
    fig_s.update_layout(template="plotly_dark", height=chart_h(1),
                        xaxis_title="Strike", yaxis_title="Implied Vol (%)",
                        margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("#### Calibration Results")
    p1,p2,p3,p4,p5 = st.columns(5)
    p1.metric("α (calibrated)", f"{a_cal:.4f}", f"init {alpha0:.3f}")
    p2.metric("β (calibrated)", f"{b_cal:.4f}", f"init {beta0:.3f}")
    p3.metric("ρ (calibrated)", f"{r_cal:.4f}", f"init {rho0:.3f}")
    p4.metric("ν (calibrated)", f"{n_cal:.4f}", f"init {nu0:.3f}")
    rmse = np.sqrt(np.mean((vols_cal - market_vols)**2)) * 100
    p5.metric("RMSE", f"{rmse:.3f}%")

    st.divider()
    st.markdown("#### Multi-Maturity SABR Surface")
    mats = [0.25, 0.5, 1.0, 2.0, 5.0]
    fig_ms = go.Figure()
    colors = ['#00d9ff','#7c3aed','#10b981','#f59e0b','#ef4444']
    for i, t in enumerate(mats):
        vs = np.array([sabr_vol(F_sabr, K, t, a_cal, b_cal, r_cal, n_cal) for K in Ks_sabr])
        fig_ms.add_trace(go.Scatter(x=Ks_sabr/F_sabr, y=vs*100,
            name=f"T={t}Y", line=dict(color=colors[i], width=2)))
    fig_ms.add_vline(x=1.0, line_dash="dot", line_color="#475569", annotation_text="ATM")
    fig_ms.update_layout(template="plotly_dark", height=chart_h(1),
                         xaxis_title="Moneyness (K/F)", yaxis_title="Implied Vol (%)",
                         margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_ms, use_container_width=True)

    with st.expander("SABR Sensitivity (Greeks of vol)"):
        da = 1e-4
        dv_dalpha = np.array([sabr_vol(F_sabr,K,T_sabr,a_cal+da,b_cal,r_cal,n_cal) -
                               sabr_vol(F_sabr,K,T_sabr,a_cal-da,b_cal,r_cal,n_cal) for K in Ks_sabr])/(2*da)
        dv_drho   = np.array([sabr_vol(F_sabr,K,T_sabr,a_cal,b_cal,r_cal+da,n_cal) -
                               sabr_vol(F_sabr,K,T_sabr,a_cal,b_cal,r_cal-da,n_cal) for K in Ks_sabr])/(2*da)
        dv_dnu    = np.array([sabr_vol(F_sabr,K,T_sabr,a_cal,b_cal,r_cal,n_cal+da) -
                               sabr_vol(F_sabr,K,T_sabr,a_cal,b_cal,r_cal,n_cal-da) for K in Ks_sabr])/(2*da)

        fig_sens = make_subplots(rows=1, cols=3,
            subplot_titles=["∂σ/∂α (level)", "∂σ/∂ρ (skew)", "∂σ/∂ν (vol-of-vol)"])
        for col_i, (data, name) in enumerate([(dv_dalpha,"dσ/dα"),(dv_drho,"dσ/dρ"),(dv_dnu,"dσ/dν")], 1):
            fig_sens.add_trace(go.Scatter(x=Ks_sabr/F_sabr, y=data*100,
                line=dict(color=colors[col_i-1], width=2), showlegend=False), row=1, col=col_i)
        fig_sens.update_layout(template="plotly_dark", height=320, margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_sens, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: VOL SURFACE 3D + LOCAL VOL
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown("### Implied Vol Surface (3D) + Local Volatility (Dupire)")

    c1, c2, c3 = st.columns(3)
    with c1:
        S3  = st.number_input("Spot", 50.0, 5000.0, 100.0, step=5.0, key="s3_S")
        r3  = st.number_input("Risk-Free (%)", 0.0, 10.0, 4.5, step=0.1, key="s3_r") / 100
    with c2:
        atm3   = st.number_input("ATM Vol (%)", 5.0, 80.0, 22.0, step=0.5, key="s3_atm") / 100
        skew3  = st.slider("Skew", -0.4, 0.0, -0.20, 0.01, key="s3_skew")
    with c3:
        curv3  = st.slider("Curvature", 0.0, 0.5, 0.10, 0.01, key="s3_curv")
        surf_type = st.selectbox("View", ["Implied Vol", "Local Vol (Dupire)", "Total Variance"], key="s3_view")

    mats_3d = np.array([1/12, 3/12, 6/12, 1.0, 1.5, 2.0, 3.0, 5.0])
    n_k = 41
    moneyness_grid = np.linspace(0.60, 1.40, n_k)
    Ks_3d = S3 * moneyness_grid

    # Build SVI surface per maturity
    surface = np.zeros((len(mats_3d), n_k))
    for i, T in enumerate(mats_3d):
        F3 = S3 * np.exp(r3 * T)
        lk = np.log(Ks_3d / F3)
        a3 = atm3**2 * T * 0.80
        b3 = atm3**2 * T * 0.35
        rho3 = skew3 * 1.8
        sig3 = 0.12 + curv3 * 0.4
        tv = a3 + b3*(rho3*lk + np.sqrt(lk**2 + sig3**2))
        tv = np.maximum(tv, 1e-6)
        surface[i, :] = np.sqrt(tv / T) * 100

    # Dupire local vol: σ_L² = (∂w/∂T) / (1 - k/w * ∂w/∂k + 0.25*(-0.25 - 1/w + k²/w²)*(∂w/∂k)²+ 0.5*∂²w/∂k²)
    # Simplified: interpolate total variance surface
    TV_surf = (surface/100)**2 * mats_3d[:, None]  # total variance
    lk_grid = np.log(moneyness_grid)
    try:
        spline = RectBivariateSpline(mats_3d, lk_grid, TV_surf, kx=3, ky=3)
        lv_surf = np.zeros_like(surface)
        for i, T in enumerate(mats_3d):
            for j, k in enumerate(lk_grid):
                dw_dT   = spline(T, k, dx=1)[0,0]
                dw_dk   = spline(T, k, dy=1)[0,0]
                d2w_dk2 = spline(T, k, dy=2)[0,0]
                w       = TV_surf[i, j]
                if w < 1e-8 or dw_dT < 0: lv_surf[i,j] = surface[i,j]; continue
                denom = 1 - (k/w)*dw_dk + 0.25*(-0.25 - 1/w + k**2/w**2)*dw_dk**2 + 0.5*d2w_dk2
                denom = max(denom, 0.01)
                lv_surf[i, j] = np.sqrt(max(dw_dT / denom, 1e-6)) * 100
    except:
        lv_surf = surface.copy()

    z_data = surface if surf_type == "Implied Vol" else (lv_surf if surf_type == "Local Vol (Dupire)" else TV_surf*1e4)
    z_label = "IV (%)" if surf_type == "Implied Vol" else ("Local Vol (%)" if surf_type == "Local Vol (Dupire)" else "Total Var × 10⁴")

    fig3d = go.Figure(data=[go.Surface(
        x=moneyness_grid, y=mats_3d, z=z_data,
        colorscale=[[0,'#0a0e1a'],[0.2,'#7c3aed'],[0.5,'#00d9ff'],[0.8,'#f59e0b'],[1,'#ef4444']],
        colorbar=dict(title=z_label, thickness=12),
        contours=dict(z=dict(show=True, usecolormap=True, highlightcolor="white", project=dict(z=True)))
    )])
    fig3d.update_layout(
        scene=dict(
            xaxis_title="Moneyness (K/S)",
            yaxis_title="Maturity (years)",
            zaxis_title=z_label,
            bgcolor='#0a0e1a',
            xaxis=dict(backgroundcolor='#0a0e1a', gridcolor='#1e293b'),
            yaxis=dict(backgroundcolor='#0a0e1a', gridcolor='#1e293b'),
            zaxis=dict(backgroundcolor='#0a0e1a', gridcolor='#1e293b'),
        ),
        template="plotly_dark", height=560, margin=dict(l=0,r=0,t=30,b=0),
        paper_bgcolor='#0a0e1a',
    )
    st.plotly_chart(fig3d, use_container_width=True)

    st.markdown("#### Term Structure of ATM Vols")
    atm_vols_ts = [surface[i, n_k//2] for i in range(len(mats_3d))]
    atm_lv_ts   = [lv_surf[i, n_k//2] for i in range(len(mats_3d))]
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=mats_3d*12, y=atm_vols_ts, mode='lines+markers',
        name='ATM IV', line=dict(color='#00d9ff', width=2.5)))
    fig_ts.add_trace(go.Scatter(x=mats_3d*12, y=atm_lv_ts, mode='lines+markers',
        name='ATM LV (Dupire)', line=dict(color='#f59e0b', width=2, dash='dash')))
    fig_ts.update_layout(template="plotly_dark", height=300,
                         xaxis_title="Maturity (months)", yaxis_title="Vol (%)",
                         margin=dict(l=0,r=0,t=20,b=0))
    st.plotly_chart(fig_ts, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: HESTON MODEL
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("### Heston Stochastic Volatility Model")
    st.caption("dS = S(r dt + √v dW₁)  ·  dv = κ(θ−v)dt + ξ√v dW₂  ·  corr(W₁,W₂) = ρ")

    c1, c2, c3 = st.columns(3)
    with c1:
        S_h = st.number_input("Spot", 50.0, 5000.0, 100.0, step=5.0, key="h_S")
        r_h = st.number_input("Risk-Free (%)", 0.0, 10.0, 4.5, step=0.1, key="h_r") / 100
        v0_h = st.slider("v₀ (initial var)", 0.01, 0.5, 0.04, 0.005, key="h_v0",
                         help="Initial variance (≈ σ²). 0.04 → 20% vol")
    with c2:
        kappa = st.slider("κ (mean-rev speed)", 0.1, 10.0, 2.0, 0.1, key="h_k")
        theta = st.slider("θ (long-run var)", 0.01, 0.5, 0.04, 0.005, key="h_th",
                          help="Long-run variance. 0.04 → 20% vol")
        xi    = st.slider("ξ (vol-of-vol)", 0.01, 2.0, 0.5, 0.01, key="h_xi")
    with c3:
        rho_h = st.slider("ρ (spot-vol corr)", -0.99, 0.99, -0.70, 0.01, key="h_rho")
        T_h   = st.number_input("Maturity (years)", 0.1, 5.0, 1.0, step=0.1, key="h_T")
        feller = 2*kappa*theta
        feller_ok = feller > xi**2
        if feller_ok:
            st.success(f"Feller: 2κθ={feller:.3f} > ξ²={xi**2:.3f} ✓")
        else:
            st.warning(f"Feller violated: 2κθ={feller:.3f} < ξ²={xi**2:.3f} — vol can hit 0")

    # Heston characteristic function & option price via COS method (simplified)
    def heston_cf(u, S, v0, kappa, theta, xi, rho, r, T):
        """Heston characteristic function of log(S_T)."""
        i = 1j
        d = np.sqrt((rho*xi*i*u - kappa)**2 + xi**2*(i*u + u**2))
        g = (kappa - rho*xi*i*u - d) / (kappa - rho*xi*i*u + d)
        C = r*i*u*T + kappa*theta/xi**2 * (
            (kappa - rho*xi*i*u - d)*T - 2*np.log((1 - g*np.exp(-d*T))/(1 - g))
        )
        D = (kappa - rho*xi*i*u - d)/xi**2 * (1 - np.exp(-d*T))/(1 - g*np.exp(-d*T))
        return np.exp(C + D*v0 + i*u*np.log(S*np.exp(r*T)))

    def heston_call(S, K, v0, kappa, theta, xi, rho, r, T, N=256):
        """Heston call price via Carr-Madan FFT (simplified COS)."""
        F = S * np.exp(r*T)
        x = np.log(F/K)
        du = 0.1
        u_max = N * du
        us = np.arange(0.5*du, u_max, du)
        cf_vals = np.array([heston_cf(u-0.5j, S, v0, kappa, theta, xi, rho, r, T)
                            / (heston_cf(-0.5j, S, v0, kappa, theta, xi, rho, r, T))
                            for u in us])
        integrand = np.real(cf_vals * np.exp(-1j*us*x)) / (us**2 + 0.25)
        price = F * np.exp(-r*T) - np.sqrt(F*K)*np.exp(-r*T)/np.pi * np.trapz(integrand, us)
        return max(price, max(F - K, 0) * np.exp(-r*T))

    # Compute Heston smile
    Ks_h = np.linspace(S_h*0.6, S_h*1.4, 41)
    heston_ivs = []
    for K in Ks_h:
        try:
            c = heston_call(S_h, K, v0_h, kappa, theta, xi, rho_h, r_h, T_h)
            iv = iv_from_price(c, S_h, K, T_h, r_h, 'call')
            heston_ivs.append(iv*100)
        except:
            heston_ivs.append(np.sqrt(v0_h)*100)
    heston_ivs = np.array(heston_ivs)

    # BS smile for comparison
    bs_flat = np.full(len(Ks_h), np.sqrt(v0_h)*100)

    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(x=Ks_h/S_h, y=heston_ivs, mode='lines',
        name='Heston IV', line=dict(color='#00d9ff', width=2.5)))
    fig_h.add_trace(go.Scatter(x=Ks_h/S_h, y=bs_flat, mode='lines',
        name='BS flat (v₀)', line=dict(color='#64748b', width=1.5, dash='dot')))
    fig_h.add_vline(x=1.0, line_dash="dot", line_color="#10b981", annotation_text="ATM")
    fig_h.update_layout(template="plotly_dark", height=380,
                         xaxis_title="Moneyness (K/S)", yaxis_title="Implied Vol (%)",
                         margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_h, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Variance Path Simulation")
        n_paths = 10
        dt_sim = T_h / 252
        steps  = int(T_h * 252)
        rng = np.random.default_rng(42)
        fig_vp = go.Figure()
        t_axis = np.linspace(0, T_h, steps+1)
        for _ in range(n_paths):
            v = np.zeros(steps+1); v[0] = v0_h
            for t_idx in range(steps):
                dW = rng.standard_normal()
                v[t_idx+1] = max(v[t_idx] + kappa*(theta - v[t_idx])*dt_sim
                                  + xi*np.sqrt(max(v[t_idx],0))*np.sqrt(dt_sim)*dW, 0)
            fig_vp.add_trace(go.Scatter(x=t_axis, y=np.sqrt(v)*100,
                mode='lines', line=dict(width=1), opacity=0.6, showlegend=False))
        fig_vp.add_hline(y=np.sqrt(theta)*100, line_dash="dash", line_color="#f59e0b",
                          annotation_text=f"θ^0.5={np.sqrt(theta)*100:.1f}%")
        fig_vp.update_layout(template="plotly_dark", height=300,
                              xaxis_title="Time (years)", yaxis_title="Inst. Vol (%)",
                              margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig_vp, use_container_width=True)

    with c2:
        st.markdown("#### Multi-Maturity Heston Surface")
        mats_h = [0.25, 0.5, 1.0, 2.0]
        fig_hm = go.Figure()
        c_list = ['#00d9ff','#7c3aed','#10b981','#f59e0b']
        for i, T_i in enumerate(mats_h):
            ivs_i = []
            for K in Ks_h:
                try:
                    c_i = heston_call(S_h, K, v0_h, kappa, theta, xi, rho_h, r_h, T_i)
                    ivs_i.append(iv_from_price(c_i, S_h, K, T_i, r_h)*100)
                except: ivs_i.append(np.sqrt(v0_h)*100)
            fig_hm.add_trace(go.Scatter(x=Ks_h/S_h, y=ivs_i,
                name=f"T={T_i}Y", line=dict(color=c_list[i], width=2)))
        fig_hm.add_vline(x=1.0, line_dash="dot", line_color="#475569")
        fig_hm.update_layout(template="plotly_dark", height=300,
                              xaxis_title="Moneyness", yaxis_title="IV (%)",
                              margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig_hm, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: VOL FORECASTING
# ─────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown("### Volatility Forecasting — EWMA · GARCH · GJR-GARCH · HAR-RV")

    c1, c2 = st.columns([2, 1])
    with c1:
        ticker_f = st.text_input("Ticker (live data)", "SPY", key="vf_ticker")
    with c2:
        use_live = st.checkbox("Use live yfinance data", value=True, key="vf_live")

    prices_f, ret_f = None, None
    if use_live:
        prices_f, ret_f = fetch_real_data(ticker_f)

    if prices_f is not None and ret_f is not None and len(ret_f) > 30:
        returns = ret_f
        source = f"Live: {ticker_f} ({len(returns)} days)"
    else:
        np.random.seed(99)
        # Simulate returns with volatility clustering (GARCH-like)
        n_sim = 252
        returns = np.zeros(n_sim)
        v = 0.0004
        for t in range(n_sim):
            v = 0.000001 + 0.08*returns[max(t-1,0)]**2 + 0.89*v
            returns[t] = np.random.normal(0, np.sqrt(v))
        source = "Simulated (GARCH-like, 252 days)"
    st.caption(f"Data source: {source}")

    lam = st.slider("EWMA λ (RiskMetrics)", 0.80, 0.99, 0.94, 0.01, key="vf_lam")
    n_fcast = st.slider("Forecast horizon (days)", 1, 60, 22, key="vf_h")

    # ── EWMA ──
    var_ewma = np.zeros(len(returns))
    var_ewma[0] = returns[0]**2
    for t in range(1, len(returns)):
        var_ewma[t] = lam*var_ewma[t-1] + (1-lam)*returns[t-1]**2
    vol_ewma = np.sqrt(var_ewma * 252) * 100
    ewma_fcast = np.full(n_fcast, vol_ewma[-1])

    # ── GARCH(1,1) MLE via scipy ──
    def garch_loglik(params, rets):
        omega, alpha_g, beta_g = params
        if omega<=0 or alpha_g<=0 or beta_g<=0 or alpha_g+beta_g>=1: return 1e10
        n = len(rets)
        v = np.var(rets)
        ll = 0
        for t in range(1, n):
            v = omega + alpha_g*rets[t-1]**2 + beta_g*v
            if v <= 0: return 1e10
            ll += np.log(v) + rets[t]**2/v
        return ll

    g_res = minimize(garch_loglik, [1e-6, 0.08, 0.88], args=(returns,),
                     method='L-BFGS-B', bounds=[(1e-8,1e-3),(1e-4,0.5),(1e-4,0.9999)])
    omega_g, alpha_g, beta_g = g_res.x
    var_garch = np.zeros(len(returns))
    var_garch[0] = np.var(returns)
    for t in range(1, len(returns)):
        var_garch[t] = omega_g + alpha_g*returns[t-1]**2 + beta_g*var_garch[t-1]
    vol_garch = np.sqrt(var_garch * 252) * 100
    # GARCH forecast
    lt_var = omega_g/(1 - alpha_g - beta_g) if (alpha_g+beta_g) < 1 else var_garch[-1]
    garch_fcast_var = np.zeros(n_fcast)
    garch_fcast_var[0] = var_garch[-1]
    for t in range(1, n_fcast):
        garch_fcast_var[t] = lt_var + (alpha_g+beta_g)*(garch_fcast_var[t-1] - lt_var)
    garch_fcast = np.sqrt(garch_fcast_var * 252) * 100

    # ── GJR-GARCH (Glosten-Jagannathan-Runkle) ──
    def gjr_loglik(params, rets):
        omega, alpha_g, gamma_gjr, beta_g = params
        if omega<=0 or alpha_g<=0 or beta_g<=0 or alpha_g+beta_g+0.5*gamma_gjr>=1: return 1e10
        n = len(rets)
        v = np.var(rets); ll = 0
        for t in range(1, n):
            ind = 1.0 if rets[t-1] < 0 else 0.0
            v = omega + (alpha_g + gamma_gjr*ind)*rets[t-1]**2 + beta_g*v
            if v <= 0: return 1e10
            ll += np.log(v) + rets[t]**2/v
        return ll

    gjr_res = minimize(gjr_loglik, [1e-6, 0.05, 0.08, 0.88], args=(returns,),
                       method='L-BFGS-B', bounds=[(1e-8,1e-3),(1e-4,0.5),(0,0.5),(1e-4,0.9999)])
    omega_gjr, alpha_gjr, gamma_gjr, beta_gjr = gjr_res.x
    var_gjr = np.zeros(len(returns))
    var_gjr[0] = np.var(returns)
    for t in range(1, len(returns)):
        ind = 1.0 if returns[t-1] < 0 else 0.0
        var_gjr[t] = omega_gjr + (alpha_gjr + gamma_gjr*ind)*returns[t-1]**2 + beta_gjr*var_gjr[t-1]
    vol_gjr = np.sqrt(np.maximum(var_gjr, 0) * 252) * 100

    # ── HAR-RV (Heterogeneous AutoRegressive) ──
    rv_1d  = returns**2 * 252
    rv_5d  = pd.Series(rv_1d).rolling(5).mean().values
    rv_22d = pd.Series(rv_1d).rolling(22).mean().values
    valid  = ~np.isnan(rv_22d)
    if valid.sum() > 30:
        X_har = np.column_stack([np.ones(valid.sum()), rv_1d[valid], rv_5d[valid], rv_22d[valid]])
        y_har = rv_1d[valid]
        XtX = X_har.T @ X_har + 1e-8*np.eye(4)
        Xty = X_har.T @ y_har
        beta_har = np.linalg.solve(XtX, Xty)
        har_pred = X_har @ beta_har
        vol_har_full = np.full(len(returns), np.nan)
        vol_har_full[valid] = np.sqrt(np.maximum(har_pred, 0)) * 100
        har_fcast_rv = beta_har[0] + beta_har[1]*rv_1d[-1] + beta_har[2]*rv_5d[-1] + beta_har[3]*rv_22d[-1]
        har_fcast = np.sqrt(max(har_fcast_rv, 0)) * 100
    else:
        vol_har_full = vol_ewma.copy()
        har_fcast = float(vol_ewma[-1])

    # ── Chart ──
    days = np.arange(len(returns))
    fig_f = go.Figure()
    rv_plot = np.abs(returns) * np.sqrt(252) * 100
    fig_f.add_trace(go.Scatter(x=days, y=rv_plot, mode='lines', name='|Return|×√252',
        line=dict(color='#334155', width=1), opacity=0.5))
    fig_f.add_trace(go.Scatter(x=days, y=vol_ewma, name='EWMA', line=dict(color='#00d9ff', width=2)))
    fig_f.add_trace(go.Scatter(x=days, y=vol_garch, name='GARCH(1,1)', line=dict(color='#7c3aed', width=2)))
    fig_f.add_trace(go.Scatter(x=days, y=vol_gjr, name='GJR-GARCH', line=dict(color='#f59e0b', width=1.5, dash='dash')))
    fig_f.add_trace(go.Scatter(x=days, y=vol_har_full, name='HAR-RV', line=dict(color='#10b981', width=1.5, dash='dot')))

    fc_days = np.arange(len(returns), len(returns)+n_fcast)
    fig_f.add_trace(go.Scatter(x=fc_days, y=ewma_fcast, name='EWMA fcast', line=dict(color='#00d9ff', width=2, dash='dash')))
    fig_f.add_trace(go.Scatter(x=fc_days, y=garch_fcast, name='GARCH fcast', line=dict(color='#7c3aed', width=2, dash='dot')))
    fig_f.add_vline(x=len(returns)-0.5, line_dash="dash", line_color="#475569", annotation_text="Forecast →")
    fig_f.update_layout(template="plotly_dark", height=chart_h(1),
                         xaxis_title="Days", yaxis_title="Annualized Vol (%)",
                         margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_f, use_container_width=True)

    st.markdown("#### Model Parameters & Forecast")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("EWMA λ", f"{lam:.2f}",   f"fcast: {ewma_fcast[0]:.2f}%")
    m2.metric("GARCH α+β", f"{alpha_g+beta_g:.4f}", f"LT vol: {np.sqrt(lt_var*252)*100:.2f}%")
    m3.metric("GJR leverage γ", f"{gamma_gjr:.4f}", "neg-shock amplification")
    m4.metric("HAR {1d}/{5d}/{22d}w",
              f"{beta_har[1]:.2f}/{beta_har[2]:.2f}/{beta_har[3]:.2f}" if valid.sum()>30 else "N/A",
              f"fcast: {har_fcast:.2f}%")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: VOL TERM STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown("### Volatility Term Structure — Forward Vol & Nelson-Siegel")

    c1, c2, c3 = st.columns(3)
    with c1:
        ts_atm  = st.number_input("Spot ATM vol (%)", 5.0, 80.0, 22.0, step=0.5, key="ts_atm") / 100
        ts_lt   = st.number_input("Long-run vol (%)", 5.0, 60.0, 18.0, step=0.5, key="ts_lt") / 100
    with c2:
        ts_kap  = st.slider("Mean-rev speed κ", 0.1, 5.0, 1.2, 0.1, key="ts_kap")
        ts_hump = st.slider("Hump (λ)", 0.1, 5.0, 1.0, 0.1, key="ts_l",
                             help="Nelson-Siegel curvature parameter")
    with c3:
        ts_curv = st.slider("Curvature β₂", -0.2, 0.2, 0.03, 0.005, key="ts_c2")
        ts_skew = st.slider("Term skew", -0.05, 0.05, -0.01, 0.005, key="ts_sk")

    mats_ts = np.array([1/52, 1/26, 1/12, 3/12, 6/12, 9/12, 1, 1.5, 2, 3, 5, 7, 10])
    labels_ts = ['1W','2W','1M','3M','6M','9M','1Y','18M','2Y','3Y','5Y','7Y','10Y']

    # Mean-reverting model
    mr_vol = ts_lt + (ts_atm - ts_lt) * np.exp(-ts_kap * mats_ts)

    # Nelson-Siegel vol term structure
    def ns_vol(T, b0, b1, b2, lam):
        decay = (1 - np.exp(-lam*T))/(lam*T)
        return b0 + b1*decay + b2*(decay - np.exp(-lam*T))

    b0 = ts_lt; b1 = ts_atm - ts_lt; b2 = ts_curv
    ns_vols = np.array([ns_vol(T, b0, b1, b2, ts_hump) for T in mats_ts])

    # Power law
    pow_vol = ts_atm * (mats_ts/mats_ts[0])**ts_skew

    # Forward vol: f(T1,T2) = sqrt((T2*σ(T2)² - T1*σ(T1)²)/(T2-T1))
    def fwd_vol(mats, vols):
        fvols = [np.nan]
        for i in range(1, len(mats)):
            tv2 = vols[i]**2 * mats[i]
            tv1 = vols[i-1]**2 * mats[i-1]
            dT  = mats[i] - mats[i-1]
            fv  = np.sqrt(max((tv2 - tv1)/dT, 1e-8))
            fvols.append(fv)
        return np.array(fvols)

    fwd_mr = fwd_vol(mats_ts, mr_vol)
    fwd_ns = fwd_vol(mats_ts, ns_vols)

    fig_ts_main = go.Figure()
    fig_ts_main.add_trace(go.Scatter(x=list(range(len(mats_ts))), y=mr_vol*100,
        name='Mean-Reverting', mode='lines+markers', line=dict(color='#00d9ff', width=2.5)))
    fig_ts_main.add_trace(go.Scatter(x=list(range(len(mats_ts))), y=ns_vols*100,
        name='Nelson-Siegel', mode='lines+markers', line=dict(color='#7c3aed', width=2.5)))
    fig_ts_main.add_trace(go.Scatter(x=list(range(len(mats_ts))), y=pow_vol*100,
        name='Power Law', mode='lines', line=dict(color='#f59e0b', width=1.5, dash='dash')))
    fig_ts_main.add_trace(go.Scatter(x=list(range(1,len(mats_ts))), y=fwd_mr[1:]*100,
        name='Fwd Vol (MR)', mode='lines', line=dict(color='#10b981', width=1.5, dash='dot')))
    fig_ts_main.update_layout(template="plotly_dark", height=380,
        xaxis=dict(tickmode='array', tickvals=list(range(len(mats_ts))), ticktext=labels_ts),
        yaxis_title="Vol (%)", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_ts_main, use_container_width=True)

    st.markdown("#### Term Structure Table")
    df_ts = pd.DataFrame({
        'Maturity': labels_ts,
        'Mean-Rev (%)': [f"{v*100:.2f}" for v in mr_vol],
        'Nelson-Siegel (%)': [f"{v*100:.2f}" for v in ns_vols],
        'Fwd Vol MR (%)': ['—'] + [f"{v*100:.2f}" if not np.isnan(v) else '—' for v in fwd_mr[1:]],
        'Fwd Vol NS (%)': ['—'] + [f"{v*100:.2f}" if not np.isnan(v) else '—' for v in fwd_ns[1:]],
    })
    st.dataframe(df_ts, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7: VOL RISK PREMIUM
# ─────────────────────────────────────────────────────────────────────────────
with tabs[6]:
    st.markdown("### Variance Risk Premium (VRP) — Implied vs Realized")
    st.caption("VRP = IV − RV  (positive = vol sellers paid risk premium)  ·  Funding cost of variance swaps")

    c1, c2 = st.columns([2,1])
    with c1:
        vrp_ticker = st.text_input("Ticker", "SPY", key="vrp_ticker")
    with c2:
        vrp_live = st.checkbox("Use live data", True, key="vrp_live")

    prices_v, rets_v = fetch_real_data(vrp_ticker) if vrp_live else (None, None)
    if prices_v is None or len(prices_v) < 60:
        np.random.seed(5)
        rets_v = np.random.normal(0.0005, 0.013, 252)
        prices_v = 100 * np.cumprod(1 + rets_v)

    # Rolling realized vol (22D)
    rv_22 = pd.Series(rets_v**2).rolling(22).sum().values * (252/22)
    rv_22 = np.sqrt(np.maximum(rv_22, 0)) * 100

    # Synthetic implied vol (VIX proxy): IV > RV on average by ~3-5 vol points
    np.random.seed(7)
    iv_synth = rv_22 + np.random.normal(3.5, 2.5, len(rv_22))
    iv_synth = np.maximum(iv_synth, rv_22 * 0.8)

    vrp = iv_synth - rv_22
    vrp_pos = np.maximum(vrp, 0)
    vrp_neg = np.minimum(vrp, 0)

    days_v = np.arange(len(rv_22))
    valid_v = ~np.isnan(rv_22)

    fig_vrp = make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35],
                             subplot_titles=["IV vs RV (22D)", "Variance Risk Premium (IV − RV)"],
                             shared_xaxes=True, vertical_spacing=0.06)

    fig_vrp.add_trace(go.Scatter(x=days_v[valid_v], y=iv_synth[valid_v],
        name='Implied Vol (proxy)', line=dict(color='#00d9ff', width=1.5)), row=1, col=1)
    fig_vrp.add_trace(go.Scatter(x=days_v[valid_v], y=rv_22[valid_v],
        name='Realized Vol (22D)', line=dict(color='#f59e0b', width=1.5)), row=1, col=1)
    fig_vrp.add_trace(go.Bar(x=days_v[valid_v], y=vrp_pos[valid_v],
        name='VRP+', marker_color='#10b981', opacity=0.7), row=2, col=1)
    fig_vrp.add_trace(go.Bar(x=days_v[valid_v], y=vrp_neg[valid_v],
        name='VRP−', marker_color='#ef4444', opacity=0.7), row=2, col=1)
    fig_vrp.add_hline(y=0, row=2, col=1, line_color='#475569', line_dash='dash')
    fig_vrp.update_layout(template="plotly_dark", height=chart_h(1),
                           margin=dict(l=0,r=0,t=40,b=0), barmode='relative')
    st.plotly_chart(fig_vrp, use_container_width=True)

    # VRP stats
    vrp_valid = vrp[valid_v]
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Mean VRP", f"{np.nanmean(vrp_valid):+.2f} vol pts")
    m2.metric("Median VRP", f"{np.nanmedian(vrp_valid):+.2f} vol pts")
    m3.metric("VRP Sharpe", f"{np.nanmean(vrp_valid)/np.nanstd(vrp_valid)*np.sqrt(252/22):.2f}")
    m4.metric("% Positive", f"{100*np.mean(vrp_valid>0):.1f}%")
    m5.metric("Max Negative VRP", f"{np.nanmin(vrp_valid):.2f} vol pts")

    st.divider()
    st.markdown("#### Variance Swap Pricing")
    c1, c2, c3, c4 = st.columns(4)
    with c1: vs_T   = st.number_input("Maturity (years)", 0.05, 2.0, 0.25, step=0.05, key="vs_T")
    with c2: vs_atm = st.number_input("ATM IV (%)", 5.0, 100.0, 22.0, step=0.5, key="vs_atm")
    with c3: vs_rv  = st.number_input("Expected RV (%)", 5.0, 100.0, 18.0, step=0.5, key="vs_rv")
    with c4: vs_notional = st.number_input("Vega notional ($)", 1000, 1000000, 100000, step=1000, key="vs_n")

    K_var = (vs_atm/100)**2 * 10000   # var strike in vol² pts
    rv_final = (vs_rv/100)**2 * 10000  # expected realized variance
    pnl_varswap = (rv_final - K_var) * vs_notional / (2 * vs_atm/100 * 100)

    vs1,vs2,vs3,vs4 = st.columns(4)
    vs1.metric("Variance Strike (K_var)", f"{K_var:.2f}")
    vs2.metric("Expected Payout", f"${pnl_varswap:,.0f}")
    vs3.metric("Fair Vol (√K_var)", f"{np.sqrt(K_var):.2f}%")
    vs4.metric("VRP in swap", f"{vs_atm - vs_rv:+.2f} vol pts")
