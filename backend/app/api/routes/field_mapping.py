"""
Routes API pour la gestion du mapping des champs.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import TreeServiceDep
from app.engine.cvss import get_cvss_field_definitions
from app.schemas.field_mapping import (
    FieldDefinition,
    FieldMapping,
    FieldMappingUpdate,
    ScanResult,
)
from app.services import field_mapping_service

router = APIRouter()


@router.get("/{tree_id}/mapping", response_model=FieldMapping | None)
async def get_mapping(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """
    Récupère le mapping des champs pour un arbre.

    Retourne null si aucun mapping n'est configuré.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )

    structure = tree_service.get_tree_structure(tree)
    return field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)


@router.put("/{tree_id}/mapping", response_model=FieldMapping)
async def update_mapping(
    tree_id: int,
    data: FieldMappingUpdate,
    tree_service: TreeServiceDep,
):
    """
    Met à jour le mapping des champs pour un arbre.

    Le mapping est stocké dans les métadonnées de l'arbre.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )

    structure = tree_service.get_tree_structure(tree)

    # Récupère le mapping existant pour obtenir la version
    existing = field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)
    new_version = (existing.version + 1) if existing else 1

    # Crée le nouveau mapping
    new_mapping = FieldMapping(
        fields=data.fields,
        source=data.source,
        version=new_version,
    )

    # Met à jour les métadonnées
    structure.metadata = field_mapping_service.set_mapping_in_tree_metadata(
        structure.metadata, new_mapping
    )

    # Sauvegarde sans créer de version (modification de métadonnées)
    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )

    return new_mapping


@router.post("/{tree_id}/mapping/import", response_model=FieldMapping)
async def import_mapping(
    tree_id: int,
    file: UploadFile = File(...),
    tree_service: TreeServiceDep = None,
):
    """
    Importe un mapping depuis un fichier JSON.

    Le fichier doit contenir un objet avec une liste de FieldDefinition.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )

    # Lit le fichier
    content = await file.read()
    try:
        import json

        mapping_data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier JSON invalide: {e}",
        )

    # Valide le mapping
    try:
        # Accepte soit un FieldMapping complet, soit juste une liste de fields
        if isinstance(mapping_data, list):
            mapping_data = {"fields": mapping_data}
        imported_mapping = FieldMapping.model_validate(mapping_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format de mapping invalide: {e}",
        )

    # Met à jour avec la source appropriée
    structure = tree_service.get_tree_structure(tree)
    existing = field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)
    new_version = (existing.version + 1) if existing else 1

    new_mapping = FieldMapping(
        fields=imported_mapping.fields,
        source=f"import:{file.filename or 'unknown'}",
        version=new_version,
    )

    structure.metadata = field_mapping_service.set_mapping_in_tree_metadata(
        structure.metadata, new_mapping
    )

    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )

    return new_mapping


@router.delete("/{tree_id}/mapping", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """
    Supprime le mapping des champs pour un arbre.

    Les nœuds existants conservent leurs configurations mais les
    utilisateurs devront à nouveau saisir manuellement les noms de champs.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )

    structure = tree_service.get_tree_structure(tree)
    structure.metadata = field_mapping_service.remove_mapping_from_tree_metadata(
        structure.metadata
    )

    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )


@router.post("/scan", response_model=ScanResult)
async def scan_file(
    file: UploadFile = File(...),
):
    """
    Scanne un fichier CSV ou JSON pour détecter les champs disponibles.

    Analyse jusqu'à 100 lignes pour inférer les types et collecter des exemples.
    Le résultat peut être utilisé pour créer ou mettre à jour un mapping.

    Formats supportés:
    - CSV avec en-têtes
    - JSON (array d'objets ou objet avec une clé contenant un array)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier requis",
        )

    content = await file.read()
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être encodé en UTF-8",
        )

    result = field_mapping_service.scan_file_content(content_str, file.filename)
    return result


@router.get("/cvss-fields", response_model=list[FieldDefinition])
async def get_cvss_fields():
    """
    Retourne les définitions des champs CVSS virtuels.

    Ces champs sont extraits automatiquement du vecteur CVSS (cvss_vector)
    lors de l'évaluation. Ils permettent de créer des conditions sur les
    métriques individuelles (Attack Vector, Attack Complexity, etc.).

    Supporte CVSS 3.1 et 4.0.
    """
    return get_cvss_field_definitions()
