"""
routes/export.py — Data export endpoints (Excel, PDF).

Étape 3 — Structuration backend
─────────────────────────────────
Routes:
  POST /api/v1/export/excel
  POST /api/v1/export/pdf
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models import EmailExportRequest, ExcelExportRequest, PDFExportRequest
from app.schemas.envelope import ApiError
from app.services.export_service import export_dashboard_excel, export_dashboard_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])

_ERROR_RESPONSES = {
    500: {"model": ApiError, "description": "Export generation failed"},
}


@router.post(
    "/excel",
    response_model=None,
    responses={**_ERROR_RESPONSES},
    summary="Export dashboard as Excel workbook",
    description="Returns a .xlsx file with selected dashboard sections as sheets.",
)
async def export_excel(request: ExcelExportRequest) -> FileResponse:
    """Export dashboard data as an Excel workbook (.xlsx)."""
    try:
        exported = await export_dashboard_excel(request)
        return FileResponse(
            exported.path,
            media_type=exported.media_type,
            filename=exported.filename,
        )
    except Exception as exc:
        logger.error("Excel export failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/pdf",
    response_model=None,
    responses={**_ERROR_RESPONSES},
    summary="Export dashboard as PDF",
    description="Returns a landscape PDF report of the current dashboard snapshot.",
)
async def export_pdf(request: PDFExportRequest) -> FileResponse:
    """Export dashboard summary as a PDF report."""
    try:
        exported = await export_dashboard_pdf(request)
        return FileResponse(
            exported.path,
            media_type=exported.media_type,
            filename=exported.filename,
        )
    except Exception as exc:
        logger.error("PDF export failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
