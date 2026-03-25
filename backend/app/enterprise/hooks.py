"""
Extension points for Enterprise modules.
Each function has a default implementation (Community mode).
Enterprise modules replace these functions at startup.

Convention: Enterprise hooks raise HTTPException(402) in Community mode.
The 402 (Payment Required) code is semantically correct and distinct from other errors.
"""

from fastapi import HTTPException


# --- Auth / RBAC ---


async def check_rbac(user: dict, action: str, resource: str) -> bool:
    """Community: no control, always authorized."""
    return True


async def get_sso_router():
    """Community: no SSO routes."""
    return None


# --- Visual Diff ---


async def get_visual_diff(
    db, tree_id: int, version_a_id: int, version_b_id: int
) -> dict:
    """Community: feature not available."""
    raise HTTPException(
        status_code=402, detail="Visual Diff is an Enterprise feature"
    )


# --- Connectors ---


def get_import_connectors() -> list[dict]:
    """Community: no native connectors (standard CSV import only)."""
    return []


def get_export_connectors() -> list[dict]:
    """Community: no outgoing connectors (standard webhooks only)."""
    return []


# --- Reporting ---


async def get_multi_tree_report(db, tree_ids: list[int]) -> dict:
    """Community: feature not available."""
    raise HTTPException(
        status_code=402, detail="Reporting is an Enterprise feature"
    )


# --- Advanced Audit Trail ---


async def generate_decision_certificate(
    db, evaluation_id: int, format: str
) -> bytes:
    """Community: feature not available."""
    raise HTTPException(
        status_code=402,
        detail="Decision certificates are an Enterprise feature",
    )
