"""
Test unitaire pour le fix C-9 (audit 2026-07-16) : lazy loading des assets.

Contexte : Tree.assets était en lazy="selectin" -> chaque select(Tree) (donc
chaque /evaluate/single, /evaluate, list_trees, ingest...) déclenchait le
chargement de TOUS les assets de l'arbre, même sans lookup. Le champ est
maintenant lazy="noload" ; les appelants qui ont réellement besoin des assets
(ex: duplicate_tree) doivent utiliser selectinload(Tree.assets) explicitement.

Note : comme pour C-5, aucune fixture DB réelle n'existe encore dans ce projet
pour vérifier au runtime qu'un select(Tree) ne déclenche pas de requête assets
supplémentaire. Ce test vérifie la configuration déclarative du mapping
SQLAlchemy, qui est la source de vérité du comportement de chargement.
"""

from app.models import Tree


def test_assets_relationship_is_noload():
    relationship_prop = Tree.__mapper__.relationships["assets"]
    assert relationship_prop.lazy == "noload", (
        "Tree.assets doit être lazy='noload' pour éviter le chargement "
        "systématique des assets sur chaque select(Tree) - voir fix C-9. "
        "Utiliser selectinload(Tree.assets) explicitement là où nécessaire."
    )
