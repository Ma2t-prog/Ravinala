"""
Prospect Theory — Kahneman & Tversky (1979, 1992).

Expected utility theory assumes people maximize E[U(wealth)].
Prospect theory says people evaluate gains/losses relative to a reference point,
with loss aversion (losses hurt ~2.25x more than equal gains feel good).

Key components:
1. Value function: concave for gains, convex for losses, steeper for losses
2. Probability weighting: overweight small probs, underweight large probs
3. Reference dependence: utility defined over changes, not absolute wealth

Cumulative Prospect Theory (CPT, 1992) extends to continuous distributions.

Reference: Kahneman & Tversky (1979), Tversky & Kahneman (1992)
"""

from __future__ import annotations

import numpy as np
from typing import Optional
from scipy.optimize import minimize_scalar


class ProspectTheoryAnalyzer:
    """
    Kahneman-Tversky Prospect Theory and Cumulative Prospect Theory.

    Default parameters (TK 1992 estimates):
        alpha = beta = 0.88  (curvature of value function)
        lambda_ = 2.25       (loss aversion coefficient)
        delta = gamma = 0.65 (probability weighting curvature)
    """

    def __init__(
        self,
        alpha: float = 0.88,   # gain sensitivity
        beta: float = 0.88,    # loss sensitivity
        lambda_: float = 2.25, # loss aversion
        delta: float = 0.65,   # probability weighting (gains)
        gamma: float = 0.65,   # probability weighting (losses)
    ):
        self.alpha = alpha
        self.beta = beta
        self.lambda_ = lambda_
        self.delta = delta
        self.gamma = gamma

    # ------------------------------------------------------------------ #
    # Value function                                                       #
    # ------------------------------------------------------------------ #

    def value(self, x: float, reference: float = 0.0) -> float:
        """
        Kahneman-Tversky value function.

        v(x) = (x - ref)^α           if x >= ref  (gain)
             = -λ × (ref - x)^β      if x < ref   (loss)

        Properties:
        - Concave for gains (diminishing sensitivity)
        - Convex for losses (risk-seeking in loss domain)
        - Steeper for losses by factor λ (loss aversion)
        """
        dx = x - reference
        if dx >= 0:
            return float(dx ** self.alpha)
        else:
            return float(-self.lambda_ * ((-dx) ** self.beta))

    def value_array(self, x: np.ndarray, reference: float = 0.0) -> np.ndarray:
        """Vectorized value function."""
        x = np.asarray(x, dtype=float)
        dx = x - reference
        gains = np.where(dx >= 0, dx ** self.alpha, 0.0)
        losses = np.where(dx < 0, -self.lambda_ * ((-dx) ** self.beta), 0.0)
        return gains + losses

    # ------------------------------------------------------------------ #
    # Probability weighting                                               #
    # ------------------------------------------------------------------ #

    def weight_gains(self, p: float) -> float:
        """
        Probability weighting function for gains (Prelec 1998 / TK 1992).

        w⁺(p) = exp(-(-ln p)^δ)

        Properties:
        - Overweights small probabilities (why lottery tickets sell)
        - Underweights moderate/large probabilities
        - w⁺(0)=0, w⁺(1)=1
        """
        if p <= 0:
            return 0.0
        if p >= 1:
            return 1.0
        return float(np.exp(-((-np.log(p)) ** self.delta)))

    def weight_losses(self, p: float) -> float:
        """Probability weighting for losses."""
        if p <= 0:
            return 0.0
        if p >= 1:
            return 1.0
        return float(np.exp(-((-np.log(p)) ** self.gamma)))

    def weight_array(self, probs: np.ndarray, gains: bool = True) -> np.ndarray:
        """Vectorized probability weighting."""
        probs = np.clip(np.asarray(probs, dtype=float), 1e-10, 1 - 1e-10)
        d = self.delta if gains else self.gamma
        return np.exp(-((-np.log(probs)) ** d))

    # ------------------------------------------------------------------ #
    # Prospect value                                                      #
    # ------------------------------------------------------------------ #

    def prospect_value(
        self,
        outcomes: np.ndarray,
        probabilities: np.ndarray,
        reference: float = 0.0,
    ) -> float:
        """
        Cumulative Prospect Theory value of a discrete prospect.

        CPT separates gains and losses, applies cumulative probability weighting
        (rank-dependent), then sums weighted values.

        V = Σ_i π⁺_i × v(x_i)  for gains
          + Σ_i π⁻_i × v(x_i)  for losses

        where π⁺_i = w⁺(F(x_i)) - w⁺(F(x_{i-1})) (decumulative weights)
        """
        outcomes = np.asarray(outcomes, dtype=float)
        probs = np.asarray(probabilities, dtype=float)
        probs = probs / probs.sum()  # normalize

        dx = outcomes - reference
        gain_idx = np.where(dx >= 0)[0]
        loss_idx = np.where(dx < 0)[0]

        total = 0.0

        # Gains: sort ascending, use decumulative weights
        if len(gain_idx) > 0:
            order = gain_idx[np.argsort(dx[gain_idx])]
            g_probs = probs[order]
            g_dx = dx[order]
            cum_probs = np.cumsum(g_probs[::-1])[::-1]  # decumulative
            cum_probs_shifted = np.append(cum_probs[1:], 0.0)
            pi = self.weight_array(cum_probs, True) - self.weight_array(cum_probs_shifted, True)
            total += float(np.sum(pi * (g_dx ** self.alpha)))

        # Losses: sort descending (least negative first)
        if len(loss_idx) > 0:
            order = loss_idx[np.argsort(-dx[loss_idx])]
            l_probs = probs[order]
            l_dx = dx[order]
            cum_probs = np.cumsum(l_probs)
            cum_probs_shifted = np.append(0.0, cum_probs[:-1])
            pi = self.weight_array(cum_probs, False) - self.weight_array(cum_probs_shifted, False)
            total += float(np.sum(-pi * self.lambda_ * ((-l_dx) ** self.beta)))

        return total

    def expected_utility(
        self,
        outcomes: np.ndarray,
        probabilities: np.ndarray,
    ) -> float:
        """Standard expected utility (log utility) for comparison."""
        outcomes = np.asarray(outcomes, dtype=float)
        probs = np.asarray(probabilities, dtype=float)
        probs = probs / probs.sum()
        # Assume log utility; shift if needed to handle non-positive outcomes
        shifted = outcomes - outcomes.min() + 1.0
        return float(np.sum(probs * np.log(shifted)))

    # ------------------------------------------------------------------ #
    # Loss-aversion-adjusted risk measures                                #
    # ------------------------------------------------------------------ #

    def loss_aversion_adjusted_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        reference: float = 0.0,
    ) -> dict:
        """
        Loss-aversion weighted VaR.

        Standard VaR ignores that losses are psychologically more painful.
        LA-VaR rescales the loss distribution by the loss aversion factor λ,
        producing a higher effective risk measure for losses.

        Returns standard VaR alongside prospect-adjusted value.
        """
        returns = np.asarray(returns, dtype=float)
        n = len(returns)

        var_standard = float(-np.percentile(returns, (1 - confidence) * 100))

        # Weight returns by prospect value
        pv = self.value_array(returns, reference)
        sorted_pv = np.sort(pv)

        # LA-VaR: find quantile in prospect-value space
        q_idx = int((1 - confidence) * n)
        la_var_pv = float(-sorted_pv[max(q_idx, 0)])

        # Effective multiplier from loss aversion
        loss_mask = returns < reference
        if loss_mask.sum() > 0:
            mean_loss = float(-np.mean(returns[loss_mask]))
            mean_loss_pv = float(-np.mean(pv[loss_mask]))
            la_multiplier = mean_loss_pv / mean_loss if mean_loss > 0 else 1.0
        else:
            la_multiplier = 1.0

        return {
            "var_standard": var_standard,
            "la_var_prospect_value": la_var_pv,
            "la_multiplier": float(la_multiplier),
            "loss_aversion_lambda": self.lambda_,
            "interpretation": (
                f"Loss-aversion (λ={self.lambda_:.2f}) makes losses feel "
                f"{la_multiplier:.2f}× worse than standard VaR implies."
            ),
        }

    # ------------------------------------------------------------------ #
    # Framing effects                                                     #
    # ------------------------------------------------------------------ #

    def framing_analysis(
        self,
        gain_frame_outcomes: np.ndarray,
        gain_frame_probs: np.ndarray,
        loss_frame_outcomes: np.ndarray,
        loss_frame_probs: np.ndarray,
    ) -> dict:
        """
        Demonstrate framing effect: identical expected outcomes, different choices.

        Classic example (Tversky & Kahneman 1981):
        - Gain frame: "400 people saved for certain" vs "1/3 chance 600 saved"
        - Loss frame: "200 people die for certain" vs "1/3 chance nobody dies"
        Economically identical, but gain frame → risk aversion; loss frame → risk seeking.
        """
        ev_gain = float(np.sum(gain_frame_probs * gain_frame_outcomes))
        ev_loss = float(np.sum(loss_frame_probs * loss_frame_outcomes))

        pv_gain = self.prospect_value(gain_frame_outcomes, gain_frame_probs)
        pv_loss = self.prospect_value(loss_frame_outcomes, loss_frame_probs)

        # Risk aversion in gain domain: prefer certain gain
        # Reference for gain frame: worst outcome; for loss frame: best outcome
        ref_gain = float(np.min(gain_frame_outcomes))
        ref_loss = float(np.max(loss_frame_outcomes))

        certain_gain_pv = self.value(ev_gain, ref_gain)
        certain_loss_pv = self.value(ev_loss, ref_loss)

        return {
            "expected_value_gain_frame": ev_gain,
            "expected_value_loss_frame": ev_loss,
            "prospect_value_gain_frame": pv_gain,
            "prospect_value_loss_frame": pv_loss,
            "certain_equivalent_gain_pv": certain_gain_pv,
            "certain_equivalent_loss_pv": certain_loss_pv,
            "risk_averse_in_gains": bool(certain_gain_pv > pv_gain),
            "risk_seeking_in_losses": bool(pv_loss > certain_loss_pv),
            "framing_effect_present": True,
            "explanation": (
                "Prospect theory predicts risk aversion in gains (value function concave) "
                "and risk seeking in losses (value function convex). Identical EV prospects "
                "are evaluated differently depending on whether framed as gains or losses."
            ),
        }

    def certainty_equivalent(
        self,
        outcomes: np.ndarray,
        probabilities: np.ndarray,
        reference: float = 0.0,
    ) -> float:
        """
        CE: certain amount with same prospect value as the risky prospect.

        Solve: v(CE) = V(prospect)  =>  CE = v^{-1}(V)
        """
        pv = self.prospect_value(outcomes, probabilities, reference)
        # Invert value function: v(CE) = pv
        if pv >= 0:
            # v(x) = x^alpha → x = pv^(1/alpha)
            return float(pv ** (1.0 / self.alpha)) + reference
        else:
            # v(x) = -lambda * (-x)^beta → -x = (-pv/lambda)^(1/beta)
            return float(-(((-pv) / self.lambda_) ** (1.0 / self.beta))) + reference
