"""
routes/generate.py — Document generation endpoints (PDF term sheets, scenario books).

Étape 3 — Structuration backend
─────────────────────────────────
Routes:
  POST /api/v1/generate/termsheet
  POST /api/v1/generate/scenariobook
  POST /api/v1/generate/risksummary
"""

import asyncio
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.core.executor import get_shared_executor
from app.models import ProductParams, ScenarioBookParams
from app.schemas.envelope import ApiError
from app.services.cache import get_cache
from app.services.document_generator import (
    RiskSummaryGenerator,
    ScenarioBookGenerator,
    TermSheetGenerator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generate"])

_ERROR_RESPONSES = {
    500: {"model": ApiError, "description": "Document generation failed"},
    504: {"model": ApiError, "description": "Generation timed out"},
    422: {"model": ApiError, "description": "Invalid request parameters"},
}


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# TERM SHEET
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/termsheet",
    response_model=None,
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"application/pdf": {}}, "description": "2-page bank-style term sheet PDF"},
    },
    summary="Generate structured product term sheet",
    description="Generates a 2-page bank-format term sheet PDF for the given structured product. Timeout: 30s.",
)
async def generate_termsheet(
    params: ProductParams,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """Generate a 2-page bank-style term sheet PDF. Timeout: 30s."""
    try:
        loop = asyncio.get_event_loop()
        generator = TermSheetGenerator()
        pdf_bytes: bytes = await asyncio.wait_for(
            loop.run_in_executor(get_shared_executor(), generator.generate, params.model_dump()),
            timeout=30.0,
        )

        product_name = (params.product_name or params.product_type).replace(" ", "_")
        filename = f"termsheet_{product_name}_{_utcnow().strftime('%Y%m%d')}.pdf"

        background_tasks.add_task(
            logger.info,
            f"📄 Term sheet generated: {filename} ({len(pdf_bytes):,} bytes)",
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Term sheet generation timed out (30s)")
    except Exception as exc:
        logger.error(f"❌ Term sheet generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO BOOK
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/scenariobook",
    response_model=None,
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"application/pdf": {}}, "description": "10-15 page scenario book PDF"},
    },
    summary="Generate structured product scenario book",
    description="Generates a detailed 10-15 page scenario book with payoff analysis. Timeout: 60s.",
)
async def generate_scenariobook(
    params: ScenarioBookParams,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """Generate a 10-15 page scenario book PDF. Timeout: 60s."""
    try:
        loop = asyncio.get_event_loop()
        generator = ScenarioBookGenerator()

        pdf_bytes: bytes = await asyncio.wait_for(
            loop.run_in_executor(
                get_shared_executor(),
                lambda: generator.generate(
                    params.model_dump(),
                    include_backtesting=params.include_backtesting,
                    client_name=params.client_name,
                ),
            ),
            timeout=60.0,
        )

        product_name = (params.product_name or params.product_type).replace(" ", "_")
        date_str = _utcnow().strftime("%Y%m%d")
        filename = f"scenariobook_{product_name}_{date_str}.pdf"

        cache = get_cache()
        background_tasks.add_task(
            cache.set,
            f"doc:scenariobook:{date_str}:{product_name}",
            {
                "filename": filename,
                "size_bytes": len(pdf_bytes),
                "generated_at": _utcnow().isoformat(),
                "client": params.client_name,
            },
            section="snapshot",
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Scenario book generation timed out (60s)")
    except Exception as exc:
        logger.error(f"❌ Scenario book generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# RISK SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/risksummary",
    response_model=None,
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"application/pdf": {}}, "description": "1-page portfolio risk summary PDF"},
    },
    summary="Generate portfolio risk summary",
    description="Generates a 1-page risk summary for a list of portfolio positions. Timeout: 20s.",
)
async def generate_risksummary(
    positions: list[ProductParams],
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """Generate a 1-page portfolio risk summary PDF. Timeout: 20s."""
    if not positions:
        raise HTTPException(status_code=422, detail="At least one position is required.")

    try:
        loop = asyncio.get_event_loop()
        generator = RiskSummaryGenerator()
        positions_dicts = [p.model_dump() for p in positions]

        pdf_bytes: bytes = await asyncio.wait_for(
            loop.run_in_executor(get_shared_executor(), generator.generate, positions_dicts),
            timeout=20.0,
        )

        date_str = _utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"risksummary_portfolio_{date_str}.pdf"

        background_tasks.add_task(
            logger.info,
            f"📊 Risk summary generated: {len(positions)} positions, {len(pdf_bytes):,} bytes",
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Risk summary generation timed out (20s)")
    except Exception as exc:
        logger.error(f"❌ Risk summary generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
