from fastapi import APIRouter

from app.api.deps import RequireAdmin
from app.api.routes import assets, auth, evaluate, field_mapping, ingest, license, tree, webhooks
from app.enterprise.license import is_enterprise

api_router = APIRouter()

# --- Routes publiques (pas d'auth) ---
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(license.router, prefix="/license", tags=["License"])

# --- Routes protégées par authentification admin ---
api_router.include_router(tree.router, prefix="/tree", tags=["Tree"], dependencies=[RequireAdmin])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"], dependencies=[RequireAdmin])
api_router.include_router(field_mapping.router, prefix="/tree", tags=["Field Mapping"], dependencies=[RequireAdmin])
api_router.include_router(field_mapping.global_router, prefix="/mapping", tags=["Field Mapping"], dependencies=[RequireAdmin])
api_router.include_router(webhooks.router, tags=["Webhooks"], dependencies=[RequireAdmin])
api_router.include_router(ingest.admin_router, tags=["Ingest"], dependencies=[RequireAdmin])
api_router.include_router(evaluate.router, prefix="/evaluate", tags=["Evaluate"], dependencies=[RequireAdmin])

# --- Routes publiques (auth propre via X-API-Key) ---
api_router.include_router(ingest.public_router, tags=["Ingest"])

# --- Routes Enterprise (enregistrement dynamique) ---
if is_enterprise():
    try:
        from app.enterprise.modules import get_enterprise_routers

        for _router, _prefix, _tag in get_enterprise_routers():
            api_router.include_router(_router, prefix=_prefix, tags=[_tag])
    except ImportError:
        pass
