"""
Auto-détection et initialisation des modules Enterprise.
Si la licence est valide et que le dossier modules/ contient du code,
les hooks Community sont remplacés par les implémentations Enterprise.
"""

import logging

from app.enterprise import hooks
from app.enterprise.license import init_license, is_enterprise

logger = logging.getLogger(__name__)

# Liste des hooks attendus — sert à vérifier que register_hooks les a tous remplacés
EXPECTED_HOOKS = [
    "check_rbac",
    "get_sso_router",
    "get_visual_diff",
    "get_import_connectors",
    "get_export_connectors",
    "get_multi_tree_report",
    "generate_decision_certificate",
]


def init_enterprise() -> None:
    """Appelée une seule fois au démarrage (lifespan de FastAPI)."""
    init_license()

    if not is_enterprise():
        return

    # Importer et enregistrer les implémentations Enterprise
    try:
        from app.enterprise.modules import register_hooks

        register_hooks(hooks)
    except ImportError:
        logger.error(
            "Enterprise modules not loadable — falling back to Community mode"
        )
        return

    # Vérifier quels hooks ont été remplacés
    replaced = []
    for hook_name in EXPECTED_HOOKS:
        fn = getattr(hooks, hook_name, None)
        if fn and fn.__module__ != "app.enterprise.hooks":
            replaced.append(hook_name)
    logger.info("Enterprise hooks registered: %s", replaced)

    missing = set(EXPECTED_HOOKS) - set(replaced)
    if missing:
        logger.warning(
            "Enterprise hooks NOT replaced (using Community defaults): %s", missing
        )
