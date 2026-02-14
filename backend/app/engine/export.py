"""
Module d'export des résultats d'évaluation en CSV et JSON.
"""

import csv
import io
import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from app.schemas.evaluation import EvaluationResponse, EvaluationResult


def export_csv(results: list[EvaluationResult], include_path: bool = True) -> Generator[str, None, None]:
    """
    Génère un fichier CSV ligne par ligne à partir des résultats d'évaluation.

    Args:
        results: Liste des résultats d'évaluation
        include_path: Inclure le chemin de décision détaillé

    Yields:
        Lignes CSV
    """
    if not results:
        yield ""
        return

    # Détermine le nombre max d'étapes dans les chemins
    max_steps = max((len(r.path) for r in results), default=0) if include_path else 0

    # Construit les headers
    headers = ["vuln_id", "decision", "decision_color", "error"]
    if include_path:
        headers.append("path_summary")
        for i in range(max_steps):
            headers.extend([
                f"step_{i + 1}_node",
                f"step_{i + 1}_type",
                f"step_{i + 1}_field",
                f"step_{i + 1}_value",
                f"step_{i + 1}_condition",
            ])

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(headers)
    yield output.getvalue()
    output.seek(0)
    output.truncate()

    # Data rows
    for result in results:
        row: list[Any] = [
            result.vuln_id or "",
            result.decision,
            result.decision_color or "",
            result.error or "",
        ]

        if include_path:
            # Path summary
            path_summary = " -> ".join(
                f"{s.node_label}[{s.condition_matched or 'END'}]"
                for s in result.path
            )
            row.append(path_summary)

            # Detailed steps
            for i in range(max_steps):
                if i < len(result.path):
                    step = result.path[i]
                    row.extend([
                        step.node_label,
                        step.node_type,
                        step.field_evaluated or "",
                        json.dumps(step.value_found) if step.value_found is not None else "",
                        step.condition_matched or "",
                    ])
                else:
                    row.extend(["", "", "", "", ""])

        writer.writerow(row)
        yield output.getvalue()
        output.seek(0)
        output.truncate()


def export_json(
    response: EvaluationResponse,
    tree_name: str | None = None,
) -> str:
    """
    Génère un export JSON complet avec métadonnées.

    Args:
        response: Réponse d'évaluation complète
        tree_name: Nom de l'arbre utilisé

    Returns:
        Chaîne JSON formatée
    """
    export_data = {
        "metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "tree_name": tree_name,
            "total": response.total,
            "success_count": response.success_count,
            "error_count": response.error_count,
            "decision_summary": response.decision_summary,
        },
        "results": [r.model_dump() for r in response.results],
    }
    return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
