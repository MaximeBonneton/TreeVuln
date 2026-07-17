"""Service SBOM : persistance (remplacement complet par asset) et caches.

Le parsing des fichiers est délégué à app.engine.sbom (fonctions pures) ;
ce service ne fait que l'I/O base de données.
"""
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.sbom import ParsedSbom
from app.models.asset import Asset
from app.models.sbom import Sbom, SbomComponent


class SbomService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def replace_sbom(
        self, asset_pk: int, parsed: ParsedSbom, filename: str | None
    ) -> Sbom:
        """Remplace le SBOM de l'asset (delete + insert, une transaction)."""
        await self.db.execute(delete(Sbom).where(Sbom.asset_id == asset_pk))
        sbom = Sbom(
            asset_id=asset_pk,
            format=parsed.format,
            spec_version=parsed.spec_version[:20],
            filename=filename,
            component_count=len(parsed.components),
        )
        self.db.add(sbom)
        await self.db.flush()  # obtient sbom.id avant les composants
        self.db.add_all(
            SbomComponent(
                sbom_id=sbom.id,
                purl=comp["purl"],
                name=comp["name"][:500],
                version=(comp["version"] or "")[:255] or None,
                component_type=comp["component_type"],
            )
            for comp in parsed.components
        )
        await self.db.commit()
        await self.db.refresh(sbom)
        return sbom

    async def get_sbom(self, asset_pk: int) -> Sbom | None:
        result = await self.db.execute(select(Sbom).where(Sbom.asset_id == asset_pk))
        return result.scalar_one_or_none()

    async def get_components(
        self, sbom_id: int, limit: int, offset: int
    ) -> tuple[list[SbomComponent], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(SbomComponent).where(
                SbomComponent.sbom_id == sbom_id
            )
        )
        result = await self.db.execute(
            select(SbomComponent)
            .where(SbomComponent.sbom_id == sbom_id)
            .order_by(SbomComponent.name, SbomComponent.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def delete_sbom(self, asset_pk: int) -> bool:
        """Supprime le SBOM de l'asset. False s'il n'y en avait pas."""
        result = await self.db.execute(delete(Sbom).where(Sbom.asset_id == asset_pk))
        await self.db.commit()
        return (result.rowcount or 0) > 0

    async def get_components_cache(
        self, tree_id: int, asset_ids: list[str] | None
    ) -> dict[str, list[dict[str, Any]]]:
        """Cache {asset_id métier: [composants]} pour le moteur d'inférence.

        Un asset avec SBOM mais sans composant apparaît avec une liste vide
        (réponse ferme False), un asset sans SBOM n'apparaît pas (None -> null).
        """
        stmt = (
            select(Asset.asset_id, SbomComponent.purl, SbomComponent.name,
                   SbomComponent.version)
            .join(Sbom, Sbom.asset_id == Asset.id)
            .outerjoin(SbomComponent, SbomComponent.sbom_id == Sbom.id)
            .where(Asset.tree_id == tree_id)
        )
        if asset_ids:
            stmt = stmt.where(Asset.asset_id.in_(asset_ids))
        result = await self.db.execute(stmt)

        cache: dict[str, list[dict[str, Any]]] = {}
        for business_id, purl, name, version in result:
            bucket = cache.setdefault(business_id, [])
            if name is not None:  # ligne du outer join sans composant
                bucket.append({"purl": purl, "name": name, "version": version})
        return cache

    async def get_tree_summary(self, tree_id: int) -> list[dict[str, Any]]:
        """Assets de l'arbre ayant un SBOM (pour les badges de l'UI)."""
        result = await self.db.execute(
            select(Asset.asset_id, Sbom.format, Sbom.component_count, Sbom.imported_at)
            .join(Sbom, Sbom.asset_id == Asset.id)
            .where(Asset.tree_id == tree_id)
            .order_by(Asset.asset_id)
        )
        return [
            {"asset_id": r[0], "format": r[1], "component_count": r[2],
             "imported_at": r[3]}
            for r in result
        ]
