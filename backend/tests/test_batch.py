"""
Tests du traitement batch.
"""

import pytest

from app.engine.batch import BatchProcessor
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class TestBatchProcessor:
    """Tests pour BatchProcessor."""

    @pytest.mark.asyncio
    async def test_process_batch(self, simple_tree_structure: TreeStructure):
        """Test: Traitement d'un batch de vulnérabilités."""
        processor = BatchProcessor(simple_tree_structure, chunk_size=10)

        vulns = [
            VulnerabilityInput(id="v1", cvss_score=9.5),  # -> Act
            VulnerabilityInput(id="v2", cvss_score=7.5),  # -> Attend
            VulnerabilityInput(id="v3", cvss_score=4.0),  # -> Track
            VulnerabilityInput(id="v4", cvss_score=9.0),  # -> Act
            VulnerabilityInput(id="v5", cvss_score=6.9),  # -> Track
        ]

        response = await processor.process_batch(vulns)

        assert response.total == 5
        assert response.success_count == 5
        assert response.error_count == 0
        assert response.decision_summary["Act"] == 2
        assert response.decision_summary["Attend"] == 1
        assert response.decision_summary["Track"] == 2

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, simple_tree_structure: TreeStructure):
        """Test: Batch avec des erreurs (champs manquants)."""
        processor = BatchProcessor(simple_tree_structure)

        vulns = [
            VulnerabilityInput(id="v1", cvss_score=9.5),  # OK
            VulnerabilityInput(id="v2"),  # Pas de cvss_score -> erreur
            VulnerabilityInput(id="v3", cvss_score=4.0),  # OK
        ]

        response = await processor.process_batch(vulns)

        assert response.total == 3
        assert response.success_count == 2
        assert response.error_count == 1

    @pytest.mark.asyncio
    async def test_process_batch_no_path(self, simple_tree_structure: TreeStructure):
        """Test: Batch sans chemin de décision (performance)."""
        processor = BatchProcessor(simple_tree_structure)

        vulns = [
            VulnerabilityInput(id=f"v{i}", cvss_score=float(i))
            for i in range(1, 11)  # 10 vulnérabilités
        ]

        response = await processor.process_batch(vulns, include_path=False)

        assert response.total == 10
        # Vérifie qu'aucun résultat n'a de chemin
        for result in response.results:
            assert len(result.path) == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_lookups(self, tree_with_lookup: TreeStructure):
        """Test: Batch avec lookups d'assets."""
        processor = BatchProcessor(tree_with_lookup)

        vulns = [
            VulnerabilityInput(id="v1", cvss_score=8.0, asset_id="srv-critical"),
            VulnerabilityInput(id="v2", cvss_score=8.0, asset_id="srv-high"),
            VulnerabilityInput(id="v3", cvss_score=8.0, asset_id="srv-medium"),
        ]

        lookups = {
            "assets": {
                "srv-critical": {"criticality": "Critical"},
                "srv-high": {"criticality": "High"},
                "srv-medium": {"criticality": "Medium"},
            }
        }

        response = await processor.process_batch(vulns, lookups=lookups)

        assert response.total == 3
        assert response.success_count == 3

        # Vérifie les décisions
        decisions = {r.vuln_id: r.decision for r in response.results}
        assert decisions["v1"] == "Act"
        assert decisions["v2"] == "Attend"
        assert decisions["v3"] == "Track"


class TestBatchProcessorDataLoading:
    """Tests pour le chargement de données."""

    def test_from_json_list(self):
        """Test: Conversion de JSON en DataFrame."""
        data = [
            {"id": "v1", "cvss_score": 9.0, "cve_id": "CVE-2024-0001"},
            {"id": "v2", "cvss_score": 7.5, "cve_id": "CVE-2024-0002"},
        ]

        df = BatchProcessor.from_json_list(data)

        assert len(df) == 2
        assert "cvss_score" in df.columns
        assert df["cvss_score"][0] == 9.0

    def test_from_csv(self):
        """Test: Chargement d'un CSV."""
        csv_content = """id,cvss_score,cve_id
v1,9.0,CVE-2024-0001
v2,7.5,CVE-2024-0002
v3,4.0,CVE-2024-0003"""

        df = BatchProcessor.from_csv(csv_content)

        assert len(df) == 3
        assert df["cvss_score"][0] == 9.0
        assert df["cve_id"][1] == "CVE-2024-0002"
