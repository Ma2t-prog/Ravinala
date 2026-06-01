"""
Tests de non-régression — Sprint F/G/H/I (S1.2, S2.4, S3.2, S6.3, Q5.4, Q2.4/Q2.2).

Périmètre :
  F — Security hardening : S1.2 (trust_x_forwarded_for guard),
                           S2.4 (anonymous access forbidden at security_level ≥ 2),
                           S3.2 (no localhost in CORS at security_level ≥ 2)
  G — Fallback visibility : S6.3 (using_fallback field in ApiResponse)
  H — Risk governance     : Q5.4 (breach_recommended_actions in AllocationCandidateRiskDiagnostics)
  I — ML data quality     : Q2.4/Q2.2 (fill_method, causal_fill_policy + row counts in artifact_meta)

Aucun appel réseau / base de données.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

# ── Stub heavy optional imports before any app import ─────────────────────────
for _mod in (
    "langgraph", "langgraph.config", "langgraph.graph", "langgraph.graph.message",
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "celery", "redis",
):
    sys.modules.setdefault(_mod, mock.MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError

# ══════════════════════════════════════════════════════════════════════════════
# Sprint F — Security hardening (S1.2 / S2.4 / S3.2)
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigSecurityHardening:
    """Tests for the three validators added to Settings.validate_security_settings()."""

    def _make_settings(self, **overrides):
        """Helper: build a Settings instance, bypassing lru_cache."""
        from app.core.config import Settings
        defaults = dict(
            db_user="test", db_host="localhost", db_port=5432, db_name="test",
            redis_host="localhost", redis_port=6379,
            secret_key="CHANGE-ME-IN-PRODUCTION",
            security_level=0,
            cors_allowed_origins="http://localhost:5173",
            allow_anonymous_readonly_local=True,
            trust_x_forwarded_for=False,
            login_max_attempts=5,
            login_window_seconds=300,
        )
        defaults.update(overrides)
        return Settings(**defaults)

    # S1.2 — trust_x_forwarded_for guard ─────────────────────────────────────

    def test_s12_trust_forwarded_for_level0_raises(self):
        """trust_x_forwarded_for=True at security_level=0 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(trust_x_forwarded_for=True, security_level=0)

    def test_s12_trust_forwarded_for_level1_raises(self):
        """trust_x_forwarded_for=True at security_level=1 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(
                trust_x_forwarded_for=True,
                security_level=1,
                secret_key="secure-key-for-level1",
                cors_allowed_origins="http://example.com",
                allow_anonymous_readonly_local=False,
            )

    def test_s12_trust_forwarded_for_level2_ok(self):
        """trust_x_forwarded_for=True at security_level=2 must be accepted."""
        s = self._make_settings(
            trust_x_forwarded_for=True,
            security_level=2,
            secret_key="secure-key-level2",
            cors_allowed_origins="http://example.com",
            allow_anonymous_readonly_local=False,
        )
        assert s.trust_x_forwarded_for is True

    def test_s12_trust_forwarded_for_false_level0_ok(self):
        """trust_x_forwarded_for=False at any level must be accepted."""
        s = self._make_settings(trust_x_forwarded_for=False, security_level=0)
        assert s.trust_x_forwarded_for is False

    # S2.4 — anonymous access forbidden at controlled level ───────────────────

    def test_s24_anonymous_at_level2_raises(self):
        """allow_anonymous_readonly_local=True at security_level=2 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(
                security_level=2,
                secret_key="secure-key-level2",
                cors_allowed_origins="http://example.com",
                allow_anonymous_readonly_local=True,
                trust_x_forwarded_for=False,
            )

    def test_s24_anonymous_at_level3_raises(self):
        """allow_anonymous_readonly_local=True at security_level=3 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(
                security_level=3,
                secret_key="secure-key-level3",
                cors_allowed_origins="http://example.com",
                allow_anonymous_readonly_local=True,
                trust_x_forwarded_for=False,
            )

    def test_s24_anonymous_false_level2_ok(self):
        """allow_anonymous_readonly_local=False at security_level=2 must be accepted."""
        s = self._make_settings(
            security_level=2,
            secret_key="secure-key-level2",
            cors_allowed_origins="http://example.com",
            allow_anonymous_readonly_local=False,
            trust_x_forwarded_for=False,
        )
        assert s.allow_anonymous_readonly_local is False

    def test_s24_anonymous_true_level1_ok(self):
        """allow_anonymous_readonly_local=True at security_level=1 must be accepted."""
        s = self._make_settings(
            security_level=1,
            secret_key="secure-key-level1",
            cors_allowed_origins="http://example.com",
            allow_anonymous_readonly_local=True,
            trust_x_forwarded_for=False,
        )
        assert s.allow_anonymous_readonly_local is True

    # S3.2 — CORS must not include localhost at security_level ≥ 2 ─────────────

    def test_s32_localhost_in_cors_level2_raises(self):
        """CORS with localhost at security_level=2 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(
                security_level=2,
                secret_key="secure-key-level2",
                cors_allowed_origins="http://localhost:5173",
                allow_anonymous_readonly_local=False,
                trust_x_forwarded_for=False,
            )

    def test_s32_127001_in_cors_level2_raises(self):
        """CORS with 127.0.0.1 at security_level=2 must raise."""
        with pytest.raises((ValueError, ValidationError)):
            self._make_settings(
                security_level=2,
                secret_key="secure-key-level2",
                cors_allowed_origins="http://127.0.0.1:5173",
                allow_anonymous_readonly_local=False,
                trust_x_forwarded_for=False,
            )

    def test_s32_clean_cors_level2_ok(self):
        """CORS without localhost at security_level=2 must be accepted."""
        s = self._make_settings(
            security_level=2,
            secret_key="secure-key-level2",
            cors_allowed_origins="https://app.example.com",
            allow_anonymous_readonly_local=False,
            trust_x_forwarded_for=False,
        )
        assert "localhost" not in s.cors_allowed_origins

    def test_s32_localhost_in_cors_level1_ok(self):
        """CORS with localhost at security_level=1 must still be accepted (warn only)."""
        s = self._make_settings(
            security_level=1,
            secret_key="secure-key-level1",
            cors_allowed_origins="http://localhost:5173",
            allow_anonymous_readonly_local=False,
            trust_x_forwarded_for=False,
        )
        assert "localhost" in s.cors_allowed_origins


# ══════════════════════════════════════════════════════════════════════════════
# Sprint G — Fallback visibility (S6.3)
# ══════════════════════════════════════════════════════════════════════════════

class TestApiResponseFallbackVisibility:
    """Tests that ApiResponse carries the using_fallback field (S6.3)."""

    def _make_response(self, **kwargs):
        from app.schemas.envelope import ApiResponse
        return ApiResponse(data={"ok": True}, data_quality="live", **kwargs)

    def test_s63_using_fallback_field_exists(self):
        """ApiResponse must expose a using_fallback field."""
        resp = self._make_response()
        assert hasattr(resp, "using_fallback")

    def test_s63_using_fallback_defaults_to_false(self):
        """using_fallback defaults to False when not provided."""
        resp = self._make_response()
        assert resp.using_fallback is False

    def test_s63_using_fallback_can_be_set_true(self):
        """Caller must be able to flag using_fallback=True."""
        resp = self._make_response(using_fallback=True)
        assert resp.using_fallback is True

    def test_s63_using_fallback_serialised_in_json(self):
        """using_fallback must appear in the JSON serialisation."""
        resp = self._make_response(using_fallback=False)
        payload = resp.model_dump()
        assert "using_fallback" in payload

    def test_s63_using_fallback_false_in_json(self):
        """Default serialised value is False."""
        resp = self._make_response()
        assert resp.model_dump()["using_fallback"] is False

    def test_s63_using_fallback_true_in_json(self):
        """Flagged value serialises as True."""
        resp = self._make_response(using_fallback=True)
        assert resp.model_dump()["using_fallback"] is True


# ══════════════════════════════════════════════════════════════════════════════
# Sprint H — Risk governance: breach_recommended_actions (Q5.4)
# ══════════════════════════════════════════════════════════════════════════════

class TestBreachRecommendedActions:
    """Tests for Q5.4 governance: corrective actions per breach type."""

    def _make_diagnostics(self, **kwargs):
        from app.schemas.allocator import AllocationCandidateRiskDiagnostics
        return AllocationCandidateRiskDiagnostics(**kwargs)

    def test_q54_field_exists_on_schema(self):
        """AllocationCandidateRiskDiagnostics must have breach_recommended_actions."""
        d = self._make_diagnostics()
        assert hasattr(d, "breach_recommended_actions")

    def test_q54_default_is_empty_dict(self):
        """breach_recommended_actions defaults to empty dict when no breaches."""
        d = self._make_diagnostics()
        assert d.breach_recommended_actions == {}

    def test_q54_accepts_populated_dict(self):
        """Schema accepts a populated breach_recommended_actions dict."""
        d = self._make_diagnostics(
            breach_recommended_actions={"max_single_name_weight": "Reduce the position."}
        )
        assert "max_single_name_weight" in d.breach_recommended_actions

    def test_q54_build_no_breach_empty_actions(self):
        """build_candidate_risk_diagnostics: no breach → empty actions dict."""
        from app.services.portfolio_risk_inputs_service import build_candidate_risk_diagnostics
        from app.schemas.allocator import (
            PortfolioRiskInputsResponse, AssetRiskInput, PortfolioRiskBudget,
            UniverseRiskDiagnostics, RiskGovernanceSummary,
        )

        cov = {"AAPL": {"AAPL": 0.04, "MSFT": 0.01}, "MSFT": {"AAPL": 0.01, "MSFT": 0.04}}
        corr = {"AAPL": {"AAPL": 1.0, "MSFT": 0.25}, "MSFT": {"AAPL": 0.25, "MSFT": 1.0}}

        risk_inputs = PortfolioRiskInputsResponse(
            methodology_version="v1",
            risk_model_type="test",
            data_source="test",
            lookback_days=252,
            observation_count=252,
            annualization_factor=252,
            risk_free_rate_used=0.043,
            benchmark_preference="60_40",
            tickers_used=["AAPL", "MSFT"],
            dropped_tickers=[],
            asset_risk_inputs=[
                AssetRiskInput(ticker="AAPL", name="Apple", asset_class="equity",
                               annualized_volatility=0.20, max_drawdown_proxy=0.15,
                               data_points_used=252),
                AssetRiskInput(ticker="MSFT", name="Microsoft", asset_class="equity",
                               annualized_volatility=0.18, max_drawdown_proxy=0.12,
                               data_points_used=252),
            ],
            covariance_matrix=cov,
            correlation_matrix=corr,
            top_correlation_pairs=[],
            risk_budget=PortfolioRiskBudget(
                target_volatility=0.99,        # very loose — no vol breach
                max_drawdown_tolerance=0.99,   # very loose — no drawdown breach
                max_single_name_weight=1.0,    # no cap
                min_weight=0.0,
                cash_buffer_weight=0.0,
                concentration_hhi_soft_limit=1.0,  # no limit
                effective_name_floor=1.0,
            ),
            universe_risk_diagnostics=UniverseRiskDiagnostics(
                asset_count=2, observation_count=252,
            ),
            governance_summary=RiskGovernanceSummary(
                model_type="test", covariance_estimator="test",
                concentration_support="test", scenario_support="deferred",
            ),
            warnings=[],
        )

        result = build_candidate_risk_diagnostics(
            candidate_weights={"AAPL": 0.5, "MSFT": 0.5},
            risk_inputs=risk_inputs,
        )
        assert result.risk_budget_breaches == []
        assert result.breach_recommended_actions == {}

    def test_q54_max_single_name_breach_has_action(self):
        """max_single_name_weight breach → non-empty recommended action."""
        from app.services.portfolio_risk_inputs_service import build_candidate_risk_diagnostics
        from app.schemas.allocator import (
            PortfolioRiskInputsResponse, AssetRiskInput, PortfolioRiskBudget,
            UniverseRiskDiagnostics, RiskGovernanceSummary,
        )

        cov = {"AAPL": {"AAPL": 0.04, "MSFT": 0.01}, "MSFT": {"AAPL": 0.01, "MSFT": 0.04}}
        corr = {"AAPL": {"AAPL": 1.0, "MSFT": 0.25}, "MSFT": {"AAPL": 0.25, "MSFT": 1.0}}

        risk_inputs = PortfolioRiskInputsResponse(
            methodology_version="v1",
            risk_model_type="test",
            data_source="test",
            lookback_days=252,
            observation_count=252,
            annualization_factor=252,
            risk_free_rate_used=0.043,
            benchmark_preference="60_40",
            tickers_used=["AAPL", "MSFT"],
            dropped_tickers=[],
            asset_risk_inputs=[
                AssetRiskInput(ticker="AAPL", name="Apple", asset_class="equity",
                               annualized_volatility=0.20, max_drawdown_proxy=0.15,
                               data_points_used=252),
                AssetRiskInput(ticker="MSFT", name="Microsoft", asset_class="equity",
                               annualized_volatility=0.18, max_drawdown_proxy=0.12,
                               data_points_used=252),
            ],
            covariance_matrix=cov,
            correlation_matrix=corr,
            top_correlation_pairs=[],
            risk_budget=PortfolioRiskBudget(
                target_volatility=0.99,
                max_drawdown_tolerance=0.99,
                max_single_name_weight=0.30,  # tight cap — 0.90 weight will breach
                min_weight=0.0,
                cash_buffer_weight=0.0,
                concentration_hhi_soft_limit=1.0,
                effective_name_floor=1.0,
            ),
            universe_risk_diagnostics=UniverseRiskDiagnostics(
                asset_count=2, observation_count=252,
            ),
            governance_summary=RiskGovernanceSummary(
                model_type="test", covariance_estimator="test",
                concentration_support="test", scenario_support="deferred",
            ),
            warnings=[],
        )

        result = build_candidate_risk_diagnostics(
            candidate_weights={"AAPL": 0.90, "MSFT": 0.10},
            risk_inputs=risk_inputs,
        )
        assert "max_single_name_weight" in result.risk_budget_breaches
        assert "max_single_name_weight" in result.breach_recommended_actions
        assert len(result.breach_recommended_actions["max_single_name_weight"]) > 10

    def test_q54_all_four_breach_types_have_actions(self):
        """All four known breach keys must produce non-empty action strings."""
        from app.schemas.allocator import AllocationCandidateRiskDiagnostics
        # Construct directly with all four known breaches
        d = AllocationCandidateRiskDiagnostics(
            risk_budget_breaches=[
                "max_single_name_weight",
                "concentration_hhi_soft_limit",
                "target_volatility",
                "weighted_drawdown_proxy",
            ],
            breach_recommended_actions={
                "max_single_name_weight": "Reduce the largest position ...",
                "concentration_hhi_soft_limit": "Increase diversification ...",
                "target_volatility": "Reduce exposure to high-volatility assets ...",
                "weighted_drawdown_proxy": "Review assets with high historical drawdown ...",
            },
        )
        for key in ("max_single_name_weight", "concentration_hhi_soft_limit",
                    "target_volatility", "weighted_drawdown_proxy"):
            assert key in d.breach_recommended_actions
            assert len(d.breach_recommended_actions[key]) > 5

    def test_q54_actions_keys_subset_of_breaches(self):
        """breach_recommended_actions keys must be a subset of risk_budget_breaches."""
        from app.services.portfolio_risk_inputs_service import build_candidate_risk_diagnostics
        from app.schemas.allocator import (
            PortfolioRiskInputsResponse, AssetRiskInput, PortfolioRiskBudget,
            UniverseRiskDiagnostics, RiskGovernanceSummary,
        )

        cov = {"AAPL": {"AAPL": 0.04, "MSFT": 0.01}, "MSFT": {"AAPL": 0.01, "MSFT": 0.04}}
        corr = {"AAPL": {"AAPL": 1.0, "MSFT": 0.25}, "MSFT": {"AAPL": 0.25, "MSFT": 1.0}}

        risk_inputs = PortfolioRiskInputsResponse(
            methodology_version="v1", risk_model_type="t", data_source="t",
            lookback_days=252, observation_count=252, annualization_factor=252,
            risk_free_rate_used=0.04, benchmark_preference="60_40",
            tickers_used=["AAPL", "MSFT"], dropped_tickers=[],
            asset_risk_inputs=[
                AssetRiskInput(ticker="AAPL", name="A", asset_class="equity",
                               annualized_volatility=0.30, max_drawdown_proxy=0.50,
                               data_points_used=252),
                AssetRiskInput(ticker="MSFT", name="M", asset_class="equity",
                               annualized_volatility=0.30, max_drawdown_proxy=0.50,
                               data_points_used=252),
            ],
            covariance_matrix=cov, correlation_matrix=corr, top_correlation_pairs=[],
            risk_budget=PortfolioRiskBudget(
                target_volatility=0.01,        # very tight → vol breach
                max_drawdown_tolerance=0.01,   # very tight → drawdown breach
                max_single_name_weight=0.30,   # tight → concentration breach
                min_weight=0.0, cash_buffer_weight=0.0,
                concentration_hhi_soft_limit=0.10,  # tight → HHI breach
                effective_name_floor=1.0,
            ),
            universe_risk_diagnostics=UniverseRiskDiagnostics(asset_count=2, observation_count=252),
            governance_summary=RiskGovernanceSummary(
                model_type="t", covariance_estimator="t",
                concentration_support="t", scenario_support="deferred",
            ),
            warnings=[],
        )

        result = build_candidate_risk_diagnostics(
            candidate_weights={"AAPL": 0.90, "MSFT": 0.10},
            risk_inputs=risk_inputs,
        )
        # Every key in actions must also be in breaches
        for key in result.breach_recommended_actions:
            assert key in result.risk_budget_breaches


# ══════════════════════════════════════════════════════════════════════════════
# Sprint I — ML data quality metadata (Q2.4 / Q2.2)
# ══════════════════════════════════════════════════════════════════════════════

class TestMLArtifactMetaDataQuality:
    """
    Tests for Q2.4/Q2.2: artifact_meta must document row counts and fill policy.

    We test by importing the private _build_artifact_meta helper or by inspecting
    the constant strings that training.py embeds at the call site.  Because we
    cannot run a full training pipeline in the test suite (no DB, no yfinance),
    we parse the source to verify the documented field names and values are
    present.  This is a structural test — it guards against accidental removal
    of the data-quality metadata.
    """

    def _get_artifact_meta_source(self) -> str:
        import inspect
        import importlib
        training = importlib.import_module("app.ml.training")
        try:
            src = inspect.getsource(training)
        except Exception:
            with open(training.__file__, encoding="utf-8") as fh:
                src = fh.read()
        return src

    def test_q24_fill_method_key_in_source(self):
        """artifact_meta must contain the 'fill_method' key (Q2.4)."""
        src = self._get_artifact_meta_source()
        assert '"fill_method"' in src or "'fill_method'" in src

    def test_q24_causal_fill_policy_key_in_source(self):
        """artifact_meta must contain the 'causal_fill_policy' key (Q2.2)."""
        src = self._get_artifact_meta_source()
        assert '"causal_fill_policy"' in src or "'causal_fill_policy'" in src

    def test_q24_dataset_total_rows_key_in_source(self):
        """artifact_meta must contain 'dataset_total_rows' (Q2.4 — before dropna)."""
        src = self._get_artifact_meta_source()
        assert '"dataset_total_rows"' in src or "'dataset_total_rows'" in src

    def test_q24_dataset_rows_after_dropna_key_in_source(self):
        """artifact_meta must contain 'dataset_rows_after_dropna' (Q2.4 — after dropna)."""
        src = self._get_artifact_meta_source()
        assert '"dataset_rows_after_dropna"' in src or "'dataset_rows_after_dropna'" in src

    def test_q24_training_samples_key_in_source(self):
        """artifact_meta must contain 'training_samples' (Q2.4)."""
        src = self._get_artifact_meta_source()
        assert '"training_samples"' in src or "'training_samples'" in src

    def test_q24_test_samples_key_in_source(self):
        """artifact_meta must contain 'test_samples' (Q2.4)."""
        src = self._get_artifact_meta_source()
        assert '"test_samples"' in src or "'test_samples'" in src

    def test_q24_feature_count_key_in_source(self):
        """artifact_meta must contain 'feature_count' (Q2.4)."""
        src = self._get_artifact_meta_source()
        assert '"feature_count"' in src or "'feature_count'" in src

    def test_q22_fill_method_value_no_fill_applied(self):
        """fill_method value must document that no fill is applied (Q2.2)."""
        src = self._get_artifact_meta_source()
        assert "no_fill_applied" in src

    def test_q22_causal_fill_policy_backward_only(self):
        """causal_fill_policy must document backward-only feature construction (Q2.2)."""
        src = self._get_artifact_meta_source()
        assert "backward_only" in src

    def test_q22_no_ffill_bfill_documented(self):
        """Policy must document absence of ffill/bfill on features (Q2.2)."""
        src = self._get_artifact_meta_source()
        assert "no_ffill_bfill" in src or "no ffill" in src.lower() or "no_ffill" in src
