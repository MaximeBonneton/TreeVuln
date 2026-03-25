"""
Traitement batch avec Polars pour les gros volumes.
"""

from collections import Counter
from typing import Any

import polars as pl

from app.engine.inference import InferenceEngine
from app.schemas.evaluation import EvaluationResponse, EvaluationResult
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class BatchProcessor:
    """
    Optimized batch processor for evaluating large volumes of vulnerabilities.
    """

    def __init__(
        self,
        tree_structure: TreeStructure,
        chunk_size: int = 5000,
    ):
        self.engine = InferenceEngine(tree_structure)
        self.chunk_size = chunk_size

    async def process_batch(
        self,
        vulnerabilities: list[VulnerabilityInput],
        lookups: dict[str, dict[str, dict[str, Any]]] | None = None,
        include_path: bool = True,
    ) -> EvaluationResponse:
        """
        Process a batch of vulnerabilities.

        Args:
            vulnerabilities: List of vulnerabilities to evaluate
            lookups: Pre-loaded lookup cache
            include_path: Include the decision path

        Returns:
            EvaluationResponse with all results
        """
        results: list[EvaluationResult] = []
        error_count = 0

        # Process in chunks to avoid memory issues
        for i in range(0, len(vulnerabilities), self.chunk_size):
            chunk = vulnerabilities[i : i + self.chunk_size]
            chunk_results = self._process_chunk(chunk, lookups, include_path)
            results.extend(chunk_results)

        # Count errors and decisions
        decision_counter: Counter[str] = Counter()
        for result in results:
            if result.error:
                error_count += 1
            else:
                decision_counter[result.decision] += 1

        return EvaluationResponse(
            total=len(results),
            success_count=len(results) - error_count,
            error_count=error_count,
            results=results,
            decision_summary=dict(decision_counter),
        )

    def _process_chunk(
        self,
        chunk: list[VulnerabilityInput],
        lookups: dict[str, dict[str, dict[str, Any]]] | None,
        include_path: bool,
    ) -> list[EvaluationResult]:
        """Process a chunk of vulnerabilities."""
        return [
            self.engine.evaluate(vuln, lookups, include_path)
            for vuln in chunk
        ]

    async def process_dataframe(
        self,
        df: pl.DataFrame,
        lookups: dict[str, dict[str, dict[str, Any]]] | None = None,
        include_path: bool = False,
    ) -> pl.DataFrame:
        """
        Process a Polars DataFrame and return enriched results.

        Optimized for very large volumes where the detailed path is not needed.

        Args:
            df: DataFrame with vulnerabilities
            lookups: Cache de lookup
            include_path: Include the path (disabled by default for performance)

        Returns:
            DataFrame enrichi avec les colonnes decision et decision_color
        """
        decisions = []
        colors = []
        errors = []

        for row in df.iter_rows(named=True):
            vuln = self._row_to_vulnerability(row)
            result = self.engine.evaluate(vuln, lookups, include_path=False)
            decisions.append(result.decision)
            colors.append(result.decision_color)
            errors.append(result.error)

        return df.with_columns([
            pl.Series("_decision", decisions),
            pl.Series("_decision_color", colors),
            pl.Series("_decision_error", errors),
        ])

    def _row_to_vulnerability(self, row: dict[str, Any]) -> VulnerabilityInput:
        """Convert a DataFrame row to VulnerabilityInput."""
        # Known standard fields
        standard_fields = {
            "id", "cve_id", "cvss_score", "cvss_vector",
            "epss_score", "epss_percentile", "kev",
            "asset_id", "hostname", "ip_address",
        }

        standard_data = {k: v for k, v in row.items() if k in standard_fields}
        extra_data = {k: v for k, v in row.items() if k not in standard_fields}

        return VulnerabilityInput(**standard_data, extra=extra_data)

    @classmethod
    def from_csv(cls, csv_content: str | bytes) -> pl.DataFrame:
        """Load a CSV into a Polars DataFrame."""
        if isinstance(csv_content, str):
            csv_content = csv_content.encode("utf-8")
        return pl.read_csv(csv_content)

    @classmethod
    def from_json_list(cls, json_data: list[dict[str, Any]]) -> pl.DataFrame:
        """Convert a list of dicts to a Polars DataFrame."""
        return pl.DataFrame(json_data)
