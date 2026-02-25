from fastapi import APIRouter

from app.api.deps import RequireAdmin
from app.api.routes import assets, auth, evaluate, field_mapping, ingest, tree, webhooks

api_router = APIRouter()

# --- Routes d'authentification (publiques) ---
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

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
