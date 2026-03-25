"""
Enterprise license verification.
Double condition: valid UUID key AND modules/ present.
Note: init_license() will need to become async during JWT migration.
"""

import logging
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_enterprise_active: bool = False
_enterprise_version: str | None = None
_features: dict[str, bool] = {}


def _is_valid_uuid(key: str) -> bool:
    """Validate that the key is a well-formed UUID v4."""
    try:
        uuid.UUID(key, version=4)
        return True
    except ValueError:
        return False


def init_license() -> None:
    """Called at startup (lifespan). Verifies key + presence of modules/."""
    global _enterprise_active, _enterprise_version, _features
    key = settings.treevuln_license_key

    if not key:
        logger.info("No license key configured — running in Community mode")
        _enterprise_active = False
        _features = _default_features(False)
        return

    # Validate UUID v4 format
    if not _is_valid_uuid(key):
        logger.warning("Invalid license key format — running in Community mode")
        _enterprise_active = False
        _features = _default_features(False)
        return

    # Check for the presence of the modules/ folder
    modules_path = Path(__file__).parent / "modules"
    modules_present = (modules_path / "__init__.py").exists()

    if not modules_present:
        logger.warning(
            "License key present but enterprise modules not found — running in Community mode"
        )
        _enterprise_active = False
        _features = _default_features(False)
        return

    _enterprise_active = True
    _features = _default_features(True)

    # Read the enterprise modules version if available
    try:
        from app.enterprise.modules import __version__ as mod_version

        _enterprise_version = mod_version
    except (ImportError, AttributeError):
        _enterprise_version = "unknown"

    logger.info("Enterprise mode activated (modules version: %s)", _enterprise_version)


def is_enterprise() -> bool:
    return _enterprise_active


def get_enterprise_version() -> str | None:
    return _enterprise_version


def get_features() -> dict[str, bool]:
    return _features.copy()


def _default_features(enterprise: bool) -> dict[str, bool]:
    return {
        "sso": enterprise,
        "rbac": enterprise,
        "visual_diff": enterprise,
        "connectors_import": enterprise,
        "connectors_export": enterprise,
        "threat_intel_node": enterprise,
        "cmdb_lookup": enterprise,
        "dynamic_mapping": enterprise,
        "audit_trail_advanced": enterprise,
        "reporting": enterprise,
        "what_if": enterprise,
    }
