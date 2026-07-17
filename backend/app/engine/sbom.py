"""Parsing SBOM (CycloneDX/SPDX JSON) et matching composant <-> vulnérabilité.

Module pur, sans I/O (même philosophie que app/engine/cvss.py) :
- parse_sbom_file() normalise un fichier SBOM en composants exploitables ;
- (Task 3) compute_sbom_fields() calcule les champs virtuels sbom_*
  exposés aux arbres de décision.
"""
import json
from dataclasses import dataclass, field
from typing import Any

from app.schemas.field_mapping import FieldDefinition, FieldType


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


# Champs virtuels exposés aux arbres (calculés à l'évaluation)
SBOM_FIELDS: tuple[str, ...] = (
    "sbom_component_present",
    "sbom_name_present",
    "sbom_component_version",
    "sbom_match_type",
)


def is_sbom_field(field: str) -> bool:
    """Le champ est-il un champ virtuel SBOM ?"""
    return field in SBOM_FIELDS


def parse_purl(purl: str) -> tuple[str | None, str | None]:
    """Extrait (name, version) d'un purl. (None, None) si non parsable.

    Format : pkg:type/namespace/name@version?qualifiers#subpath
    """
    if not purl.startswith("pkg:"):
        return None, None
    body = purl[4:].split("#", 1)[0].split("?", 1)[0]
    version: str | None = None
    if "@" in body:
        body, version = body.rsplit("@", 1)
    name = body.rstrip("/").rsplit("/", 1)[-1]
    return (name or None), (version or None)


def normalize_purl(purl: str) -> str:
    """Forme canonique pour comparaison : sans qualifiers/subpath,
    tout en minuscules sauf la version (sensible à la casse)."""
    base = purl.strip().split("#", 1)[0].split("?", 1)[0]
    if "@" in base:
        head, version = base.rsplit("@", 1)
        return f"{head.lower()}@{version}"
    return base.lower()


def _vuln_get(vuln: dict[str, Any], field: str) -> Any:
    """Lit un champ de la vuln (champs standards puis extra)."""
    value = vuln.get(field)
    if value is None:
        extra = vuln.get("extra") or {}
        value = extra.get(field)
    return value


@dataclass
class ComponentIndex:
    """Index de matching pré-calculé pour les composants d'un SBOM.

    Construit une fois par asset (au chargement du cache) pour éviter de
    re-normaliser chaque purl à chaque évaluation : le matching devient O(1)
    par vulnérabilité au lieu de O(nb composants).
    """

    purls: set[str]                       # purls normalisés
    versions_by_name: dict[str, list[str | None]]  # nom lowercase -> versions


def build_component_index(components: list[dict]) -> ComponentIndex:
    """Construit l'index de matching depuis les composants normalisés."""
    purls: set[str] = set()
    versions_by_name: dict[str, list[str | None]] = {}
    for comp in components:
        if comp.get("purl"):
            purls.add(normalize_purl(str(comp["purl"])))
        name_lc = str(comp.get("name") or "").strip().lower()
        if name_lc:
            versions_by_name.setdefault(name_lc, []).append(comp.get("version"))
    return ComponentIndex(purls=purls, versions_by_name=versions_by_name)


def compute_sbom_fields(
    vuln_fields: dict[str, Any],
    components: list[dict] | ComponentIndex | None,
) -> dict[str, Any]:
    """Calcule les 4 champs virtuels sbom_* pour une vulnérabilité.

    Args:
        vuln_fields: la vuln sérialisée (purl / component_name /
            component_version, en champ direct ou dans extra).
        components: composants du SBOM de l'asset (liste brute ou
            ComponentIndex déjà pré-calculé) ; None = pas de SBOM
            (tous les champs valent alors None — information indisponible,
            à distinguer d'un SBOM présent sans le composant -> False).
    """
    empty: dict[str, Any] = {f: None for f in SBOM_FIELDS}
    if components is None:
        return empty

    # Rétrocompatibilité : une liste brute est indexée à la volée.
    index = (
        components
        if isinstance(components, ComponentIndex)
        else build_component_index(components)
    )

    purl = _vuln_get(vuln_fields, "purl")
    name = _vuln_get(vuln_fields, "component_name")
    version = _vuln_get(vuln_fields, "component_version")

    # Sans component_name, le nom/version se déduisent du purl
    purl_parsable = True
    if purl and (name is None or version is None):
        purl_name, purl_version = parse_purl(str(purl))
        purl_parsable = purl_name is not None
        name = name if name is not None else purl_name
        version = version if version is not None else purl_version

    # Identifiant inexploitable (purl non parsable et aucun nom fourni par
    # ailleurs) = information indisponible : jamais un faux « absent ».
    if purl is None and name is None:
        return empty
    if purl and not purl_parsable and name is None:
        return empty

    present = False
    match_type = "none"

    if purl:
        target = normalize_purl(str(purl))
        if target in index.purls:
            present, match_type = True, "purl"

    name_lc = str(name).strip().lower() if name is not None else None
    versions_for_name = index.versions_by_name.get(name_lc, []) if name_lc is not None else []
    name_present: bool | None = bool(versions_for_name) if name_lc is not None else None

    if not present and name_lc is not None and version is not None:
        if any(v == str(version) for v in versions_for_name if v is not None):
            present, match_type = True, "name_version"

    versions_str = ", ".join(sorted({str(v) for v in versions_for_name if v})) or None

    return {
        "sbom_component_present": present,
        "sbom_name_present": name_present,
        "sbom_component_version": versions_str,
        "sbom_match_type": match_type,
    }


def get_sbom_field_definitions() -> list[FieldDefinition]:
    """Définitions des champs virtuels SBOM pour l'UI de field mapping."""
    return [
        FieldDefinition(
            name="sbom_component_present",
            label="SBOM: Component Present",
            type=FieldType.BOOLEAN,
            description="Le composant (purl ou nom+version) est présent dans "
            "le SBOM de l'asset. Null si pas de SBOM ou pas "
            "d'identifiant de composant.",
            examples=[True, False],
        ),
        FieldDefinition(
            name="sbom_name_present",
            label="SBOM: Name Present (any version)",
            type=FieldType.BOOLEAN,
            description="Le nom du composant existe dans le SBOM, toute "
            "version confondue.",
            examples=[True, False],
        ),
        FieldDefinition(
            name="sbom_component_version",
            label="SBOM: Version(s) in SBOM",
            type=FieldType.STRING,
            description="Version(s) du composant trouvées dans le SBOM "
            "(jointes par des virgules).",
            examples=["4.17.21"],
        ),
        FieldDefinition(
            name="sbom_match_type",
            label="SBOM: Match Type",
            type=FieldType.STRING,
            description="Mode de correspondance : purl, name_version ou none.",
            examples=["purl", "name_version", "none"],
        ),
    ]
