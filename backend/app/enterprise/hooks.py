"""
Points d'extension pour les modules Enterprise.
Chaque fonction a une implémentation par défaut (mode Community).
Les modules Enterprise remplacent ces fonctions au démarrage.

Convention : les hooks Enterprise lèvent HTTPException(402) en mode Community.
Le code 402 (Payment Required) est sémantiquement correct et distinct des autres erreurs.
"""

from fastapi import HTTPException


# --- Auth / RBAC ---


async def check_rbac(user: dict, action: str, resource: str) -> bool:
    """Community : pas de contrôle, toujours autorisé."""
    return True


async def get_sso_router():
    """Community : pas de routes SSO."""
    return None


# --- Visual Diff ---


async def get_visual_diff(
    db, tree_id: int, version_a_id: int, version_b_id: int
) -> dict:
    """Community : feature non disponible."""
    raise HTTPException(
        status_code=402, detail="Visual Diff is an Enterprise feature"
    )


# --- Connecteurs ---


def get_import_connectors() -> list[dict]:
    """Community : pas de connecteurs natifs (import CSV standard uniquement)."""
    return []


def get_export_connectors() -> list[dict]:
    """Community : pas de connecteurs sortants (webhooks standards uniquement)."""
    return []


# --- Reporting ---


async def get_multi_tree_report(db, tree_ids: list[int]) -> dict:
    """Community : feature non disponible."""
    raise HTTPException(
        status_code=402, detail="Reporting is an Enterprise feature"
    )


# --- Audit Trail Avancé ---


async def generate_decision_certificate(
    db, evaluation_id: int, format: str
) -> bytes:
    """Community : feature non disponible."""
    raise HTTPException(
        status_code=402,
        detail="Decision certificates are an Enterprise feature",
    )
