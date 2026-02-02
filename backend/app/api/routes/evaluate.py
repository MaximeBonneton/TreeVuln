"""
Routes API pour l'évaluation des vulnérabilités.
Support multi-arbres avec endpoints dédiés par slug.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.deps import AssetServiceDep, TreeServiceDep
from app.config import settings
from app.engine import BatchProcessor, InferenceEngine
from app.models import Tree
from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    SingleEvaluationRequest,
)
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput

router = APIRouter()


async def _get_engine_and_lookups(
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    tree_id: int | None = None,
    asset_ids: list[str] | None = None,
) -> tuple[InferenceEngine, dict[str, dict[str, dict[str, Any]]], int]:
    """
    Helper pour obtenir le moteur et les lookups.

    Args:
        tree_service: Service des arbres
        asset_service: Service des assets
        tree_id: ID de l'arbre spécifique (défaut si non fourni)
        asset_ids: Liste des asset_ids à charger

    Returns:
        Tuple (engine, lookups, tree_id)
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun arbre de décision configuré",
        )

    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    # Prépare le cache de lookup pour les assets (filtré par arbre)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids)

    return engine, lookups, tree.id


async def _get_engine_for_tree(
    tree: Tree,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    asset_ids: list[str] | None = None,
) -> tuple[InferenceEngine, dict[str, dict[str, dict[str, Any]]]]:
    """Helper pour obtenir le moteur pour un arbre spécifique."""
    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids)

    return engine, lookups


@router.post("/single", response_model=EvaluationResult)
async def evaluate_single(
    request: SingleEvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Évalue une vulnérabilité unique (temps réel).

    Utilise l'arbre par défaut. Pour un arbre spécifique, utilisez /tree/{slug}/evaluate.
    """
    # Extrait les asset_ids pour le lookup
    asset_ids = []
    if request.vulnerability.asset_id:
        asset_ids.append(request.vulnerability.asset_id)

    engine, lookups, _ = await _get_engine_and_lookups(
        tree_service, asset_service, asset_ids=asset_ids
    )

    result = engine.evaluate(
        request.vulnerability,
        lookups,
        request.include_path,
    )
    return result


@router.post("", response_model=EvaluationResponse)
async def evaluate_batch(
    request: EvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Évalue un batch de vulnérabilités.

    Utilise l'arbre par défaut. Optimisé pour traiter jusqu'à 50 000 vulnérabilités.
    """
    if len(request.vulnerabilities) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch trop grand. Maximum: {settings.max_batch_size}",
        )

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun arbre de décision configuré",
        )

    structure = tree_service.get_tree_structure(tree)

    # Extrait tous les asset_ids pour le lookup
    asset_ids = [
        v.asset_id for v in request.vulnerabilities
        if v.asset_id is not None
    ]

    # Prépare les lookups (filtrés par arbre)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        request.vulnerabilities,
        lookups,
        request.include_path,
    )
    return response


@router.post("/csv", response_model=EvaluationResponse)
async def evaluate_csv(
    file: UploadFile,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    include_path: bool = False,
):
    """
    Évalue des vulnérabilités depuis un fichier CSV.

    Le CSV doit avoir des colonnes correspondant aux champs attendus par l'arbre.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être au format CSV",
        )

    content = await file.read()

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun arbre de décision configuré",
        )

    structure = tree_service.get_tree_structure(tree)

    # Parse le CSV avec Polars
    df = BatchProcessor.from_csv(content)

    if len(df) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier trop grand ({len(df)} lignes). Maximum: {settings.max_batch_size}",
        )

    # Convertit en liste de VulnerabilityInput
    vulnerabilities = []
    for row in df.iter_rows(named=True):
        vuln = _row_to_vuln(row)
        vulnerabilities.append(vuln)

    # Prépare les lookups (filtrés par arbre)
    asset_ids = [v.asset_id for v in vulnerabilities if v.asset_id]
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        vulnerabilities,
        lookups,
        include_path,
    )
    return response


# --- Endpoint dédié par slug d'arbre ---


@router.post("/tree/{slug}", response_model=EvaluationResult)
async def evaluate_by_slug(
    slug: str,
    request: SingleEvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Évalue une vulnérabilité avec un arbre spécifique identifié par son slug.

    L'arbre doit avoir api_enabled=true et un api_slug configuré.
    """
    tree = await tree_service.get_tree_by_slug(slug)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre '{slug}' non trouvé ou API désactivée",
        )

    # Extrait les asset_ids pour le lookup
    asset_ids = []
    if request.vulnerability.asset_id:
        asset_ids.append(request.vulnerability.asset_id)

    engine, lookups = await _get_engine_for_tree(
        tree, tree_service, asset_service, asset_ids
    )

    result = engine.evaluate(
        request.vulnerability,
        lookups,
        request.include_path,
    )
    return result


@router.post("/tree/{slug}/batch", response_model=EvaluationResponse)
async def evaluate_batch_by_slug(
    slug: str,
    request: EvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Évalue un batch de vulnérabilités avec un arbre spécifique identifié par son slug.

    L'arbre doit avoir api_enabled=true et un api_slug configuré.
    """
    if len(request.vulnerabilities) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch trop grand. Maximum: {settings.max_batch_size}",
        )

    tree = await tree_service.get_tree_by_slug(slug)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre '{slug}' non trouvé ou API désactivée",
        )

    structure = tree_service.get_tree_structure(tree)

    # Extrait tous les asset_ids pour le lookup
    asset_ids = [
        v.asset_id for v in request.vulnerabilities
        if v.asset_id is not None
    ]

    # Prépare les lookups (filtrés par arbre)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        request.vulnerabilities,
        lookups,
        request.include_path,
    )
    return response


def _row_to_vuln(row: dict[str, Any]) -> VulnerabilityInput:
    """Convertit une ligne de DataFrame en VulnerabilityInput."""
    standard_fields = {
        "id", "cve_id", "cvss_score", "cvss_vector",
        "epss_score", "epss_percentile", "kev",
        "asset_id", "hostname", "ip_address",
    }
    standard_data = {k: v for k, v in row.items() if k in standard_fields}
    extra_data = {k: v for k, v in row.items() if k not in standard_fields}
    return VulnerabilityInput(**standard_data, extra=extra_data)
