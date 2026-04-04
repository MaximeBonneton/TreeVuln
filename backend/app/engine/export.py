"""
Export module for evaluation results in CSV and JSON.
"""

import csv
import io
import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from app.schemas.evaluation import EvaluationResponse, EvaluationResult

# Characters that trigger formula interpretation in spreadsheet applications
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value: Any) -> Any:
    """Prevent CSV formula injection by prefixing dangerous values with a single quote."""
    if isinstance(value, str) and value and value[0] in _FORMULA_PREFIXES:
        return f"'{value}"
    return value


def export_csv(results: list[EvaluationResult], include_path: bool = True) -> Generator[str, None, None]:
    """
    Generate a CSV file line by line from evaluation results.

    Args:
        results: List of evaluation results
        include_path: Include the detailed decision path

    Yields:
        CSV lines
    """
    if not results:
        yield ""
        return

    # Determine the max number of steps in paths
    max_steps = max((len(r.path) for r in results), default=0) if include_path else 0

    # Build the headers
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
            _sanitize_cell(result.vuln_id or ""),
            _sanitize_cell(result.decision),
            _sanitize_cell(result.decision_color or ""),
            _sanitize_cell(result.error or ""),
        ]

        if include_path:
            # Path summary
            path_summary = " -> ".join(
                f"{s.node_label}[{s.condition_matched or 'END'}]"
                for s in result.path
            )
            row.append(_sanitize_cell(path_summary))

            # Detailed steps
            for i in range(max_steps):
                if i < len(result.path):
                    step = result.path[i]
                    row.extend([
                        _sanitize_cell(step.node_label),
                        _sanitize_cell(step.node_type),
                        _sanitize_cell(step.field_evaluated or ""),
                        _sanitize_cell(json.dumps(step.value_found) if step.value_found is not None else ""),
                        _sanitize_cell(step.condition_matched or ""),
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
    Generate a complete JSON export with metadata.

    Args:
        response: Complete evaluation response
        tree_name: Name of the tree used

    Returns:
        Formatted JSON string
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
