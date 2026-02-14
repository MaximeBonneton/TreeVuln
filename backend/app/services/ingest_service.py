"""
Service pour la gestion des webhooks entrants (endpoints d'ingestion).
"""

import logging
import secrets
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import InferenceEngine
from app.models.ingest import IngestEndpoint, IngestLog
from app.schemas.ingest import IngestEndpointCreate, IngestEndpointUpdate, IngestResult
from app.schemas.vulnerability import VulnerabilityInput

logger = logging.getLogger(__name__)


class IngestService:
    """Service de gestion des endpoints d'ingestion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_endpoints(self, tree_id: int) -> list[IngestEndpoint]:
        """Liste les endpoints d'un arbre."""
        result = await self.db.execute(
            select(IngestEndpoint)
            .where(IngestEndpoint.tree_id == tree_id)
            .order_by(IngestEndpoint.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_endpoint(self, endpoint_id: int) -> IngestEndpoint | None:
        """Récupère un endpoint par son ID."""
        result = await self.db.execute(
            select(IngestEndpoint).where(IngestEndpoint.id == endpoint_id)
        )
        return result.scalar_one_or_none()

    async def get_endpoint_by_slug(self, slug: str) -> IngestEndpoint | None:
        """Récupère un endpoint par son slug."""
        result = await self.db.execute(
            select(IngestEndpoint).where(
                IngestEndpoint.slug == slug,
                IngestEndpoint.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_endpoint(self, tree_id: int, data: IngestEndpointCreate) -> IngestEndpoint:
        """Crée un nouveau endpoint d'ingestion avec une clé API générée."""
        endpoint = IngestEndpoint(
            tree_id=tree_id,
            name=data.name,
            slug=data.slug,
            api_key=generate_api_key(),
            field_mapping=data.field_mapping,
            is_active=data.is_active,
            auto_evaluate=data.auto_evaluate,
        )
        self.db.add(endpoint)
        await self.db.commit()
        await self.db.refresh(endpoint)
        return endpoint

    async def update_endpoint(
        self, endpoint_id: int, data: IngestEndpointUpdate
    ) -> IngestEndpoint | None:
        """Met à jour un endpoint."""
        endpoint = await self.get_endpoint(endpoint_id)
        if not endpoint:
            return None

        if data.name is not None:
            endpoint.name = data.name
        if data.slug is not None:
            endpoint.slug = data.slug
        if data.field_mapping is not None:
            endpoint.field_mapping = data.field_mapping
        if data.is_active is not None:
            endpoint.is_active = data.is_active
        if data.auto_evaluate is not None:
            endpoint.auto_evaluate = data.auto_evaluate

        await self.db.commit()
        await self.db.refresh(endpoint)
        return endpoint

    async def delete_endpoint(self, endpoint_id: int) -> bool:
        """Supprime un endpoint."""
        endpoint = await self.get_endpoint(endpoint_id)
        if not endpoint:
            return False
        await self.db.delete(endpoint)
        await self.db.commit()
        return True

    async def regenerate_key(self, endpoint_id: int) -> IngestEndpoint | None:
        """Régénère la clé API d'un endpoint."""
        endpoint = await self.get_endpoint(endpoint_id)
        if not endpoint:
            return None
        endpoint.api_key = generate_api_key()
        await self.db.commit()
        await self.db.refresh(endpoint)
        return endpoint

    async def get_logs(self, endpoint_id: int, limit: int = 50) -> list[IngestLog]:
        """Récupère les logs de réception."""
        result = await self.db.execute(
            select(IngestLog)
            .where(IngestLog.endpoint_id == endpoint_id)
            .order_by(IngestLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def ingest(
        self,
        endpoint: IngestEndpoint,
        payload: list[dict[str, Any]],
        engine: InferenceEngine,
        lookups: dict[str, dict[str, dict[str, Any]]],
        source_ip: str | None = None,
    ) -> IngestResult:
        """
        Ingère un batch de vulnérabilités, applique le mapping, évalue si configuré.

        Args:
            endpoint: Endpoint d'ingestion
            payload: Liste de vulnérabilités brutes
            engine: Moteur d'inférence pré-chargé
            lookups: Tables de lookup pré-chargées
            source_ip: IP source de la requête

        Returns:
            Résultat de l'ingestion
        """
        start = time.monotonic()
        results: list[dict[str, Any]] = []
        success_count = 0
        error_count = 0

        for entry in payload:
            try:
                # Applique le mapping de champs
                mapped = transform_payload(entry, endpoint.field_mapping)

                if endpoint.auto_evaluate:
                    vuln = _build_vulnerability(mapped)
                    eval_result = engine.evaluate(vuln, lookups, include_path=True)
                    results.append(eval_result.model_dump())
                    if not eval_result.error:
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    success_count += 1
                    results.append({"status": "received", "data": mapped})
            except Exception as e:
                error_count += 1
                results.append({"status": "error", "error": str(e)})

        duration_ms = int((time.monotonic() - start) * 1000)

        # Log la réception
        log = IngestLog(
            endpoint_id=endpoint.id,
            source_ip=source_ip,
            payload_size=len(str(payload)),
            vuln_count=len(payload),
            success_count=success_count,
            error_count=error_count,
            duration_ms=duration_ms,
        )
        self.db.add(log)
        await self.db.commit()

        return IngestResult(
            received=len(payload),
            evaluated=success_count + error_count,
            errors=error_count,
            results=results,
        )


def generate_api_key() -> str:
    """Génère une clé API aléatoire."""
    return secrets.token_urlsafe(32)


def transform_payload(entry: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """
    Applique le mapping de champs sur une entrée.

    Le mapping est au format {champ_source: champ_treevuln}.
    Les champs non mappés sont passés tels quels.
    """
    if not mapping:
        return entry

    result: dict[str, Any] = {}
    mapped_source_keys = set(mapping.keys())

    for source_key, target_key in mapping.items():
        if source_key in entry:
            result[target_key] = entry[source_key]

    # Conserve les champs non mappés
    for key, value in entry.items():
        if key not in mapped_source_keys and key not in result:
            result[key] = value

    return result


def _build_vulnerability(data: dict[str, Any]) -> VulnerabilityInput:
    """Construit un VulnerabilityInput depuis un dict mappé."""
    standard_fields = {
        "id", "cve_id", "cvss_score", "cvss_vector",
        "epss_score", "epss_percentile", "kev",
        "asset_id", "hostname", "ip_address", "asset_criticality",
    }
    standard_data = {k: v for k, v in data.items() if k in standard_fields}
    extra_data = {k: v for k, v in data.items() if k not in standard_fields}
    return VulnerabilityInput(**standard_data, extra=extra_data)
