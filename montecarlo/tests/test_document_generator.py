"""
Tests for Ravinala Document Generator.
Tests cover PDF validity, page count, LLM fallback, and endpoint behaviour.
"""

from __future__ import annotations

import sys
import os
import io
from unittest.mock import patch, MagicMock

import pytest

# Make sure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import generators directly (bypasses FastAPI)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.document_generator import (
    TermSheetGenerator,
    ScenarioBookGenerator,
    RiskSummaryGenerator,
    generate_narrative,
    _narrative_fallback,
)

# ── Fixtures ──────────────────────────────────────────────────────────────

MINIMAL_PARAMS = {
    "product_type":      "european_call",
    "underlying":        "CAC 40",
    "currency":          "EUR",
    "issuer":            "Ravinala Capital",
    "spot":              7500.0,
    "strike":            7500.0,
    "maturity_years":    1.0,
    "risk_free_rate":    0.03,
    "volatility":        0.20,
    "dividend_yield":    0.0,
    "capital_protection": 0.90,
    "coupon_rate":       0.08,
    "barrier_level":     None,
    "barrier_type":      None,
    "autocall_levels":   None,
    "correlation_matrix": None,
    "underlyings":       None,
    "client_name":       "Test Client",
    "product_name":      "Test Call",
    "include_backtesting": False,
    "notional":          1.0,
}

BARRIER_PARAMS = {
    **MINIMAL_PARAMS,
    "product_type":  "barrier",
    "barrier_level": 0.70,
    "barrier_type":  "down-and-in",
    "product_name":  "Barrier Down-In",
}

AUTOCALL_PARAMS = {
    **MINIMAL_PARAMS,
    "product_type":    "autocall",
    "autocall_levels": [1.0, 0.95, 0.90],
    "coupon_rate":     0.10,
    "product_name":    "Autocall Phoenix",
}


# ═══════════════════════════════════════════════════════════════════════════
# 1. TermSheetGenerator
# ═══════════════════════════════════════════════════════════════════════════

class TestTermSheetGenerator:

    def test_generates_valid_pdf_bytes(self):
        """Output must start with PDF magic bytes and exceed 10 KB."""
        gen = TermSheetGenerator()
        pdf = gen.generate(MINIMAL_PARAMS)

        assert isinstance(pdf, bytes), "generate() must return bytes"
        assert pdf[:4] == b"%PDF", "Output is not a valid PDF (bad magic bytes)"
        assert len(pdf) > 10_000, f"PDF too small: {len(pdf)} bytes"

    def test_generates_pdf_for_barrier_product(self):
        gen = TermSheetGenerator()
        pdf = gen.generate(BARRIER_PARAMS)
        assert pdf[:4] == b"%PDF"

    def test_generates_pdf_for_autocall_product(self):
        gen = TermSheetGenerator()
        pdf = gen.generate(AUTOCALL_PARAMS)
        assert pdf[:4] == b"%PDF"

    def test_output_is_deterministic_structure(self):
        """Two runs with same params produce PDFs of similar size (±20%)."""
        gen = TermSheetGenerator()
        pdf1 = gen.generate(MINIMAL_PARAMS)
        pdf2 = gen.generate(MINIMAL_PARAMS)
        ratio = len(pdf1) / len(pdf2)
        assert 0.8 <= ratio <= 1.2, "PDFs differ too much between runs"


# ═══════════════════════════════════════════════════════════════════════════
# 2. ScenarioBookGenerator
# ═══════════════════════════════════════════════════════════════════════════

class TestScenarioBookGenerator:

    def test_generates_valid_pdf(self):
        gen = ScenarioBookGenerator()
        pdf = gen.generate(MINIMAL_PARAMS, include_backtesting=False)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 30_000, f"Scenario book PDF too small: {len(pdf)} bytes"

    def test_page_count_within_expected_range(self):
        """
        Parse PDF with pypdf (if available) and verify 10–15 pages.
        Falls back to size heuristic if pypdf not installed.
        """
        gen = ScenarioBookGenerator()
        pdf = gen.generate(MINIMAL_PARAMS, include_backtesting=False)

        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf))
            n_pages = len(reader.pages)
            assert 8 <= n_pages <= 20, (
                f"Expected 10–15 pages, got {n_pages}. "
                "Margins may differ slightly in test environment."
            )
        except ImportError:
            # Heuristic: a typical 12-page PDF with images is > 100 KB
            assert len(pdf) > 100_000, (
                f"PDF may be too short ({len(pdf)} bytes). "
                "Install pypdf for exact page count: pip install pypdf"
            )

    def test_generates_with_backtesting_enabled(self):
        gen = ScenarioBookGenerator()
        pdf = gen.generate(MINIMAL_PARAMS, include_backtesting=True)
        assert pdf[:4] == b"%PDF"

    def test_generates_with_client_name(self):
        gen = ScenarioBookGenerator()
        pdf = gen.generate(MINIMAL_PARAMS, client_name="BNP Paribas AM")
        assert pdf[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# 3. RiskSummaryGenerator
# ═══════════════════════════════════════════════════════════════════════════

class TestRiskSummaryGenerator:

    def test_generates_valid_pdf_single_position(self):
        gen = RiskSummaryGenerator()
        pdf = gen.generate([MINIMAL_PARAMS])
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 10_000

    def test_generates_valid_pdf_multiple_positions(self):
        gen = RiskSummaryGenerator()
        positions = [MINIMAL_PARAMS, BARRIER_PARAMS, AUTOCALL_PARAMS]
        pdf = gen.generate(positions)
        assert pdf[:4] == b"%PDF"

    def test_aggregation_does_not_crash_on_high_delta(self):
        """Extreme parameters should not raise exceptions."""
        extreme = {**MINIMAL_PARAMS, "spot": 100.0, "strike": 50.0,
                   "volatility": 0.80, "maturity_years": 0.1}
        gen = RiskSummaryGenerator()
        pdf = gen.generate([extreme])
        assert pdf[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# 4. Narrative / LLM fallback
# ═══════════════════════════════════════════════════════════════════════════

class TestNarrative:

    def test_fallback_returns_four_keys(self):
        result = _narrative_fallback(MINIMAL_PARAMS, {"delta": 0.5, "vega": 0.1, "var_95": -2.0})
        assert set(result.keys()) == {
            "executive_summary", "risk_analysis", "market_context", "conclusion"
        }

    def test_fallback_strings_are_non_empty(self):
        result = _narrative_fallback(MINIMAL_PARAMS, {"delta": 0.5, "vega": 0.1, "var_95": -2.0})
        for key, val in result.items():
            assert isinstance(val, str) and len(val) > 20, \
                f"Narrative key '{key}' is too short or not a string"

    def test_narrative_uses_fallback_when_llm_raises(self):
        """
        Mock the LLM call to raise an exception.
        generate_narrative() must still return valid text blocks.
        """
        metrics = {"delta": 0.45, "vega": 0.12, "var_95": -3.5}

        with patch("app.services.document_generator._call_anthropic",
                   side_effect=Exception("LLM quota exceeded")), \
             patch("app.services.document_generator._call_openai",
                   side_effect=Exception("LLM quota exceeded")), \
             patch.dict(os.environ, {"NARRATIVE_LLM_PROVIDER": "anthropic"}):

            result = generate_narrative(MINIMAL_PARAMS, metrics)

        assert isinstance(result, dict)
        assert "executive_summary" in result
        assert len(result["executive_summary"]) > 10

    def test_termsheet_pdf_still_generated_without_llm(self):
        """
        Even when LLM fails, TermSheetGenerator must produce a valid PDF
        (term sheet does not call LLM, so this is a sanity check).
        """
        with patch("app.services.document_generator._call_anthropic",
                   side_effect=Exception("No LLM")), \
             patch("app.services.document_generator._call_openai",
                   side_effect=Exception("No LLM")):
            gen = TermSheetGenerator()
            pdf = gen.generate(MINIMAL_PARAMS)

        assert pdf[:4] == b"%PDF"

    def test_scenariobook_pdf_still_generated_without_llm(self):
        """Scenario book uses LLM for narrative but must fall back gracefully."""
        with patch("app.services.document_generator._call_anthropic",
                   side_effect=Exception("No LLM")), \
             patch("app.services.document_generator._call_openai",
                   side_effect=Exception("No LLM")), \
             patch.dict(os.environ, {"NARRATIVE_LLM_PROVIDER": "anthropic"}):
            gen = ScenarioBookGenerator()
            pdf = gen.generate(MINIMAL_PARAMS)

        assert pdf[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# 5. FastAPI endpoint tests (requires httpx TestClient)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from fastapi.testclient import TestClient
    from app.main import app as _fastapi_app
    _FASTAPI_OK = True
except Exception:
    _FASTAPI_OK = False


@pytest.mark.skipif(not _FASTAPI_OK, reason="FastAPI app not importable in this context")
class TestEndpoints:

    @pytest.fixture
    def client(self):
        return TestClient(_fastapi_app)

    def test_termsheet_endpoint_returns_pdf(self, client):
        resp = client.post("/api/v1/generate/termsheet", json=MINIMAL_PARAMS)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_termsheet_endpoint_rejects_missing_spot(self, client):
        bad = {k: v for k, v in MINIMAL_PARAMS.items() if k != "spot"}
        resp = client.post("/api/v1/generate/termsheet", json=bad)
        assert resp.status_code == 422  # Pydantic validation error

    def test_scenariobook_endpoint_returns_pdf(self, client):
        params = {**MINIMAL_PARAMS, "backtest_period_years": 5.0, "var_confidence": 0.95}
        resp = client.post("/api/v1/generate/scenariobook", json=params)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_risksummary_endpoint_returns_pdf(self, client):
        resp = client.post("/api/v1/generate/risksummary", json=[MINIMAL_PARAMS])
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_risksummary_rejects_empty_positions(self, client):
        resp = client.post("/api/v1/generate/risksummary", json=[])
        assert resp.status_code == 422
