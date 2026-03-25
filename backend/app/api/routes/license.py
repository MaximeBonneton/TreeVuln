"""Route pour exposer le statut de licence (Community / Enterprise)."""

from fastapi import APIRouter

from app.enterprise.license import get_enterprise_version, get_features, is_enterprise

router = APIRouter()


@router.get("")
async def get_license_info():
    """Return the active mode, available features, and enterprise version.

    No auth required: the frontend must be able to call it before login.
    Never returns the license key itself.
    """
    return {
        "edition": "enterprise" if is_enterprise() else "community",
        "features": get_features(),
        "enterprise_version": get_enterprise_version(),
    }
