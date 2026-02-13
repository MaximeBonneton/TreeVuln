from fastapi import APIRouter

from app.api.routes import assets, evaluate, field_mapping, tree

api_router = APIRouter()

api_router.include_router(tree.router, prefix="/tree", tags=["Tree"])
api_router.include_router(evaluate.router, prefix="/evaluate", tags=["Evaluate"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(field_mapping.router, prefix="/tree", tags=["Field Mapping"])
api_router.include_router(field_mapping.global_router, prefix="/mapping", tags=["Field Mapping"])
