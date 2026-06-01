import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

_render_page_header("PB", "The Probability Bible", "From combinatorics to stochastic calculus — the language of risk", "Probability")

pb_tabs = st.tabs(["L3 Foundations", "M2 Stochastic", "PhD Advanced", "Interactive Lab"])

with pb_tabs[0]:
    st.markdown("### Undergraduate Foundations")
    for title, content, formulas, note in [
        ("Kolmogorov Axioms", "Probability space $(\\Omega, \\mathcal{F}, P)$:",
         [r"P(\Omega)=1", r"P(A)\geq 0", r"P\!\left(\bigcup A_i\right)=\sum P(A_i)\ \text{(disjoint)}"], ""),
        ("Bayes' Theorem", "Update beliefs given evidence:",
         [r"P(A|B) = \frac{P(B|A)P(A)}{P(B)}"],
         "Finance: update PD given CDS spread change"),
        ("Log-Normal Stock Prices", "Black-Scholes assumes log-normal:",
         [r"S_T = S_0\exp\!\left(\!\left(\mu-\tfrac{\sigma^2}{2}\right)T + \sigma\sqrt{T}Z\right), \quad Z\sim\mathcal{N}(0,1)"],
         "Consequence: returns are normal, prices are log-normal → always positive"),
        ("Central Limit Theorem", "Foundation of Monte Carlo:",
         [r"\frac{\bar{X}_n - \mu}{\sigma/\sqrt{n}} \xrightarrow{d} \mathcal{N}(0,1)"],
         "MC standard error = σ/√N → 4× simulations needed to halve error"),
    ]:
        with st.expander(f"{title}"):
            st.markdown(content)
            for f in formulas:
                st.latex(f)
            if note:
                st.info(note)

with pb_tabs[1]:
    st.markdown("### Master Level — Stochastic Calculus")
    with st.expander("Brownian Motion $W_t$"):
        st.latex(r"W_0=0,\quad W_t-W_s\sim\mathcal{N}(0,t-s),\quad \langle W\rangle_t = t")
        st.markdown("Paths are **continuous but nowhere differentiable**. Quadratic variation is finite: $d\\langle W\\rangle_t = dt$.")
    with st.expander("Itô's Lemma"):
        st.latex(r"df(t,X_t) = \frac{\partial f}{\partial t}dt + \frac{\partial f}{\partial x}dX_t + \frac{1}{2}\frac{\partial^2 f}{\partial x^2}d\langle X\rangle_t")
        st.markdown("The **Itô correction** $\\frac{1}{2}\\sigma^2 f''$ is the source of the BSM PDE and all second-order Greeks.")
    with st.expander("Girsanov — Change to Risk-Neutral Measure"):
        st.latex(r"\frac{dQ}{dP} = \mathcal{E}\!\left(-\int_0^T\theta_s\,dW_s\right), \quad \theta_t = \frac{\mu - r}{\sigma}")
        st.markdown("Under Q, **all assets grow at r** and the discounted price is a martingale → no-arbitrage pricing.")
    with st.expander("Martingale Pricing"):
        st.latex(r"V_0 = e^{-rT}\,\mathbb{E}^Q[\text{Payoff}(S_T)]")
        st.markdown("Every derivative price is a **conditional expectation** under Q. Monte Carlo computes this by averaging simulated payoffs.")

with pb_tabs[2]:
    st.markdown("### PhD Level")
    with st.expander("Malliavin Calculus — Greeks Without Finite Differences"):
        st.latex(r"\Delta = \mathbb{E}^Q\!\left[\text{Payoff}(S_T)\cdot\frac{W_T}{\sigma S_0 T}\right]")
        st.markdown("The **Clark-Ocone representation** gives Greeks as expectations — no numerical differentiation bias.")
    with st.expander("Lévy Processes — Jump Diffusion (Merton 1976)"):
        st.latex(r"dS_t = \mu S_t dt + \sigma S_t dW_t + S_{t^-}(e^J-1)dN_t, \quad N_t\sim\text{Poisson}(\lambda)")
        st.latex(r"C_{Merton} = \sum_{n=0}^\infty \frac{e^{-\lambda T}(\lambda T)^n}{n!}C_{BS}(S,K,T,r_n,\sigma_n)")
    with st.expander("First & Second Fundamental Theorems"):
        st.markdown("**FT1:** No-arbitrage $\\Leftrightarrow$ $\\exists$ equivalent martingale measure Q")
        st.markdown("**FT2:** Completeness $\\Leftrightarrow$ Q is **unique**")
        st.markdown("Stochastic vol models (Heston, SABR) are **incomplete** → range of arbitrage-free prices. Calibration selects one.")

with pb_tabs[3]:
    st.markdown("### Interactive Probability Lab")
    lab = st.selectbox("Experiment", [
        "Distribution Explorer", "CLT Simulator",
        "Brownian Paths", "Fat Tails vs Normal"
    ], key="pb_lab")

    if lab == "Distribution Explorer":
        d_type = st.selectbox("Distribution", ["Normal","Log-Normal","Student-t","Poisson"], key="pb_dist")
        c1, c2 = st.columns(2)
        if d_type == "Normal":
            from scipy.stats import norm as sp_norm
            with c1: mu_d = st.slider("μ", -3.0, 3.0, 0.0, 0.1, key="pb_mu")
            with c2: sig_d = st.slider("σ", 0.1, 3.0, 1.0, 0.1, key="pb_sig")
            x = np.linspace(-8, 8, 500)
            y = sp_norm.pdf(x, mu_d, sig_d)
        elif d_type == "Student-t":
            with c1: nu = st.slider("ν (dof)", 2, 30, 5, 1, key="pb_nu")
            from scipy.stats import t as sp_t2
            x = np.linspace(-6, 6, 500)
            y = sp_t2.pdf(x, nu)
        elif d_type == "Log-Normal":
            with c1: lmu = st.slider("μ_log", -1.0, 1.0, 0.0, 0.1, key="pb_lmu")
            with c2: lsig = st.slider("σ_log", 0.1, 1.5, 0.4, 0.1, key="pb_lsig")
            from scipy.stats import lognorm as sp_ln2
            x = np.linspace(0.01, 8, 500)
            y = sp_ln2.pdf(x, lsig, scale=np.exp(lmu))
        else:
            with c1: lam_p = st.slider("λ", 0.5, 10.0, 3.0, 0.5, key="pb_lam")
            from scipy.stats import poisson as sp_pois2
            x = np.arange(0, 20)
            y = sp_pois2.pmf(x, lam_p)
        fig_pb = go.Figure(go.Scatter(x=x, y=y, fill="tozeroy", mode="lines",
                                       line=dict(color="#6366f1", width=2), fillcolor="rgba(99,102,241,0.1)"))
        fig_pb.update_layout(paper_bgcolor="#0A0A0F", plot_bgcolor="#0A0A0F",
                              font=dict(color="#9ca3af"), height=320, margin=dict(l=0,r=0,t=10,b=0),
                              xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                              yaxis=dict(gridcolor="rgba(255,255,255,0.04)"))
        st.plotly_chart(fig_pb, width="stretch")

    elif lab == "CLT Simulator":
        n_clt = st.slider("Sample Size N", 1, 500, 30, 5, key="clt_n")
        reps  = st.slider("Repetitions", 100, 5000, 1000, 100, key="clt_r")
        dist_c = st.selectbox("Population Distribution", ["Uniform","Exponential","Bernoulli(p=0.3)","Chi-squared(k=2)"], key="clt_d")
        if "Uniform" in dist_c:
            pop = np.random.uniform(0, 1, (reps, n_clt))
        elif "Exponential" in dist_c:
            pop = np.random.exponential(1.0, (reps, n_clt))
        elif "Bernoulli" in dist_c:
            pop = np.random.binomial(1, 0.3, (reps, n_clt))
        else:
            pop = np.random.chisquare(2, (reps, n_clt))
        means = pop.mean(axis=1)
        fig_clt = go.Figure()
        fig_clt.add_trace(go.Histogram(x=means, nbinsx=50, histnorm="probability density",
                                        marker_color="#6366f1", opacity=0.75, name="Sample Means"))
        from scipy.stats import norm as sp_norm
        m_fit, s_fit = means.mean(), means.std()
        x_f = np.linspace(means.min(), means.max(), 200)
        fig_clt.add_trace(go.Scatter(x=x_f, y=sp_norm.pdf(x_f, m_fit, s_fit), mode="lines",
                                      line=dict(color="#f59e0b", width=2), name="Normal Fit"))
        fig_clt.update_layout(paper_bgcolor="#0A0A0F", plot_bgcolor="#0A0A0F", font=dict(color="#9ca3af"),
                               height=350, margin=dict(l=0,r=0,t=10,b=0),
                               xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                               yaxis=dict(gridcolor="rgba(255,255,255,0.04)"))
        st.plotly_chart(fig_clt, width="stretch")
        st.caption(f"N={n_clt}: Skewness={float(pd.Series(means).skew()):.3f}, Kurtosis={float(pd.Series(means).kurtosis()):.3f} → approaches Normal as N→∞")

    elif lab == "Brownian Paths":
        n_p = st.slider("Paths", 1, 50, 10, key="bm_n")
        T_b = st.slider("Days", 30, 504, 252, key="bm_T")
        sig_b = st.slider("Annual Vol (%)", 5, 80, 20, key="bm_vol") / 100
        dr_b  = st.slider("Annual Drift (%)", -30, 50, 5, key="bm_dr") / 100
        dt_b  = 1/252
        Z_b   = np.random.standard_normal((T_b, n_p))
        paths = np.exp(np.cumsum((dr_b - 0.5*sig_b**2)*dt_b + sig_b*np.sqrt(dt_b)*Z_b, axis=0)) * 100
        fig_bm = go.Figure()
        for j in range(n_p):
            fig_bm.add_trace(go.Scatter(y=paths[:,j], mode="lines", line=dict(width=1), opacity=0.65, showlegend=False))
        fig_bm.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
        fig_bm.update_layout(paper_bgcolor="#0A0A0F", plot_bgcolor="#0A0A0F", font=dict(color="#9ca3af"),
                              height=380, margin=dict(l=0,r=0,t=10,b=0),
                              yaxis=dict(title="S_t (S₀=100)", gridcolor="rgba(255,255,255,0.04)"),
                              xaxis=dict(title="Days", gridcolor="rgba(255,255,255,0.04)"))
        st.plotly_chart(fig_bm, width="stretch")

    else:  # Fat Tails
        nu_ft = st.slider("Student-t degrees of freedom ν", 2, 30, 4, key="ft_nu")
        from scipy.stats import t as sp_t3
        t_d = np.random.standard_t(nu_ft, 50000)
        n_d = np.random.standard_normal(50000)
        fig_ft = go.Figure()
        fig_ft.add_trace(go.Histogram(x=np.clip(t_d,-6,6), nbinsx=120, histnorm="probability density",
                                       marker_color="#ef4444", opacity=0.6, name=f"t(ν={nu_ft})"))
        fig_ft.add_trace(go.Histogram(x=np.clip(n_d,-6,6), nbinsx=120, histnorm="probability density",
                                       marker_color="#6366f1", opacity=0.6, name="Normal"))
        fig_ft.update_layout(barmode="overlay", paper_bgcolor="#0A0A0F", plot_bgcolor="#0A0A0F",
                              font=dict(color="#9ca3af"), height=360, margin=dict(l=0,r=0,t=10,b=0),
                              xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                              yaxis=dict(gridcolor="rgba(255,255,255,0.04)"))
        st.plotly_chart(fig_ft, width="stretch")
        ek = float(pd.Series(t_d).kurtosis())
        st.metric("Excess Kurtosis of t-distribution", f"{ek:.2f}",
                  f"Normal=0. Fat tails = {ek:.1f}× more kurtosis → VaR underestimation if using Normal")
