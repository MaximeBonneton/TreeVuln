"""Parsing SBOM (CycloneDX/SPDX JSON) et matching composant <-> vulnérabilité.

Module pur, sans I/O (même philosophie que app/engine/cvss.py) :
- parse_sbom_file() normalise un fichier SBOM en composants exploitables ;
- (Task 3) compute_sbom_fields() calcule les champs virtuels sbom_*
  exposés aux arbres de décision.
"""
import json
from dataclasses import dataclass, field


@dataclass
class ParsedSbom:
    """Résultat normalisé du parsing d'un fichier SBOM."""

    format: str  # "cyclonedx" | "spdx"
    spec_version: str
    components: list[dict]  # {"purl", "name", "version", "component_type"}
    warnings: list[str] = field(default_factory=list)


def parse_sbom_file(content: bytes) -> ParsedSbom:
    """Parse un SBOM JSON (CycloneDX ou SPDX, auto-détection).

    Raises:
        ValueError: JSON invalide, non-objet, ou format non reconnu.
    """
    try:
        data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON: {exc}")

    if not isinstance(data, dict):
        raise ValueError("Unsupported SBOM: expected a JSON object")

    if data.get("bomFormat") == "CycloneDX":
        return _parse_cyclonedx(data)
    if "spdxVersion" in data:
        return _parse_spdx(data)
    raise ValueError(
        "Unsupported SBOM format: expected CycloneDX JSON (bomFormat) "
        "or SPDX JSON (spdxVersion)"
    )


def _parse_cyclonedx(data: dict) -> ParsedSbom:
    """CycloneDX >= 1.4 : composants dans components[]."""
    warnings: list[str] = []
    components: list[dict] = []
    for i, comp in enumerate(data.get("components") or []):
        name = str(comp.get("name") or "").strip()
        if not name:
            warnings.append(f"Component #{i} ignored: missing name")
            continue
        components.append({
            "purl": comp.get("purl") or None,
            "name": name,
            "version": comp.get("version") or None,
            "component_type": comp.get("type") or None,
        })
    return ParsedSbom(
        format="cyclonedx",
        spec_version=str(data.get("specVersion") or ""),
        components=components,
        warnings=warnings,
    )


def _parse_spdx(data: dict) -> ParsedSbom:
    """SPDX >= 2.2 : packages[], purl dans externalRefs (referenceType=purl)."""
    warnings: list[str] = []
    components: list[dict] = []
    for i, pkg in enumerate(data.get("packages") or []):
        name = str(pkg.get("name") or "").strip()
        if not name:
            warnings.append(f"Package #{i} ignored: missing name")
            continue
        purl = None
        for ref in pkg.get("externalRefs") or []:
            if ref.get("referenceType") == "purl":
                purl = ref.get("referenceLocator") or None
                break
        components.append({
            "purl": purl,
            "name": name,
            "version": pkg.get("versionInfo") or None,
            "component_type": None,
        })
    return ParsedSbom(
        format="spdx",
        spec_version=str(data.get("spdxVersion") or ""),
        components=components,
        warnings=warnings,
    )
