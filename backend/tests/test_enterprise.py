"""
Tests pour le système Enterprise (licence, hooks, features).
"""

import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException


class TestLicenseValidation:
    """Tests de validation de la clé de licence."""

    def test_no_license_key(self):
        """Sans clé de licence, le mode Community est actif."""
        from app.enterprise.license import (
            _default_features,
            _is_valid_uuid,
            is_enterprise,
        )

        # Par défaut (pas de clé), on est en Community
        assert is_enterprise() is False

    def test_valid_uuid_format(self):
        """Un UUID v4 est accepté."""
        from app.enterprise.license import _is_valid_uuid

        key = str(uuid.uuid4())
        assert _is_valid_uuid(key) is True

    def test_invalid_uuid_format(self):
        """Une chaîne non-UUID est rejetée."""
        from app.enterprise.license import _is_valid_uuid

        assert _is_valid_uuid("not-a-uuid") is False
        assert _is_valid_uuid("") is False
        assert _is_valid_uuid("12345") is False

    def test_features_community_all_false(self):
        """En mode Community, toutes les features sont à False."""
        from app.enterprise.license import _default_features

        features = _default_features(False)
        assert all(v is False for v in features.values())

    def test_features_enterprise_all_true(self):
        """En mode Enterprise, toutes les features sont à True."""
        from app.enterprise.license import _default_features

        features = _default_features(True)
        assert all(v is True for v in features.values())

    def test_get_features_returns_copy(self):
        """get_features() retourne une copie (pas de mutation externe)."""
        from app.enterprise.license import get_features, init_license

        # S'assurer que les features sont initialisées
        init_license()
        features = get_features()
        features["sso"] = True  # Mutation de la copie
        # L'original ne doit pas changer
        assert get_features().get("sso") is False

    def test_feature_list_completeness(self):
        """La liste des features contient tous les éléments attendus."""
        from app.enterprise.license import _default_features

        expected = {
            "sso",
            "rbac",
            "visual_diff",
            "connectors_import",
            "connectors_export",
            "threat_intel_node",
            "cmdb_lookup",
            "dynamic_mapping",
            "audit_trail_advanced",
            "reporting",
            "what_if",
        }
        features = _default_features(False)
        assert set(features.keys()) == expected


class TestHooks:
    """Tests des hooks Community (implémentations par défaut)."""

    @pytest.mark.asyncio
    async def test_check_rbac_always_true(self):
        """En Community, check_rbac autorise tout."""
        from app.enterprise.hooks import check_rbac

        result = await check_rbac({}, "write", "tree")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_sso_router_returns_none(self):
        """En Community, pas de routes SSO."""
        from app.enterprise.hooks import get_sso_router

        result = await get_sso_router()
        assert result is None

    @pytest.mark.asyncio
    async def test_visual_diff_raises_402(self):
        """En Community, visual diff lève 402."""
        from app.enterprise.hooks import get_visual_diff

        with pytest.raises(HTTPException) as exc_info:
            await get_visual_diff(None, 1, 1, 2)
        assert exc_info.value.status_code == 402

    def test_import_connectors_empty(self):
        """En Community, pas de connecteurs d'import."""
        from app.enterprise.hooks import get_import_connectors

        assert get_import_connectors() == []

    def test_export_connectors_empty(self):
        """En Community, pas de connecteurs d'export."""
        from app.enterprise.hooks import get_export_connectors

        assert get_export_connectors() == []

    @pytest.mark.asyncio
    async def test_reporting_raises_402(self):
        """En Community, le reporting lève 402."""
        from app.enterprise.hooks import get_multi_tree_report

        with pytest.raises(HTTPException) as exc_info:
            await get_multi_tree_report(None, [1, 2])
        assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_decision_certificate_raises_402(self):
        """En Community, les certificats de décision lèvent 402."""
        from app.enterprise.hooks import generate_decision_certificate

        with pytest.raises(HTTPException) as exc_info:
            await generate_decision_certificate(None, 1, "pdf")
        assert exc_info.value.status_code == 402
