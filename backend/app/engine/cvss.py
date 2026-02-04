"""
CVSS Vector Parser - Support for CVSS 3.1 and 4.0 metrics.

Parses CVSS vectors and extracts individual metrics as readable values
for use in decision tree Input nodes.
"""

from app.schemas.field_mapping import FieldDefinition, FieldType

# CVSS 3.1 Metrics mapping: abbreviation -> (field_name, label, value_mapping)
CVSS_31_METRICS: dict[str, tuple[str, str, dict[str, str]]] = {
    "AV": (
        "cvss_av",
        "Attack Vector",
        {"N": "Network", "A": "Adjacent", "L": "Local", "P": "Physical"},
    ),
    "AC": (
        "cvss_ac",
        "Attack Complexity",
        {"L": "Low", "H": "High"},
    ),
    "PR": (
        "cvss_pr",
        "Privileges Required",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "UI": (
        "cvss_ui",
        "User Interaction",
        {"N": "None", "R": "Required"},
    ),
    "S": (
        "cvss_s",
        "Scope",
        {"U": "Unchanged", "C": "Changed"},
    ),
    "C": (
        "cvss_c",
        "Confidentiality Impact",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "I": (
        "cvss_i",
        "Integrity Impact",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "A": (
        "cvss_a",
        "Availability Impact",
        {"N": "None", "L": "Low", "H": "High"},
    ),
}

# CVSS 4.0 additional metrics (CVSS 4.0 has different structure)
CVSS_40_METRICS: dict[str, tuple[str, str, dict[str, str]]] = {
    # Base metrics (similar to 3.1 but with some differences)
    "AV": (
        "cvss_av",
        "Attack Vector",
        {"N": "Network", "A": "Adjacent", "L": "Local", "P": "Physical"},
    ),
    "AC": (
        "cvss_ac",
        "Attack Complexity",
        {"L": "Low", "H": "High"},
    ),
    "AT": (
        "cvss_at",
        "Attack Requirements",
        {"N": "None", "P": "Present"},
    ),
    "PR": (
        "cvss_pr",
        "Privileges Required",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "UI": (
        "cvss_ui",
        "User Interaction",
        {"N": "None", "P": "Passive", "A": "Active"},
    ),
    # Vulnerable System Impact
    "VC": (
        "cvss_vc",
        "Vulnerable System Confidentiality",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "VI": (
        "cvss_vi",
        "Vulnerable System Integrity",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "VA": (
        "cvss_va",
        "Vulnerable System Availability",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    # Subsequent System Impact
    "SC": (
        "cvss_sc",
        "Subsequent System Confidentiality",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "SI": (
        "cvss_si",
        "Subsequent System Integrity",
        {"N": "None", "L": "Low", "H": "High"},
    ),
    "SA": (
        "cvss_sa",
        "Subsequent System Availability",
        {"N": "None", "L": "Low", "H": "High"},
    ),
}


def detect_cvss_version(vector: str) -> str | None:
    """
    Detect CVSS version from vector string.

    Args:
        vector: CVSS vector string (e.g., "CVSS:3.1/AV:N/AC:L/...")

    Returns:
        "3.1", "4.0", or None if not detected
    """
    if not vector or not isinstance(vector, str):
        return None

    vector_upper = vector.upper().strip()

    if vector_upper.startswith("CVSS:4.0/"):
        return "4.0"
    if vector_upper.startswith("CVSS:3.1/"):
        return "3.1"
    if vector_upper.startswith("CVSS:3.0/"):
        return "3.1"  # Treat 3.0 as 3.1 for metric parsing

    return None


def parse_cvss_vector(vector: str) -> dict[str, str]:
    """
    Parse a CVSS vector and return individual metrics as readable values.

    Args:
        vector: CVSS vector string (e.g., "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")

    Returns:
        Dictionary mapping field names to readable values.
        Example: {"cvss_av": "Network", "cvss_ac": "Low", ...}

    Note:
        Returns empty dict if vector is invalid or empty.
    """
    result: dict[str, str] = {}

    version = detect_cvss_version(vector)
    if not version:
        return result

    # Select appropriate metrics mapping based on version
    metrics_map = CVSS_40_METRICS if version == "4.0" else CVSS_31_METRICS

    # Remove prefix and split into metric pairs
    vector_upper = vector.upper().strip()
    if version == "4.0":
        parts = vector_upper.replace("CVSS:4.0/", "").split("/")
    else:
        # Handle both CVSS:3.0 and CVSS:3.1
        parts = (
            vector_upper.replace("CVSS:3.1/", "")
            .replace("CVSS:3.0/", "")
            .split("/")
        )

    # Parse each metric
    for part in parts:
        if ":" not in part:
            continue

        abbrev, value = part.split(":", 1)
        abbrev = abbrev.strip()
        value = value.strip()

        if abbrev in metrics_map:
            field_name, _, value_mapping = metrics_map[abbrev]
            readable_value = value_mapping.get(value, value)
            result[field_name] = readable_value

    return result


def get_cvss_field_definitions() -> list[FieldDefinition]:
    """
    Get field definitions for all CVSS metrics.

    Returns:
        List of FieldDefinition objects for use in field mapping UI.
    """
    definitions: list[FieldDefinition] = []
    seen_fields: set[str] = set()

    # CVSS 3.1 fields
    for abbrev, (field_name, label, value_mapping) in CVSS_31_METRICS.items():
        if field_name not in seen_fields:
            seen_fields.add(field_name)
            definitions.append(
                FieldDefinition(
                    name=field_name,
                    label=f"CVSS {label}",
                    type=FieldType.STRING,
                    description=f"CVSS {label} metric. Values: {', '.join(value_mapping.values())}",
                    examples=list(value_mapping.values())[:3],
                    required=False,
                )
            )

    # CVSS 4.0 additional fields (not in 3.1)
    for abbrev, (field_name, label, value_mapping) in CVSS_40_METRICS.items():
        if field_name not in seen_fields:
            seen_fields.add(field_name)
            definitions.append(
                FieldDefinition(
                    name=field_name,
                    label=f"CVSS 4.0 {label}",
                    type=FieldType.STRING,
                    description=f"CVSS 4.0 {label} metric. Values: {', '.join(value_mapping.values())}",
                    examples=list(value_mapping.values())[:3],
                    required=False,
                )
            )

    return definitions


def is_cvss_field(field_name: str) -> bool:
    """
    Check if a field name is a CVSS virtual field.

    Args:
        field_name: Field name to check

    Returns:
        True if it's a CVSS metric field (cvss_av, cvss_ac, etc.)
    """
    # Exclude cvss_score and cvss_vector which are direct fields
    if field_name in ("cvss_score", "cvss_vector"):
        return False

    if not field_name.startswith("cvss_"):
        return False

    # Check if it's a known CVSS field
    all_fields = set()
    for _, (field_name_def, _, _) in CVSS_31_METRICS.items():
        all_fields.add(field_name_def)
    for _, (field_name_def, _, _) in CVSS_40_METRICS.items():
        all_fields.add(field_name_def)

    return field_name in all_fields
