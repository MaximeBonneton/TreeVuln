"""
Tests unitaires pour le fix C-5 (audit 2026-07-16) : arbre par défaut unique.

Contexte : set_default_tree() faisait un read-modify-write objet par objet sans
verrou ni contrainte d'unicité en base -> deux admins concurrents pouvaient créer
deux arbres is_default=True, ce qui casse get_tree()/get_default_tree()
(scalar_one_or_none -> MultipleResultsFound -> 500 sur tout /evaluate).

Le fix combine :
- un index unique partiel en base (idx_trees_default) sur trees.is_default
  WHERE is_default = true,
- une réécriture atomique de set_default_tree() en deux UPDATE (désactivation
  globale puis activation ciblée) dans la même transaction, dont les verrous de
  ligne sérialisent les appels concurrents.

Note : le projet ne dispose pas encore de fixture DB réelle (Postgres) pour les
tests backend - toute la couche SQLAlchemy est mockée ici (session AsyncMock).
Ces tests vérifient donc la forme des requêtes émises, mais PAS l'application
effective de l'index unique partiel côté Postgres (contrainte réellement
testable seulement avec une vraie base). Une vérification bout-en-bout
nécessitera la fixture DB prévue en WS5.
"""

from unittest.mock import AsyncMock, MagicMock

from app.models import Tree
from app.services.tree_service import TreeService


def _make_service_with_mock_session() -> TreeService:
    """Construit un TreeService dont la session DB est entièrement mockée."""
    service = TreeService.__new__(TreeService)
    service.db = AsyncMock()
    service.db.execute = AsyncMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()
    return service


class TestSetDefaultTreeAtomicity:
    """
    set_default_tree doit basculer l'ancien défaut à False et le nouveau à True
    via deux UPDATE atomiques dans la même transaction (pas de read-modify-write
    objet par objet), afin d'éviter la race condition entre deux admins
    concurrents.
    """

    async def test_emits_two_update_statements_before_commit(self):
        tree = MagicMock(spec=Tree)
        tree.id = 42
        tree.is_default = False

        service = _make_service_with_mock_session()
        service.get_tree = AsyncMock(return_value=tree)

        result = await service.set_default_tree(42)

        assert result is tree
        # Deux appels execute() : un UPDATE pour désactiver l'ancien défaut,
        # un UPDATE pour activer le nouveau.
        assert service.db.execute.await_count == 2

        first_stmt = service.db.execute.await_args_list[0].args[0]
        second_stmt = service.db.execute.await_args_list[1].args[0]

        assert first_stmt.is_update
        assert second_stmt.is_update

        # Premier UPDATE : cible trees.is_default = true (désactivation globale)
        first_compiled = first_stmt.compile()
        assert "trees" in str(first_compiled)
        assert "is_default" in str(first_compiled)

        # Un seul commit, exécuté après les deux UPDATE
        service.db.commit.assert_awaited_once()
        service.db.refresh.assert_awaited_once_with(tree)

    async def test_no_update_when_tree_does_not_exist(self):
        """Si l'arbre ciblé n'existe pas, aucun UPDATE ne doit être émis."""
        service = _make_service_with_mock_session()
        service.get_tree = AsyncMock(return_value=None)

        result = await service.set_default_tree(999)

        assert result is None
        service.db.execute.assert_not_awaited()
        service.db.commit.assert_not_awaited()

    async def test_call_order_is_deactivate_then_activate_then_commit(self):
        """
        Vérifie l'ordre exact des opérations : désactivation globale d'abord,
        puis activation ciblée, puis commit - jamais l'inverse (sinon on
        risquerait de désactiver l'arbre qu'on vient d'activer).
        """
        tree = MagicMock(spec=Tree)
        tree.id = 7
        tree.is_default = False

        service = _make_service_with_mock_session()
        service.get_tree = AsyncMock(return_value=tree)

        call_order: list[str] = []

        # Utilisation de coroutines factices pour tracer l'ordre sans casser l'await
        async def fake_execute(stmt):
            call_order.append("execute")
            return MagicMock()

        async def fake_commit():
            call_order.append("commit")

        service.db.execute = AsyncMock(side_effect=fake_execute)
        service.db.commit = AsyncMock(side_effect=fake_commit)

        await service.set_default_tree(7)

        assert call_order == ["execute", "execute", "commit"]


class TestTreeDefaultPartialUniqueIndex:
    """Vérifie que l'index unique partiel est bien déclaré sur le modèle Tree."""

    def test_trees_table_has_partial_unique_default_index(self):
        index_names = {idx.name for idx in Tree.__table__.indexes}
        assert "idx_trees_default" in index_names
        idx = next(i for i in Tree.__table__.indexes if i.name == "idx_trees_default")
        assert idx.unique is True
