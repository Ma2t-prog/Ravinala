"""
services/user_service.py - compatibility shim for user-management helpers.

The canonical implementation now lives in `identity_service.py`, which hosts
both auth and user-management flows behind one backend service boundary.
"""

from app.services.identity_service import (  # noqa: F401
    client_ip_from_request,
    deactivate_user,
    fetch_audit_trail,
    get_roles_catalog,
    get_security_status,
    get_visible_user,
    list_registered_users,
    update_managed_user,
)

__all__ = [
    "client_ip_from_request",
    "deactivate_user",
    "fetch_audit_trail",
    "get_roles_catalog",
    "get_security_status",
    "get_visible_user",
    "list_registered_users",
    "update_managed_user",
]
