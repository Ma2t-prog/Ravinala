"""
Information-theoretic measures for financial markets.

Entropy = uncertainty or complexity of a system.
Higher entropy = more unpredictable = harder to profit from.

Shannon entropy: overall unpredictability of returns
Sample entropy (SampEn): time-series complexity / regularity
Transfer entropy: directed information flow between assets (who leads whom?)
Permutation entropy: order-pattern complexity

Reference: Shannon (1948), Richman & Moorman (2000), Schreiber (2000)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from itertools import permutations
from typing import Optional


class EntropyAnalyzer:
    """Information-theoretic analysis of financial time series."""

    def shannon_entropy(self, returns: np.ndarray, n_bins: int = 50) -> dict:
        """
        Shannon entropy of the return distribution.

        H = -Σ p_i × log₂(p_i)

        Returns:
            {
                'entropy_bits': float,
                'max_possible_entropy': float,
                'normalized_entropy': float,
                'normal_entropy': float,
                'excess_entropy': float,
                'interpretation': str,
            }
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        returns = np.asarray(returns, dtype=float)
        returns = returns[np.isfinite(returns)]

        counts, _ = np.histogram(returns, bins=n_bins)
        probs = counts / counts.sum()
        probs = probs[probs > 0]

        H = float(-np.sum(probs * np.log2(probs)))
        H_max = float(np.log2(n_bins))
        H_norm = H / H_max

        # Gaussian reference entropy (in bits): ½log₂(2πeσ²)
        sigma = float(np.std(returns))
        H_normal = float(0.5 * np.log2(2 * np.pi * np.e * sigma**2)) if sigma > 0 else 0.0

        excess = H - H_normal

        if H_norm < 0.6:
            interp = "Low entropy — return distribution shows strong concentration (predictable patterns may exist)."
        elif H_norm < 0.8:
            interp = "Moderate entropy — near-normal distribution."
        else:
            interp = "High entropy — returns are broadly distributed and highly unpredictable."

        return {
            "entropy_bits": H,
            "max_possible_entropy": H_max,
            "normalized_entropy": float(H_norm),
            "normal_entropy": H_normal,
            "excess_entropy": float(excess),
            "interpretation": interp,
        }

    def sample_entropy(
        self,
        series: np.ndarray,
        m: int = 2,
        r: Optional[float] = None,
    ) -> dict:
        """
        Sample Entropy (SampEn) — measures time series complexity.

        Lower SampEn = more regular/predictable.
        Higher SampEn = more complex/random.

        Args:
            m: embedding dimension (2 is standard)
            r: tolerance (default: 0.2 × std of series)
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        series = series[np.isfinite(series)]
        N = len(series)

        if r is None:
            r = 0.2 * float(np.std(series))

        def _count_matches(template_len: int) -> int:
            count = 0
            for i in range(N - template_len):
                template = series[i : i + template_len]
                for j in range(i + 1, N - template_len):
                    if np.max(np.abs(series[j : j + template_len] - template)) <= r:
                        count += 1
            return count

        B = _count_matches(m)
        A = _count_matches(m + 1)

        if B == 0:
            samp_en = np.nan
        else:
            samp_en = -np.log(A / B) if A > 0 else float("inf")

        if np.isnan(samp_en):
            interp = "Could not compute SampEn (no template matches)."
        elif samp_en < 0.5:
            interp = f"Low SampEn ({samp_en:.3f}) — series is highly regular/predictable."
        elif samp_en < 1.5:
            interp = f"Moderate SampEn ({samp_en:.3f}) — intermediate complexity."
        else:
            interp = f"High SampEn ({samp_en:.3f}) — series is complex and unpredictable."

        return {
            "sample_entropy": float(samp_en) if np.isfinite(samp_en) else None,
            "template_matches_m": B,
            "template_matches_m1": A,
            "tolerance_r": float(r),
            "interpretation": interp,
        }

    def permutation_entropy(
        self,
        series: np.ndarray,
        order: int = 3,
        delay: int = 1,
        normalize: bool = True,
    ) -> dict:
        """
        Permutation entropy — complexity from ordinal patterns.

        1. Extract all ordinal patterns of length `order`
        2. Count relative frequency of each pattern
        3. H_perm = -Σ p_i log p_i

        Fast, robust, suitable for non-stationary series.

        Lower H_perm = more regular/predictable.
        Higher H_perm = closer to random.
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        N = len(series)

        # Generate all possible permutations
        all_perms = list(permutations(range(order)))
        perm_index = {p: i for i, p in enumerate(all_perms)}
        counts = np.zeros(len(all_perms))

        for i in range(N - (order - 1) * delay):
            motif = tuple(
                np.argsort([series[i + j * delay] for j in range(order)])
            )
            counts[perm_index[motif]] += 1

        probs = counts / counts.sum()
        probs = probs[probs > 0]

        H = float(-np.sum(probs * np.log(probs)))
        H_max = float(np.log(len(all_perms)))

        H_norm = H / H_max if H_max > 0 else 0.0

        return {
            "permutation_entropy": H,
            "normalized_permutation_entropy": float(H_norm),
            "n_distinct_patterns": int(np.sum(counts > 0)),
            "n_possible_patterns": len(all_perms),
            "complexity_ci": float(H_norm * (1 - H_norm)),
            "interpretation": (
                f"Normalised H_perm = {H_norm:.3f}. "
                + (
                    "Low — strong ordinal structure, series is predictable."
                    if H_norm < 0.6
                    else "High — near-maximal complexity, close to random."
                    if H_norm > 0.9
                    else "Intermediate complexity."
                )
            ),
        }

    def transfer_entropy(
        self,
        source: np.ndarray,
        target: np.ndarray,
        lag: int = 1,
        n_bins: int = 10,
    ) -> dict:
        """
        Transfer entropy: T_{X→Y} measures information flow from X to Y.

        T_{X→Y} = H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-1})

        If T_{X→Y} > T_{Y→X}: X leads Y (X is the "cause").

        Returns:
            {
                'te_source_to_target': float,
                'te_target_to_source': float,
                'net_flow': float,
                'dominant_direction': str,
                'statistical_significance': float,
            }
        """
        if isinstance(source, pd.Series):
            source = source.values
        if isinstance(target, pd.Series):
            target = target.values

        source = np.asarray(source, dtype=float)
        target = np.asarray(target, dtype=float)

        # Discretise both series
        def _discretise(x: np.ndarray, bins: int) -> np.ndarray:
            edges = np.linspace(x.min() - 1e-10, x.max() + 1e-10, bins + 1)
            return np.digitize(x, edges) - 1

        s = _discretise(source, n_bins)
        t = _discretise(target, n_bins)

        def _te(x: np.ndarray, y: np.ndarray, k: int) -> float:
            """T_{X→Y}: info in X_{t-k} about Y_t beyond Y_{t-k}."""
            N = len(y) - k
            if N < 10:
                return 0.0

            y_t = y[k:]
            y_lag = y[:N]
            x_lag = x[:N]

            # Joint and marginal counts
            def joint_prob(*arrays):
                shape = tuple(n_bins for _ in arrays)
                counts = np.zeros(shape)
                for idx in zip(*arrays):
                    if all(0 <= v < n_bins for v in idx):
                        counts[idx] += 1
                return counts / max(counts.sum(), 1e-300)

            p_yt_ylag = joint_prob(y_t, y_lag)
            p_yt_ylag_xlag = joint_prob(y_t, y_lag, x_lag)
            p_ylag = np.sum(p_yt_ylag, axis=0)
            p_ylag_xlag = np.sum(p_yt_ylag_xlag, axis=0)

            te = 0.0
            for a in range(n_bins):
                for b in range(n_bins):
                    for c in range(n_bins):
                        p3 = p_yt_ylag_xlag[a, b, c]
                        p2_ylag = p_ylag[b] if p_ylag[b] > 0 else 1e-300
                        p2_lag = p_ylag_xlag[b, c] if p_ylag_xlag[b, c] > 0 else 1e-300
                        p2_yt = p_yt_ylag[a, b] if p_yt_ylag[a, b] > 0 else 1e-300
                        if p3 > 0:
                            te += p3 * np.log(p3 * p2_ylag / (p2_lag * p2_yt))

            return max(float(te), 0.0)

        te_s2t = _te(s, t, lag)
        te_t2s = _te(t, s, lag)
        net_flow = te_s2t - te_t2s

        # Shuffle test for significance
        n_surr = 50
        null_dist = []
        rng = np.random.default_rng(42)
        for _ in range(n_surr):
            s_shuf = rng.permutation(s)
            null_dist.append(_te(s_shuf, t, lag))
        null_arr = np.array(null_dist)
        p_value = float(np.mean(null_arr >= te_s2t))

        return {
            "te_source_to_target": te_s2t,
            "te_target_to_source": te_t2s,
            "net_flow": net_flow,
            "dominant_direction": (
                "source_leads" if net_flow > 0.01
                else "target_leads" if net_flow < -0.01
                else "bidirectional"
            ),
            "statistical_significance_pvalue": p_value,
            "significant_at_5pct": p_value < 0.05,
        }

    def entropy_over_time(
        self, series: np.ndarray, window: int = 60
    ) -> pd.Series:
        """
        Rolling sample entropy (permutation entropy for speed).

        Useful for detecting:
        - Entropy drops before crashes (market becomes "too ordered")
        - Entropy spikes after shocks
        - Regime changes (entropy level shifts)
        """
        if isinstance(series, pd.Series):
            idx = series.index
            series = series.values
        else:
            idx = None

        N = len(series)
        entropies = np.full(N, np.nan)

        for i in range(window, N + 1):
            chunk = series[i - window : i]
            result = self.permutation_entropy(chunk, order=3, normalize=True)
            entropies[i - 1] = result["normalized_permutation_entropy"]

        if idx is not None:
            return pd.Series(entropies, index=idx, name="rolling_permutation_entropy")
        return pd.Series(entropies, name="rolling_permutation_entropy")

    def market_complexity_score(self, returns_df: pd.DataFrame) -> dict:
        """
        Composite complexity score for the overall market (0–100).

        Combines:
        1. Average permutation entropy of individual assets
        2. Eigenvalue entropy of correlation matrix (market structure)
        3. Average volatility normalised to recent history

        Score interpretation:
        0–30:  Low complexity (calm, trending, predictable)
        30–60: Normal complexity
        60–80: High complexity (volatile, uncertain)
        80–100: Extreme complexity (crisis, regime break)
        """
        scores = {}

        # 1. Individual permutation entropies
        ind_entropies = []
        for col in returns_df.columns:
            arr = returns_df[col].dropna().values
            if len(arr) >= 10:
                pe = self.permutation_entropy(arr, order=3, normalize=True)
                ind_entropies.append(pe["normalized_permutation_entropy"])
        avg_pe = float(np.mean(ind_entropies)) if ind_entropies else 0.5
        scores["individual_entropy"] = avg_pe

        # 2. Eigenvalue entropy of correlation matrix
        corr = returns_df.corr().values
        eigenvalues = np.linalg.eigvalsh(corr)
        eigenvalues = eigenvalues[eigenvalues > 0]
        eig_probs = eigenvalues / eigenvalues.sum()
        eig_entropy = float(-np.sum(eig_probs * np.log(eig_probs))) / np.log(len(eigenvalues))
        scores["eigenvalue_entropy"] = eig_entropy

        # 3. Vol ratio (recent 20d vs. full period)
        recent_vol = returns_df.tail(20).std().mean()
        full_vol = returns_df.std().mean()
        vol_ratio = float(recent_vol / (full_vol + 1e-8))
        scores["vol_ratio"] = float(min(vol_ratio, 3.0) / 3.0)

        # Composite score
        composite = 100 * (0.4 * avg_pe + 0.4 * eig_entropy + 0.2 * scores["vol_ratio"])

        if composite < 30:
            regime = "Low complexity — calm market, trending conditions."
        elif composite < 60:
            regime = "Normal complexity."
        elif composite < 80:
            regime = "High complexity — volatile and uncertain."
        else:
            regime = "Extreme complexity — potential crisis or regime break."

        return {
            "complexity_score": float(composite),
            "components": scores,
            "regime": regime,
        }
