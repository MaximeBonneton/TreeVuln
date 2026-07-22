"""Service d'accès aux settings applicatifs globaux (table app_settings)."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import AppSetting

# Clé du bloc de settings CSAF (identité éditeur + clé de signature)
CSAF_SETTINGS_KEY = "csaf"

# Clé du bloc de settings ENISA (identité fabricant pour le pré-remplissage des jalons)
ENISA_SETTINGS_KEY = "enisa"


class SettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_setting(self, key: str) -> dict[str, Any] | None:
        """Retourne la valeur d'un setting, ou None s'il n'existe pas."""
        result = await self.db.execute(
            select(AppSetting.value).where(AppSetting.key == key)
        )
        row = result.scalar_one_or_none()
        return row

    async def set_setting(self, key: str, value: dict[str, Any]) -> None:
        """Crée ou remplace un setting (upsert PostgreSQL)."""
        stmt = pg_insert(AppSetting).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AppSetting.key],
            set_={"value": value},
        )
        await self.db.execute(stmt)
        await self.db.commit()
