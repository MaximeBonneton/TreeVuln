"""Service pour le mapping des champs et le scan de fichiers."""

import csv
import io
import json
import re
from datetime import datetime
from typing import Any

from app.schemas.field_mapping import FieldDefinition, FieldMapping, FieldType, ScanResult

# Nombre max de lignes à scanner pour l'inférence de types
MAX_SCAN_ROWS = 100
MAX_EXAMPLES = 5


def infer_field_type(values: list[Any]) -> FieldType:
    """Infère le type d'un champ à partir de ses valeurs."""
    non_null_values = [v for v in values if v is not None and v != ""]

    if not non_null_values:
        return FieldType.UNKNOWN

    # Vérifie si ce sont des booléens
    bool_values = {"true", "false", "1", "0", "yes", "no", "oui", "non"}
    if all(str(v).lower() in bool_values for v in non_null_values):
        return FieldType.BOOLEAN

    # Vérifie si ce sont des nombres
    try:
        for v in non_null_values:
            float(v)
        return FieldType.NUMBER
    except (ValueError, TypeError):
        pass

    # Vérifie si ce sont des dates (patterns courants)
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}",  # ISO format
        r"^\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY ou MM/DD/YYYY
        r"^\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY
    ]
    if all(any(re.match(p, str(v)) for p in date_patterns) for v in non_null_values):
        return FieldType.DATE

    # Vérifie si ce sont des arrays (format JSON)
    if all(isinstance(v, list) or (isinstance(v, str) and v.startswith("[")) for v in non_null_values):
        return FieldType.ARRAY

    return FieldType.STRING


def get_unique_examples(values: list[Any], max_count: int = MAX_EXAMPLES) -> list[Any]:
    """Retourne des exemples uniques de valeurs."""
    seen = set()
    examples = []
    for v in values:
        if len(examples) >= max_count:
            break
        if v is not None and v != "" and str(v) not in seen:
            seen.add(str(v))
            # Convertit en type approprié si possible
            if isinstance(v, str):
                try:
                    examples.append(float(v) if "." in v else int(v))
                    continue
                except ValueError:
                    pass
                if v.lower() in ("true", "yes", "oui"):
                    examples.append(True)
                    continue
                if v.lower() in ("false", "no", "non"):
                    examples.append(False)
                    continue
            examples.append(v)
    return examples


def scan_csv_content(content: str, filename: str = "upload.csv") -> ScanResult:
    """Scanne un contenu CSV et retourne les champs détectés."""
    warnings: list[str] = []
    fields: list[FieldDefinition] = []

    # Parse le CSV
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    if not headers:
        return ScanResult(
            fields=[],
            rows_scanned=0,
            source_type="csv",
            warnings=["Aucun en-tête détecté dans le fichier CSV"],
        )

    # Collecte les valeurs pour chaque colonne
    column_values: dict[str, list[Any]] = {h: [] for h in headers}
    rows_scanned = 0

    for row in reader:
        if rows_scanned >= MAX_SCAN_ROWS:
            warnings.append(f"Scan limité aux {MAX_SCAN_ROWS} premières lignes")
            break
        for header in headers:
            column_values[header].append(row.get(header))
        rows_scanned += 1

    # Crée les définitions de champs
    for header in headers:
        values = column_values[header]
        field_type = infer_field_type(values)
        examples = get_unique_examples(values)

        # Génère un label lisible à partir du nom technique
        label = header.replace("_", " ").replace("-", " ").title()

        fields.append(
            FieldDefinition(
                name=header,
                label=label,
                type=field_type,
                description=None,
                examples=examples,
                required=all(v is not None and v != "" for v in values),
            )
        )

    return ScanResult(
        fields=fields,
        rows_scanned=rows_scanned,
        source_type="csv",
        warnings=warnings,
    )


def scan_json_content(content: str, filename: str = "upload.json") -> ScanResult:
    """Scanne un contenu JSON (array d'objets) et retourne les champs détectés."""
    warnings: list[str] = []
    fields: list[FieldDefinition] = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return ScanResult(
            fields=[],
            rows_scanned=0,
            source_type="json",
            warnings=[f"Erreur de parsing JSON: {e}"],
        )

    # Vérifie que c'est un array d'objets
    if not isinstance(data, list):
        # Si c'est un objet avec une clé contenant un array, utilise-la
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    data = value
                    warnings.append(f"Utilisation de la clé '{key}' comme source de données")
                    break
            else:
                return ScanResult(
                    fields=[],
                    rows_scanned=0,
                    source_type="json",
                    warnings=["Le fichier JSON doit contenir un array d'objets"],
                )

    if not data or not isinstance(data[0], dict):
        return ScanResult(
            fields=[],
            rows_scanned=0,
            source_type="json",
            warnings=["Le fichier JSON doit contenir un array d'objets non vide"],
        )

    # Collecte toutes les clés présentes
    all_keys: set[str] = set()
    for item in data[:MAX_SCAN_ROWS]:
        if isinstance(item, dict):
            all_keys.update(item.keys())

    # Collecte les valeurs pour chaque clé
    column_values: dict[str, list[Any]] = {k: [] for k in all_keys}
    rows_scanned = 0

    for item in data[:MAX_SCAN_ROWS]:
        if not isinstance(item, dict):
            continue
        for key in all_keys:
            column_values[key].append(item.get(key))
        rows_scanned += 1

    if rows_scanned >= MAX_SCAN_ROWS:
        warnings.append(f"Scan limité aux {MAX_SCAN_ROWS} premières lignes")

    # Crée les définitions de champs
    for key in sorted(all_keys):
        values = column_values[key]
        field_type = infer_field_type(values)
        examples = get_unique_examples(values)

        label = key.replace("_", " ").replace("-", " ").title()

        fields.append(
            FieldDefinition(
                name=key,
                label=label,
                type=field_type,
                description=None,
                examples=examples,
                required=all(v is not None and v != "" for v in values),
            )
        )

    return ScanResult(
        fields=fields,
        rows_scanned=rows_scanned,
        source_type="json",
        warnings=warnings,
    )


def scan_file_content(content: str, filename: str) -> ScanResult:
    """Scanne un fichier (CSV ou JSON) et retourne les champs détectés."""
    lower_filename = filename.lower()

    if lower_filename.endswith(".csv"):
        return scan_csv_content(content, filename)
    elif lower_filename.endswith(".json"):
        return scan_json_content(content, filename)
    else:
        # Tente de deviner le format
        content_stripped = content.strip()
        if content_stripped.startswith(("{", "[")):
            return scan_json_content(content, filename)
        else:
            return scan_csv_content(content, filename)


def get_mapping_from_tree_metadata(metadata: dict[str, Any] | None) -> FieldMapping | None:
    """Extrait le mapping des champs depuis les métadonnées d'un arbre."""
    if not metadata or "field_mapping" not in metadata:
        return None

    mapping_data = metadata["field_mapping"]
    try:
        return FieldMapping.model_validate(mapping_data)
    except Exception:
        return None


def set_mapping_in_tree_metadata(
    metadata: dict[str, Any] | None, mapping: FieldMapping
) -> dict[str, Any]:
    """Met à jour le mapping dans les métadonnées d'un arbre."""
    if metadata is None:
        metadata = {}

    metadata["field_mapping"] = mapping.model_dump()
    return metadata


def remove_mapping_from_tree_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Supprime le mapping des métadonnées d'un arbre."""
    if metadata is None:
        return {}

    metadata.pop("field_mapping", None)
    return metadata
