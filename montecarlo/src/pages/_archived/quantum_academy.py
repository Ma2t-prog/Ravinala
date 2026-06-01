import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st

_render_page_header("QA", "The Quantum Academy", "Mathematical foundations of pricing, risk and structuring models", "Theory")

acad_tabs = st.tabs(["BSM Foundations", "Greeks Library", "Numerical Methods", "Exotic Mechanics"])

with acad_tabs[0]:
    st.markdown("### The Black-Scholes-Merton PDE")
    st.latex(r"\frac{\partial V}{\partial t} + (r-q)S\frac{\partial V}{\partial S} + \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")
    st.markdown("Under the risk-neutral measure Q, the underlying follows:")
    st.latex(r"dS_t = (r-q)S_t\,dt + \sigma S_t\,dW_t^Q")
    st.markdown("**Closed-form solution — European Call:**")
    st.latex(r"C = Se^{-qT}N(d_1) - Ke^{-rT}N(d_2)")
    st.latex(r"d_1 = \frac{\ln(S/K) + (r - q + \frac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}")
    st.markdown("**Model Assumptions and their limits:**")
    for assumption, reality in {
        "Constant volatility": "Reality: Implied vol varies with strike (smile) → SABR, Heston, SVI",
        "No jumps": "Reality: Overnight gaps → Merton Jump-Diffusion, Variance Gamma",
        "Continuous hedging": "Reality: Discrete rebalancing → residual Gamma P&L",
        "Log-normal returns": "Reality: Fat tails (kurtosis ≈ 4-6) → Lévy processes",
        "No transaction costs": "Reality: Bid-ask spreads → Deep Hedging (Reinforcement Learning)",
    }.items():
        with st.expander(f"{assumption}"):
            st.write(reality)

with acad_tabs[1]:
    st.markdown("### Greeks Reference Library")
    greek_ref = {
        "Delta (Δ)": (r"\Delta_{call} = e^{-qT} N(d_1)", "Price move per €1 spot. Hedge: hold -Δ shares."),
        "Gamma (Γ)": (r"\Gamma = \frac{e^{-qT} N'(d_1)}{S\sigma\sqrt{T}}", "Rate of Delta change. Long Γ = profits from large moves. Peaks ATM near expiry."),
        "Vega (ν)": (r"\nu = Se^{-qT}\sqrt{T}\,N'(d_1)/100", "Price change per 1% vol move. Always positive for long options."),
        "Theta (Θ)": (r"\Theta = \frac{-Se^{-qT}N'(d_1)\sigma}{2\sqrt{T}} - rKe^{-rT}N(d_2)", "Daily time decay. Theta = -Gamma·S²σ²/2 (BSM identity)."),
        "Vanna": (r"\text{Vanna} = -e^{-qT}N'(d_1)\frac{d_2}{\sigma}", "How Delta changes with vol. Critical for crash hedging."),
        "Volga (Vomma)": (r"\text{Volga} = Se^{-qT}\sqrt{T}\,N'(d_1)\frac{d_1 d_2}{\sigma}", "Vol-of-vol risk. Highest for OTM options."),
        "Charm": (r"\text{Charm} = -e^{-qT}\left[N'(d_1)\frac{2(r-q)T - d_2\sigma\sqrt{T}}{2T\sigma\sqrt{T}}\right]", "Daily Delta decay — how delta changes overnight."),
    }
    sel_g = st.selectbox("Select Greek", list(greek_ref.keys()), key="acad_g")
    formula, interp = greek_ref[sel_g]
    st.latex(formula)
    st.info(f"**Interpretation:** {interp}")

with acad_tabs[2]:
    st.markdown("### Numerical Methods")
    nt = st.tabs(["Monte Carlo", "Finite Differences", "SABR Calibration"])
    with nt[0]:
        st.latex(r"C_0 = e^{-rT} \mathbb{E}^Q\!\left[\max(S_T - K, 0)\right] \approx e^{-rT}\frac{1}{N}\sum_{i=1}^N (S_T^{(i)}-K)^+")
        st.markdown("**Standard Error:**")
        st.latex(r"SE = \frac{\hat{\sigma}}{\sqrt{N}} \implies \text{halving SE requires } 4\times \text{ more paths}")
        st.markdown("**Antithetic Variates (Ravinala uses this):**")
        st.latex(r"\hat{C}_{AV} = \frac{f(Z) + f(-Z)}{2} \quad \Rightarrow \quad \text{Var}[\hat{C}_{AV}] \leq \text{Var}[\hat{C}]")
    with nt[1]:
        st.markdown("**Crank-Nicolson scheme** — 2nd order accurate, unconditionally stable:")
        st.latex(r"\frac{V^{n+1}_i - V^n_i}{\Delta t} = \frac{1}{2}\left(\mathcal{L}V^n_i + \mathcal{L}V^{n+1}_i\right)")
        st.markdown("where $\\mathcal{L}$ is the Black-Scholes spatial operator applied at grid point $i$.")
    with nt[2]:
        st.markdown("**SABR stochastic volatility model:**")
        st.latex(r"dF = \sigma F^\beta dW_1, \quad d\sigma = \nu\sigma dW_2, \quad \langle dW_1, dW_2 \rangle = \rho\,dt")
        st.markdown("""
| α | β | ρ | ν |
|---|---|---|---|
| Vol level | Backbone (0=normal, 1=lognormal) | Skew (neg for equity) | Smile curvature |
""")

with acad_tabs[3]:
    st.markdown("### Exotic Payoff Mechanics")
    sel_ex = st.selectbox("Select", ["Barrier","Asian","Autocall","Himalaya"], key="sel_ex")
    if sel_ex == "Barrier":
        st.latex(r"V_{DI}(T) = (S_T - K)^+ \cdot \mathbf{1}_{\{\min_{t} S_t > B\}}")
        st.markdown("**Gap Risk:** Stock can jump below barrier overnight — cannot hedge continuously. Priced via Monte Carlo with small Δt.")
    elif sel_ex == "Asian":
        st.latex(r"V_{Asian}(T) = \left(\frac{1}{N}\sum_{i=1}^N S_{t_i} - K\right)^+")
        st.markdown("**Property:** Averaging reduces variance → cheaper than vanilla. Used in FX/Commodities to reduce fixing risk.")
    elif sel_ex == "Autocall":
        st.latex(r"\text{Payoff}_{t_i} = \begin{cases}100(1+c\cdot i) & S_{t_i}\geq K_{call}\\ \text{Continue} & B<S_{t_i}<K_{call}\\ 100\cdot S_T/S_0 & S_T \leq B\end{cases}")
        st.markdown("**Delta Profile:** Negative delta near autocall trigger (digital risk). Requires careful gamma/digital hedging.")
    else:
        st.latex(r"\text{Payoff}_{Himalaya} = \frac{1}{n}\sum_{k=1}^n \max_{j\notin\text{removed}}\frac{S_j(t_k)}{S_j(0)}")
        st.markdown("**Key Risk:** Correlation risk dominates. As correlation rises, diversification benefit vanishes. Require C-Delta hedging.")
