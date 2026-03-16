"""Route pour exposer le statut de licence (Community / Enterprise)."""

from fastapi import APIRouter

from app.enterprise.license import get_enterprise_version, get_features, is_enterprise

router = APIRouter()


@router.get("")
async def get_license_info():
    """Retourne le mode actif, les features disponibles et la version enterprise.

    Pas d'auth requise : le frontend doit pouvoir l'appeler avant login.
    Ne retourne jamais la clé de licence elle-même.
    """
    return {
        "edition": "enterprise" if is_enterprise() else "community",
        "features": get_features(),
        "enterprise_version": get_enterprise_version(),
    }
