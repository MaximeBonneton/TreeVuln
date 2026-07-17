"""Tests des modèles SBOM (structure, contraintes)."""

from sqlalchemy import Text

from app.models.sbom import Sbom, SbomComponent


class TestSbomModel:
    def test_asset_id_unique(self):
        # Un seul SBOM par asset : le dernier import remplace le précédent
        assert Sbom.__table__.columns["asset_id"].unique is True

    def test_asset_fk_cascade(self):
        fk = next(iter(Sbom.__table__.columns["asset_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"


class TestSbomComponentModel:
    def test_sbom_fk_cascade(self):
        fk = next(iter(SbomComponent.__table__.columns["sbom_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_purl_est_text_nullable(self):
        col = SbomComponent.__table__.columns["purl"]
        assert isinstance(col.type, Text)
        assert col.nullable is True

    def test_indexes_presents(self):
        index_names = {idx.name for idx in SbomComponent.__table__.indexes}
        assert "idx_sbom_components_purl" in index_names
        assert "idx_sbom_components_name" in index_names
