"""Tests du service de settings globaux (table app_settings)."""

import pytest
from sqlalchemy.dialects.postgresql import JSONB

from app.models.settings import AppSetting
from app.services.settings_service import SettingsService

pytestmark = pytest.mark.asyncio


class TestAppSettingModel:
    def test_key_est_cle_primaire(self):
        assert AppSetting.__table__.columns["key"].primary_key is True

    def test_value_est_jsonb(self):
        assert isinstance(AppSetting.__table__.columns["value"].type, JSONB)


class TestSettingsService:
    async def test_get_setting_absent_retourne_none(self, db_session):
        service = SettingsService(db_session)
        assert await service.get_setting("csaf") is None

    async def test_set_puis_get(self, db_session):
        service = SettingsService(db_session)
        await service.set_setting("csaf", {"publisher": {"name": "ACME"}})
        value = await service.get_setting("csaf")
        assert value == {"publisher": {"name": "ACME"}}

    async def test_set_ecrase_la_valeur_existante(self, db_session):
        service = SettingsService(db_session)
        await service.set_setting("csaf", {"a": 1})
        await service.set_setting("csaf", {"b": 2})
        assert await service.get_setting("csaf") == {"b": 2}
