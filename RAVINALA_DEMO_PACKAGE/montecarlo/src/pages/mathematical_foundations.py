"""
Fusion 7 — Mathematical Foundations
Absorbs: learn.py, quantum_academy.py, probability_bible_page.py
Three pillars: Educational Hub · Quantum Academy · Probability Bible
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

_render_page_header(
    "MF", "Mathematical Foundations",
    "Educational hub, pricing theory and stochastic calculus",
    "Academy"
)

_BG = "#0A0A0F"
_GRID = "rgba(255,255,255,0.04)"
_BASE_LAYOUT = dict(paper_bgcolor=_BG, plot_bgcolor=_BG,
                     font=dict(color="#9ca3af"),
                     xaxis=dict(gridcolor=_GRID),
                     yaxis=dict(gridcolor=_GRID))

# ── top-level tabs ──────────────────────────────────────────────
tab_edu, tab_qa, tab_pb = st.tabs([
    "📚 Educational Hub",
    "⚛️ Quantum Academy",
    "🎲 Probability Bible",
])

# ═══════════════════════════════════════════════════════════════
#  TAB 1 — Educational Hub  (from learn.py)
# ═══════════════════════════════════════════════════════════════
with tab_edu:
    edu_tabs = st.tabs([
        "Equities & Indices", "Commodities", "FX Pairs",
        "Interest Rates", "Macro Indicators"
    ])

    # --- Equities & Indices ---
    with edu_tabs[0]:
        st.markdown("### Equities & Major Indices")
        st.markdown("""
**What are Equity Indices?**

An equity index is a grouping of stocks that measures market performance. Key indices:
- **S&P 500** (USA): 500 large-cap US companies → Market leader
- **DAX** (Germany): 40 largest German companies → Eurozone bellwether
- **EUROSTOXX 50** (Eurozone): 50 largest EU companies
- **Nikkei 225** (Japan): 225 top Japanese companies
- **Hang Seng** (Hong Kong): Major Hong Kong stocks
- **KOSPI** (South Korea): Korean market index
        """)
        if st.button("Load Indices Snapshot", key="mf_equity_snap"):
            try:
                from macro_data import fetch_indices_snapshot
                df = fetch_indices_snapshot()
                if df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Commodities ---
    with edu_tabs[1]:
        st.markdown("### Commodities Markets")
        st.markdown("""
**What are Commodities?**

Raw materials and agricultural products traded on global exchanges:
- **Energy**: WTI Crude, Brent, Natural Gas
- **Metals**: Gold, Silver, Copper, Aluminum
- **Agricultural**: Wheat, Corn, Soybeans, Coffee, Cocoa
- **Uses**: Industrial production, hedging inflation, portfolio diversification
        """)
        if st.button("Load Commodities", key="mf_comm_snap"):
            try:
                from macro_data import fetch_commodities_snapshot
                df = fetch_commodities_snapshot()
                if df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

    # --- FX Pairs ---
    with edu_tabs[2]:
        st.markdown("### Foreign Exchange (FX) Markets")
        st.markdown("""
**What is FX?**

Currency trading market — largest financial market globally (~$6 trillion daily volume).

**Key Pairs:**
- **EUR/USD**: Euro vs US Dollar (most liquid)
- **GBP/USD**: British Pound vs Dollar
- **USD/JPY**: Dollar vs Yen (safe-haven pair)
- **AUD/USD**: Australian Dollar vs Dollar
- **Emerging Markets**: USD/CNH, USD/INR, USD/BRL
        """)
        if st.button("Load FX Snapshot", key="mf_fx_snap"):
            try:
                from macro_data import fetch_fx_snapshot
                df = fetch_fx_snapshot()
                if df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Interest Rates ---
    with edu_tabs[3]:
        st.markdown("### Interest Rates & Fixed Income")
        st.markdown("""
**What are Interest Rates?**

Cost of borrowing / return on lending. Government bond yields are key economic indicators.

**Key Rates:**
- **US Treasuries**: 2Y, 5Y, 10Y benchmarks (Fed policy-sensitive)
- **German Bunds**: Eurozone risk-free rate
- **UK Gilts**: BOE policy-sensitive
- **Japan JGB**: BOJ heavily manages yields
- **Spreads**: Yield curve (2Y-10Y), credit spreads measure risk
- **1 basis point = 0.01%**
        """)
        if st.button("Load Rates Snapshot", key="mf_rates_snap"):
            try:
                from macro_data import fetch_rates_snapshot
                df = fetch_rates_snapshot()
                if df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Macro Indicators ---
    with edu_tabs[4]:
        st.markdown("### Macroeconomic Indicators")
        st.markdown("""
**Key Macro Indicators:**
- **CPI (Inflation)**: YoY % change in consumer prices (Central banks target 2%)
- **GDP**: Total economic output growth (YoY %)
- **Unemployment**: % of labor force without jobs
- **Central Bank Rates**: Fed Funds Rate, ECB Deposit Rate, BOJ Policy Rate
- **Demographics**: Population growth, median age
        """)

# ═══════════════════════════════════════════════════════════════
#  TAB 2 — Quantum Academy  (from quantum_academy.py)
# ═══════════════════════════════════════════════════════════════
with tab_qa:
    qa_tabs = st.tabs([
        "BSM Foundations", "Greeks Library",
        "Numerical Methods", "Exotic Mechanics"
    ])

    # --- BSM Foundations ---
    with qa_tabs[0]:
        st.markdown("### The Black-Scholes-Merton PDE")
        st.latex(r"\frac{\partial V}{\partial t} + (r-q)S\frac{\partial V}{\partial S} "
                 r"+ \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")
        st.markdown("Under the risk-neutral measure Q, the underlying follows:")
        st.latex(r"dS_t = (r-q)S_t\,dt + \sigma S_t\,dW_t^Q")
        st.markdown("**Closed-form solution — European Call:**")
        st.latex(r"C = Se^{-qT}N(d_1) - Ke^{-rT}N(d_2)")
        st.latex(r"d_1 = \frac{\ln(S/K) + (r - q + \frac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}, "
                 r"\quad d_2 = d_1 - \sigma\sqrt{T}")
        st.markdown("**Model Assumptions and their limits:**")
        for assumption, reality in {
            "Constant volatility":
                "Reality: Implied vol varies with strike (smile) → SABR, Heston, SVI",
            "No jumps":
                "Reality: Overnight gaps → Merton Jump-Diffusion, Variance Gamma",
            "Continuous hedging":
                "Reality: Discrete rebalancing → residual Gamma P&L",
            "Log-normal returns":
                "Reality: Fat tails (kurtosis ≈ 4-6) → Lévy processes",
            "No transaction costs":
                "Reality: Bid-ask spreads → Deep Hedging (Reinforcement Learning)",
        }.items():
            with st.expander(assumption):
                st.write(reality)

    # --- Greeks Library ---
    with qa_tabs[1]:
        st.markdown("### Greeks Reference Library")
        greek_ref = {
            "Delta (Δ)": (
                r"\Delta_{call} = e^{-qT} N(d_1)",
                "Price move per €1 spot. Hedge: hold -Δ shares."),
            "Gamma (Γ)": (
                r"\Gamma = \frac{e^{-qT} N'(d_1)}{S\sigma\sqrt{T}}",
                "Rate of Delta change. Long Γ = profits from large moves. Peaks ATM near expiry."),
            "Vega (ν)": (
                r"\nu = Se^{-qT}\sqrt{T}\,N'(d_1)/100",
                "Price change per 1% vol move. Always positive for long options."),
            "Theta (Θ)": (
                r"\Theta = \frac{-Se^{-qT}N'(d_1)\sigma}{2\sqrt{T}} - rKe^{-rT}N(d_2)",
                "Daily time decay. Theta = -Gamma·S²σ²/2 (BSM identity)."),
            "Vanna": (
                r"\text{Vanna} = -e^{-qT}N'(d_1)\frac{d_2}{\sigma}",
                "How Delta changes with vol. Critical for crash hedging."),
            "Volga (Vomma)": (
                r"\text{Volga} = Se^{-qT}\sqrt{T}\,N'(d_1)\frac{d_1 d_2}{\sigma}",
                "Vol-of-vol risk. Highest for OTM options."),
            "Charm": (
                r"\text{Charm} = -e^{-qT}\left[N'(d_1)"
                r"\frac{2(r-q)T - d_2\sigma\sqrt{T}}{2T\sigma\sqrt{T}}\right]",
                "Daily Delta decay — how delta changes overnight."),
        }
        sel_g = st.selectbox("Select Greek", list(greek_ref.keys()), key="mf_greek")
        formula, interp = greek_ref[sel_g]
        st.latex(formula)
        st.info(f"**Interpretation:** {interp}")

    # --- Numerical Methods ---
    with qa_tabs[2]:
        st.markdown("### Numerical Methods")
        nm_tabs = st.tabs(["Monte Carlo", "Finite Differences", "SABR Calibration"])

        with nm_tabs[0]:
            st.latex(r"C_0 = e^{-rT} \mathbb{E}^Q\!\left[\max(S_T - K, 0)\right] "
                     r"\approx e^{-rT}\frac{1}{N}\sum_{i=1}^N (S_T^{(i)}-K)^+")
            st.markdown("**Standard Error:**")
            st.latex(r"SE = \frac{\hat{\sigma}}{\sqrt{N}} \implies "
                     r"\text{halving SE requires } 4\times \text{ more paths}")
            st.markdown("**Antithetic Variates (Ravinala uses this):**")
            st.latex(r"\hat{C}_{AV} = \frac{f(Z) + f(-Z)}{2} "
                     r"\quad \Rightarrow \quad \text{Var}[\hat{C}_{AV}] \leq \text{Var}[\hat{C}]")

        with nm_tabs[1]:
            st.markdown("**Crank-Nicolson scheme** — 2nd order accurate, unconditionally stable:")
            st.latex(r"\frac{V^{n+1}_i - V^n_i}{\Delta t} = "
                     r"\frac{1}{2}\left(\mathcal{L}V^n_i + \mathcal{L}V^{n+1}_i\right)")
            st.markdown(
                "where $\\mathcal{L}$ is the Black-Scholes spatial operator "
                "applied at grid point $i$."
            )

        with nm_tabs[2]:
            st.markdown("**SABR stochastic volatility model:**")
            st.latex(r"dF = \sigma F^\beta dW_1, \quad d\sigma = \nu\sigma dW_2, "
                     r"\quad \langle dW_1, dW_2 \rangle = \rho\,dt")
            st.markdown("""
| α | β | ρ | ν |
|---|---|---|---|
| Vol level | Backbone (0=normal, 1=lognormal) | Skew (neg for equity) | Smile curvature |
""")

    # --- Exotic Mechanics ---
    with qa_tabs[3]:
        st.markdown("### Exotic Payoff Mechanics")
        sel_ex = st.selectbox(
            "Select Exotic", ["Barrier", "Asian", "Autocall", "Himalaya"],
            key="mf_exotic"
        )
        if sel_ex == "Barrier":
            st.latex(r"V_{DI}(T) = (S_T - K)^+ \cdot "
                     r"\mathbf{1}_{\{\min_{t} S_t > B\}}")
            st.markdown(
                "**Gap Risk:** Stock can jump below barrier overnight — "
                "cannot hedge continuously. Priced via Monte Carlo with small Δt."
            )
        elif sel_ex == "Asian":
            st.latex(r"V_{Asian}(T) = \left(\frac{1}{N}\sum_{i=1}^N S_{t_i} - K\right)^+")
            st.markdown(
                "Average price option — lower vol than vanilla, popular in "
                "commodities. No closed-form: use MC or recursive PDE."
            )
        elif sel_ex == "Autocall":
            st.markdown("""
**Autocallable Note:**
- At each observation date, if $S_{t_i} \\geq B_{auto}$: product redeems with coupon.
- At maturity, if $S_T < B_{put}$: investor bears downside loss.
- Priced via MC with discrete barrier monitoring.
            """)
        else:  # Himalaya
            st.markdown("""
**Himalaya Option:**
- N underlyings observed at N dates.
- At each date, the best performer is locked in and removed.
- Payoff = average of locked returns.
- Highly path-dependent → Monte Carlo only.
            """)

# ═══════════════════════════════════════════════════════════════
#  TAB 3 — Probability Bible  (from probability_bible_page.py)
# ═══════════════════════════════════════════════════════════════
with tab_pb:
    pb_tabs = st.tabs([
        "L3 Foundations", "M2 Stochastic", "PhD Advanced", "Interactive Lab"
    ])

    # --- L3 Foundations ---
    with pb_tabs[0]:
        st.markdown("### Undergraduate Foundations")
        for title, content, formulas, note in [
            ("Kolmogorov Axioms",
             "Probability space $(\\Omega, \\mathcal{F}, P)$:",
             [r"P(\Omega)=1", r"P(A)\geq 0",
              r"P\!\left(\bigcup A_i\right)=\sum P(A_i)\ \text{(disjoint)}"], ""),
            ("Bayes' Theorem",
             "Update beliefs given evidence:",
             [r"P(A|B) = \frac{P(B|A)P(A)}{P(B)}"],
             "Finance: update PD given CDS spread change"),
            ("Log-Normal Stock Prices",
             "Black-Scholes assumes log-normal:",
             [r"S_T = S_0\exp\!\left(\!\left(\mu-\tfrac{\sigma^2}{2}\right)T "
              r"+ \sigma\sqrt{T}Z\right), \quad Z\sim\mathcal{N}(0,1)"],
             "Consequence: returns are normal, prices are log-normal → always positive"),
            ("Central Limit Theorem",
             "Foundation of Monte Carlo:",
             [r"\frac{\bar{X}_n - \mu}{\sigma/\sqrt{n}} "
              r"\xrightarrow{d} \mathcal{N}(0,1)"],
             "MC standard error = σ/√N → 4× simulations needed to halve error"),
        ]:
            with st.expander(title):
                st.markdown(content)
                for f in formulas:
                    st.latex(f)
                if note:
                    st.info(note)

    # --- M2 Stochastic ---
    with pb_tabs[1]:
        st.markdown("### Master Level — Stochastic Calculus")
        with st.expander("Brownian Motion $W_t$"):
            st.latex(r"W_0=0,\quad W_t-W_s\sim\mathcal{N}(0,t-s),\quad \langle W\rangle_t = t")
            st.markdown(
                "Paths are **continuous but nowhere differentiable**. "
                "Quadratic variation is finite: $d\\langle W\\rangle_t = dt$."
            )
        with st.expander("Itô's Lemma"):
            st.latex(r"df(t,X_t) = \frac{\partial f}{\partial t}dt + "
                     r"\frac{\partial f}{\partial x}dX_t + "
                     r"\frac{1}{2}\frac{\partial^2 f}{\partial x^2}d\langle X\rangle_t")
            st.markdown(
                "The **Itô correction** $\\frac{1}{2}\\sigma^2 f''$ is the source "
                "of the BSM PDE and all second-order Greeks."
            )
        with st.expander("Girsanov — Change to Risk-Neutral Measure"):
            st.latex(r"\frac{dQ}{dP} = \mathcal{E}\!\left(-\int_0^T\theta_s\,dW_s\right), "
                     r"\quad \theta_t = \frac{\mu - r}{\sigma}")
            st.markdown(
                "Under Q, **all assets grow at r** and the discounted price is a "
                "martingale → no-arbitrage pricing."
            )
        with st.expander("Martingale Pricing"):
            st.latex(r"V_0 = e^{-rT}\,\mathbb{E}^Q[\text{Payoff}(S_T)]")
            st.markdown(
                "Every derivative price is a **conditional expectation** under Q. "
                "Monte Carlo computes this by averaging simulated payoffs."
            )

    # --- PhD Advanced ---
    with pb_tabs[2]:
        st.markdown("### PhD Level")
        with st.expander("Malliavin Calculus — Greeks Without Finite Differences"):
            st.latex(r"\Delta = \mathbb{E}^Q\!\left[\text{Payoff}(S_T)"
                     r"\cdot\frac{W_T}{\sigma S_0 T}\right]")
            st.markdown(
                "The **Clark-Ocone representation** gives Greeks as expectations "
                "— no numerical differentiation bias."
            )
        with st.expander("Lévy Processes — Jump Diffusion (Merton 1976)"):
            st.latex(r"dS_t = \mu S_t dt + \sigma S_t dW_t + S_{t^-}(e^J-1)dN_t, "
                     r"\quad N_t\sim\text{Poisson}(\lambda)")
            st.latex(r"C_{Merton} = \sum_{n=0}^\infty "
                     r"\frac{e^{-\lambda T}(\lambda T)^n}{n!}"
                     r"C_{BS}(S,K,T,r_n,\sigma_n)")
        with st.expander("First & Second Fundamental Theorems"):
            st.markdown(
                "**FT1:** No-arbitrage $\\Leftrightarrow$ $\\exists$ "
                "equivalent martingale measure Q"
            )
            st.markdown(
                "**FT2:** Completeness $\\Leftrightarrow$ Q is **unique**"
            )
            st.markdown(
                "Stochastic vol models (Heston, SABR) are **incomplete** → "
                "range of arbitrage-free prices. Calibration selects one."
            )

    # --- Interactive Lab ---
    with pb_tabs[3]:
        st.markdown("### Interactive Probability Lab")
        lab = st.selectbox("Experiment", [
            "Distribution Explorer", "CLT Simulator",
            "Brownian Paths", "Fat Tails vs Normal"
        ], key="mf_lab")

        if lab == "Distribution Explorer":
            d_type = st.selectbox(
                "Distribution", ["Normal", "Log-Normal", "Student-t", "Poisson"],
                key="mf_dist"
            )
            c1, c2 = st.columns(2)
            if d_type == "Normal":
                from scipy.stats import norm as sp_norm
                with c1: mu_d = st.slider("μ", -3.0, 3.0, 0.0, 0.1, key="mf_mu")
                with c2: sig_d = st.slider("σ", 0.1, 3.0, 1.0, 0.1, key="mf_sig")
                x = np.linspace(-8, 8, 500)
                y = sp_norm.pdf(x, mu_d, sig_d)
            elif d_type == "Student-t":
                from scipy.stats import t as sp_t
                with c1: nu = st.slider("ν (dof)", 2, 30, 5, 1, key="mf_nu")
                x = np.linspace(-6, 6, 500)
                y = sp_t.pdf(x, nu)
            elif d_type == "Log-Normal":
                from scipy.stats import lognorm as sp_ln
                with c1: lmu = st.slider("μ_log", -1.0, 1.0, 0.0, 0.1, key="mf_lmu")
                with c2: lsig = st.slider("σ_log", 0.1, 1.5, 0.4, 0.1, key="mf_lsig")
                x = np.linspace(0.01, 8, 500)
                y = sp_ln.pdf(x, lsig, scale=np.exp(lmu))
            else:  # Poisson
                from scipy.stats import poisson as sp_pois
                with c1: lam_p = st.slider("λ", 0.5, 10.0, 3.0, 0.5, key="mf_lam")
                x = np.arange(0, 20)
                y = sp_pois.pmf(x, lam_p)

            fig = go.Figure(go.Scatter(
                x=x, y=y, fill="tozeroy", mode="lines",
                line=dict(color="#6366f1", width=2),
                fillcolor="rgba(99,102,241,0.1)"
            ))
            fig.update_layout(**_BASE_LAYOUT, height=320,
                              margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

        elif lab == "CLT Simulator":
            n_clt = st.slider("Sample Size N", 1, 500, 30, 5, key="mf_clt_n")
            reps = st.slider("Repetitions", 100, 5000, 1000, 100, key="mf_clt_r")
            dist_c = st.selectbox(
                "Population Distribution",
                ["Uniform", "Exponential", "Bernoulli(p=0.3)", "Chi-squared(k=2)"],
                key="mf_clt_d"
            )
            rng = np.random.default_rng(42)
            if "Uniform" in dist_c:
                pop = rng.uniform(0, 1, (reps, n_clt))
            elif "Exponential" in dist_c:
                pop = rng.exponential(1.0, (reps, n_clt))
            elif "Bernoulli" in dist_c:
                pop = rng.binomial(1, 0.3, (reps, n_clt))
            else:
                pop = rng.chisquare(2, (reps, n_clt))
            means = pop.mean(axis=1)

            from scipy.stats import norm as sp_norm_clt
            m_fit, s_fit = means.mean(), means.std()
            x_f = np.linspace(means.min(), means.max(), 200)

            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=means, nbinsx=50, histnorm="probability density",
                marker_color="#6366f1", opacity=0.75, name="Sample Means"
            ))
            fig.add_trace(go.Scatter(
                x=x_f, y=sp_norm_clt.pdf(x_f, m_fit, s_fit),
                mode="lines", line=dict(color="#f59e0b", width=2),
                name="Normal Fit"
            ))
            fig.update_layout(**_BASE_LAYOUT, height=350,
                              margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"N={n_clt}: Skewness={float(pd.Series(means).skew()):.3f}, "
                f"Kurtosis={float(pd.Series(means).kurtosis()):.3f} "
                "→ approaches Normal as N→∞"
            )

        elif lab == "Brownian Paths":
            n_p = st.slider("Paths", 1, 50, 10, key="mf_bm_n")
            T_b = st.slider("Days", 30, 504, 252, key="mf_bm_T")
            sig_b = st.slider("Annual Vol (%)", 5, 80, 20, key="mf_bm_vol") / 100
            dr_b = st.slider("Annual Drift (%)", -30, 50, 5, key="mf_bm_dr") / 100
            dt_b = 1 / 252
            rng = np.random.default_rng()
            Z_b = rng.standard_normal((T_b, n_p))
            paths = np.exp(np.cumsum(
                (dr_b - 0.5 * sig_b**2) * dt_b + sig_b * np.sqrt(dt_b) * Z_b,
                axis=0
            )) * 100

            fig = go.Figure()
            for j in range(n_p):
                fig.add_trace(go.Scatter(
                    y=paths[:, j], mode="lines",
                    line=dict(width=1), opacity=0.65, showlegend=False
                ))
            fig.add_hline(y=100, line_dash="dash",
                          line_color="rgba(255,255,255,0.2)")
            fig.update_layout(
                **_BASE_LAYOUT, height=380,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(title="S_t (S₀=100)", gridcolor=_GRID),
                xaxis=dict(title="Days", gridcolor=_GRID),
            )
            st.plotly_chart(fig, use_container_width=True)

        else:  # Fat Tails vs Normal
            from scipy.stats import t as sp_t_ft
            nu_ft = st.slider("Student-t degrees of freedom ν", 2, 30, 4, key="mf_ft_nu")
            rng = np.random.default_rng(0)
            t_d = rng.standard_t(nu_ft, 50_000)
            n_d = rng.standard_normal(50_000)

            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=np.clip(t_d, -6, 6), nbinsx=120,
                histnorm="probability density",
                marker_color="#ef4444", opacity=0.5,
                name=f"Student-t (ν={nu_ft})"
            ))
            fig.add_trace(go.Histogram(
                x=np.clip(n_d, -6, 6), nbinsx=120,
                histnorm="probability density",
                marker_color="#6366f1", opacity=0.4,
                name="Normal"
            ))
            fig.update_layout(
                **_BASE_LAYOUT, height=350, barmode="overlay",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, use_container_width=True)
            exc = float(np.mean(np.abs(t_d) > 3))
            st.metric("P(|X| > 3)", f"{exc:.2%}",
                      delta=f"vs Normal {0.0027:.2%}", delta_color="inverse")
