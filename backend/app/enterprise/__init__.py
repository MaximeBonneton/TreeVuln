"""
Auto-detection and initialization of Enterprise modules.
If the license is valid and the modules/ folder contains code,
Community hooks are replaced by Enterprise implementations.
"""

import logging

from app.enterprise import hooks
from app.enterprise.license import init_license, is_enterprise

logger = logging.getLogger(__name__)

# List of expected hooks — used to verify that register_hooks replaced them all
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
    """Called once at startup (FastAPI lifespan)."""
    init_license()

    if not is_enterprise():
        return

    # Import and register Enterprise implementations
    try:
        from app.enterprise.modules import register_hooks

        register_hooks(hooks)
    except ImportError:
        logger.error(
            "Enterprise modules not loadable — falling back to Community mode"
        )
        return

    # Check which hooks have been replaced
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
