"""
Tests pour l'infrastructure de migrations Alembic (B-14, plan WS3-R Task 1).

Il n'existe pas encore de fixture Postgres réelle dans les tests : on
vérifie donc ici (a) que la configuration Alembic et l'historique de
migrations se chargent, (b) la parité modèles <-> baseline par introspection
du source de la migration. L'application réelle des migrations (base vierge
et base legacy stampée) est vérifiée manuellement via docker compose,
cf. plan 2026-07-16-ws3r-review-fixes.md.
"""

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

import app.models  # noqa: F401  (peuple Base.metadata)
from app.database import Base

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASELINE_PATH = BACKEND_DIR / "alembic" / "versions" / "0001_baseline.py"


class TestAlembicConfig:
    """La configuration et l'historique Alembic sont chargeables."""

    def test_config_and_history_load(self):
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)

        # La baseline 0001 est l'unique racine de l'historique
        assert list(script.get_bases()) == ["0001"]
        # Historique linéaire (une seule head), chargé sans erreur
        assert len(script.get_heads()) == 1

    def test_baseline_file_exists(self):
        assert BASELINE_PATH.is_file()


class TestBaselineCoversAllModels:
    """
    Parité modèles <-> baseline : chaque table déclarée dans Base.metadata
    doit être créée par la migration baseline. Encode la leçon du constat #1
    de la revue 2026-07-16 : un modèle ORM modifié sans migration ne change
    rien sur une base réelle.
    """

    def test_every_model_table_is_created_by_a_migration(self):
        # Une table peut naître après la baseline (ex: app_settings en 0004) :
        # on scanne l'ensemble des migrations, pas seulement 0001.
        versions_dir = BACKEND_DIR / "alembic" / "versions"
        sources = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(versions_dir.glob("*.py"))
        )
        missing = [
            table_name
            for table_name in Base.metadata.tables
            if not re.search(
                rf"create_table\(\s*['\"]{re.escape(table_name)}['\"]", sources
            )
        ]
        assert not missing, f"Tables absentes des migrations Alembic : {missing}"

    def test_partial_unique_index_on_default_tree(self):
        # C-5 : l'index unique partiel sur trees.is_default doit être dans la
        # baseline (l'autogénération Alembic peut rater les index partiels).
        source = BASELINE_PATH.read_text(encoding="utf-8")
        assert "idx_trees_default" in source
        assert "postgresql_where" in source
