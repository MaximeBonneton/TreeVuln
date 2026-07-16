"""
Traitement batch avec Polars pour les gros volumes.
"""

from collections import Counter
from typing import Any

import polars as pl
from pydantic import ValidationError

from app.engine.inference import InferenceEngine
from app.schemas.evaluation import EvaluationResponse, EvaluationResult
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput

# Champs standards reconnus lors de la conversion ligne brute -> VulnerabilityInput
_STANDARD_FIELDS = {
    "id", "cve_id", "cvss_score", "cvss_vector",
    "epss_score", "epss_percentile", "kev",
    "asset_id", "hostname", "ip_address",
}


def _row_to_vulnerability(row: dict[str, Any]) -> VulnerabilityInput:
    """
    Convertit une ligne brute (dict issu du JSON ou d'un CSV) en VulnerabilityInput.

    Peut lever ValidationError/ValueError/TypeError si les données sont
    invalides (ex: cvss_score hors de [0, 10] ou non convertible en nombre).
    """
    standard_data = {k: v for k, v in row.items() if k in _STANDARD_FIELDS}
    extra_data = {k: v for k, v in row.items() if k not in _STANDARD_FIELDS}
    return VulnerabilityInput(**standard_data, extra=extra_data)


def _extract_row_vuln_id(row: dict[str, Any]) -> str | None:
    """Extrait un identifiant lisible d'une ligne brute pour un résultat d'erreur (B-12)."""
    vuln_id = row.get("id") or row.get("cve_id")
    return str(vuln_id) if vuln_id is not None else None


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
        vulnerabilities: list[VulnerabilityInput | dict[str, Any]],
        lookups: dict[str, dict[str, dict[str, Any]]] | None = None,
        include_path: bool = True,
    ) -> EvaluationResponse:
        """
        Process a batch of vulnerabilities.

        Accepte soit des VulnerabilityInput déjà validés, soit des lignes
        brutes (dict) qui seront converties/validées ligne par ligne (B-12).

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
            chunk_results = self._process_chunk_sync(chunk, lookups, include_path)
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

    def _process_chunk_sync(
        self,
        chunk: list[VulnerabilityInput | dict[str, Any]],
        lookups: dict[str, dict[str, dict[str, Any]]] | None,
        include_path: bool,
    ) -> list[EvaluationResult]:
        """
        Traite un chunk de vulnérabilités de façon synchrone (CPU-bound).

        Exécutée hors de l'event loop via asyncio.to_thread (B-13).
        Isole les erreurs de conversion/validation ligne par ligne (B-12) :
        une ligne brute invalide produit un résultat "Error" au lieu de
        faire échouer tout le chunk.
        """
        results: list[EvaluationResult] = []
        for item in chunk:
            if isinstance(item, VulnerabilityInput):
                vuln = item
            else:
                try:
                    vuln = _row_to_vulnerability(item)
                except (ValidationError, ValueError, TypeError) as exc:
                    results.append(
                        EvaluationResult(
                            vuln_id=_extract_row_vuln_id(item),
                            decision="Error",
                            error=f"Invalid row: {exc}",
                        )
                    )
                    continue
            results.append(self.engine.evaluate(vuln, lookups, include_path))
        return results

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
        return _row_to_vulnerability(row)

    @classmethod
    def from_csv(cls, csv_content: str | bytes) -> pl.DataFrame:
        """
        Load a CSV into a Polars DataFrame.

        Raises:
            ValueError: si le contenu n'est pas un CSV exploitable (B-12) —
            à charge de l'appelant de convertir en HTTPException 400.
        """
        if isinstance(csv_content, str):
            csv_content = csv_content.encode("utf-8")
        try:
            return pl.read_csv(csv_content)
        except Exception as exc:  # polars.exceptions.* (NoDataError, ComputeError, ...)
            raise ValueError(f"Malformed CSV file: {exc}") from exc

    @classmethod
    def from_json_list(cls, json_data: list[dict[str, Any]]) -> pl.DataFrame:
        """Convert a list of dicts to a Polars DataFrame."""
        return pl.DataFrame(json_data)
