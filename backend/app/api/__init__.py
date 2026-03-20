from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.api.routes import assets, auth, evaluate, field_mapping, ingest, license, tree, users, webhooks
from app.enterprise.license import is_enterprise

RequireAuth = [Depends(require_auth)]

api_router = APIRouter()

# --- Routes publiques (pas d'auth) ---
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(license.router, prefix="/license", tags=["License"])

# --- Routes authentifiées (operator + admin) — vérifications admin per-route ---
api_router.include_router(tree.router, prefix="/tree", tags=["Tree"], dependencies=RequireAuth)
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"], dependencies=RequireAuth)
api_router.include_router(field_mapping.router, prefix="/tree", tags=["Field Mapping"], dependencies=RequireAuth)
api_router.include_router(field_mapping.global_router, prefix="/mapping", tags=["Field Mapping"], dependencies=RequireAuth)
api_router.include_router(evaluate.router, prefix="/evaluate", tags=["Evaluate"], dependencies=RequireAuth)
api_router.include_router(webhooks.router, tags=["Webhooks"], dependencies=RequireAuth)
api_router.include_router(ingest.admin_router, tags=["Ingest"], dependencies=RequireAuth)

# --- Gestion utilisateurs (admin via per-route checks) ---
api_router.include_router(users.router, tags=["Users"], dependencies=RequireAuth)

# --- Ingestion publique (auth par X-API-Key) ---
api_router.include_router(ingest.public_router, tags=["Ingest"])

# --- Routes Enterprise (enregistrement dynamique) ---
if is_enterprise():
    try:
        from app.enterprise.modules import get_enterprise_routers

        for _router, _prefix, _tag in get_enterprise_routers():
            api_router.include_router(_router, prefix=_prefix, tags=[_tag])
    except ImportError:
        pass
