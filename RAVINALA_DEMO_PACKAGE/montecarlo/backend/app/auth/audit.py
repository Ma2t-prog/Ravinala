"""
auth/audit.py — Audit trail logger.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
Records security-relevant actions to the audit_events table.
Fire-and-forget — never blocks the request path.

Actions:
  LOGIN, LOGOUT, LOGIN_FAILED,
  CREATE, UPDATE, DELETE,
  EXPORT, EXECUTE, ADMIN_ACTION
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


async def record_audit_event(
    action: str,
    user_id: str | uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Persist an audit event.  Best-effort — DB unavailability is tolerated.
    """
    try:
        from app.db.base import async_session  # noqa: PLC0415
        from app.db.models import AuditEvent   # noqa: PLC0415

        factory = async_session()
        if factory is None:
            return
        async with factory() as session:
            event = AuditEvent(
                user_id=uuid.UUID(str(user_id)) if user_id else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                detail=detail,
                ip_address=ip_address,
            )
            session.add(event)
            await session.commit()
    except Exception as exc:
        logger.debug("Audit event write skipped: %s", exc)


def fire_audit(
    action: str,
    user_id: str | uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Fire-and-forget audit event — safe to call from sync or async context.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(record_audit_event(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        ))
    except RuntimeError:
        # No event loop — skip silently (e.g. during tests or CLI)
        pass
