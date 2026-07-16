"""Orchestration de l'export CSAF : settings -> génération -> signature -> ZIP."""
import io
import json
import logging
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.crypto import decrypt_secret
from app.engine.csaf import build_csaf_document
from app.schemas.evaluation import EvaluationResult
from app.schemas.tree import TreeStructure
from app.services.csaf_signing import compute_hashes, sign_detached
from app.services.settings_service import CSAF_SETTINGS_KEY, SettingsService

logger = logging.getLogger(__name__)


class CsafExportConfigError(Exception):
    """Configuration insuffisante ou aucun item exportable (-> 422)."""


class CsafSigningKeyMissingError(Exception):
    """signed=true demandé sans clé de signature configurée (-> 409)."""


def _tracking_id(namespace: str) -> str:
    """Identifiant de tracking : {slug-du-host-du-namespace}-{uuid4}."""
    host = urlparse(namespace).netloc or "treevuln"
    slug = re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
    return f"{slug}-{uuid.uuid4()}"


async def build_csaf_export(
    results: list[EvaluationResult],
    raw_rows: list[dict[str, Any]],
    structure: TreeStructure,
    asset_cache: dict[str, dict[str, Any]],
    settings_service: SettingsService,
    signed: bool,
) -> tuple[bytes, str]:
    """Construit le bundle ZIP CSAF pour un batch évalué.

    Returns:
        (bytes du ZIP, nom de fichier "{tracking_id}.zip")

    Raises:
        CsafExportConfigError: settings éditeur absents / aucun item exportable.
        CsafSigningKeyMissingError: signed=True sans clé configurée.
        SigningError: échec gpg (l'appelant la laisse remonter en 500).
    """
    stored = await settings_service.get_setting(CSAF_SETTINGS_KEY) or {}
    publisher = stored.get("publisher")
    if not publisher or not publisher.get("name") or not publisher.get("namespace"):
        raise CsafExportConfigError(
            "CSAF publisher settings are not configured "
            "(set them via PUT /api/v1/settings/csaf)"
        )

    signing_key_enc = stored.get("signing_key")
    if signed and not signing_key_enc:
        raise CsafSigningKeyMissingError(
            "No signing key configured. Configure one or pass signed=false."
        )

    document, exclusions = build_csaf_document(
        items=list(zip(results, raw_rows)),
        assets=asset_cache,
        structure=structure,
        publisher=publisher,
        tracking_id=_tracking_id(publisher["namespace"]),
        generated_at=datetime.now(timezone.utc),
    )
    if document is None:
        raise CsafExportConfigError(
            "No exportable item in the batch "
            f"({len(exclusions)} excluded — check vex_status on output nodes, "
            "asset_id resolution and cve_id fields)"
        )

    tracking_id = document["document"]["tracking"]["id"]
    doc_name = f"{tracking_id}.json"
    doc_bytes = json.dumps(document, indent=2, ensure_ascii=False).encode("utf-8")

    # La signature est calculée AVANT d'ouvrir le ZIP : un échec gpg ne
    # produit aucun ZIP partiel.
    signature: str | None = None
    if signed:
        passphrase_enc = stored.get("signing_key_passphrase")
        signature = sign_detached(
            doc_bytes,
            decrypt_secret(signing_key_enc),
            decrypt_secret(passphrase_enc) if passphrase_enc else None,
        )

    sha256, sha512 = compute_hashes(doc_bytes)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(doc_name, doc_bytes)
        if signature is not None:
            zf.writestr(f"{doc_name}.asc", signature)
        zf.writestr(f"{doc_name}.sha256", f"{sha256}  {doc_name}\n")
        zf.writestr(f"{doc_name}.sha512", f"{sha512}  {doc_name}\n")
        if exclusions:
            zf.writestr(
                "exclusions.json",
                json.dumps(
                    [{"vuln_id": e.vuln_id, "reason": e.reason} for e in exclusions],
                    indent=2,
                    ensure_ascii=False,
                ),
            )

    return buffer.getvalue(), f"{tracking_id}.zip"
