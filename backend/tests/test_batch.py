"""
Tests for batch processing.
"""

import asyncio
from typing import Any

import pytest

from app.engine.batch import BatchProcessor
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class TestBatchProcessor:
    """Tests for BatchProcessor."""

    @pytest.mark.asyncio
    async def test_process_batch(self, simple_tree_structure: TreeStructure):
        """Test: Processing a batch of vulnerabilities."""
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
        """Test: Batch with errors (missing fields)."""
        processor = BatchProcessor(simple_tree_structure)

        vulns = [
            VulnerabilityInput(id="v1", cvss_score=9.5),  # OK
            VulnerabilityInput(id="v2"),  # No cvss_score -> error
            VulnerabilityInput(id="v3", cvss_score=4.0),  # OK
        ]

        response = await processor.process_batch(vulns)

        assert response.total == 3
        assert response.success_count == 2
        assert response.error_count == 1

    @pytest.mark.asyncio
    async def test_process_batch_no_path(self, simple_tree_structure: TreeStructure):
        """Test: Batch without decision path (performance)."""
        processor = BatchProcessor(simple_tree_structure)

        vulns = [
            VulnerabilityInput(id=f"v{i}", cvss_score=float(i))
            for i in range(1, 11)  # 10 vulnerabilities
        ]

        response = await processor.process_batch(vulns, include_path=False)

        assert response.total == 10
        # Verify that no result has a path
        for result in response.results:
            assert len(result.path) == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_lookups(self, tree_with_lookup: TreeStructure):
        """Test: Batch with asset lookups."""
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

        # Verify the decisions
        decisions = {r.vuln_id: r.decision for r in response.results}
        assert decisions["v1"] == "Act"
        assert decisions["v2"] == "Attend"
        assert decisions["v3"] == "Track"

    @pytest.mark.asyncio
    async def test_process_batch_isolates_invalid_raw_rows(
        self, simple_tree_structure: TreeStructure
    ):
        """B-12: une ligne brute invalide (dict) ne fait pas échouer tout le batch."""
        processor = BatchProcessor(simple_tree_structure, chunk_size=10)

        rows: list[dict[str, Any]] = [
            {"id": "v1", "cvss_score": 9.5},  # OK -> Act
            {"id": "v2", "cvss_score": 11},  # hors [0, 10] -> Error
            {"id": "v3", "cvss_score": "N/A"},  # non convertible -> Error
        ]

        response = await processor.process_batch(rows)

        assert response.total == 3
        assert response.success_count == 1
        assert response.error_count == 2

        decisions = [r.decision for r in response.results]
        assert decisions == ["Act", "Error", "Error"]

        assert response.results[0].vuln_id == "v1"
        assert response.results[1].vuln_id == "v2"
        assert response.results[1].error is not None
        assert response.results[2].vuln_id == "v3"
        assert response.results[2].error is not None

    @pytest.mark.asyncio
    async def test_process_batch_uses_to_thread(
        self, simple_tree_structure: TreeStructure, monkeypatch
    ):
        """B-13: le traitement CPU-bound doit passer par asyncio.to_thread (hors event loop)."""
        import app.engine.batch as batch_module

        processor = BatchProcessor(simple_tree_structure, chunk_size=2)
        vulns = [VulnerabilityInput(id=f"v{i}", cvss_score=5.0) for i in range(5)]

        calls: list[Any] = []
        real_to_thread = asyncio.to_thread

        async def spy_to_thread(func, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(batch_module.asyncio, "to_thread", spy_to_thread)

        response = await processor.process_batch(vulns)

        assert response.total == 5
        # 5 items / chunk_size=2 -> 3 chunks, donc 3 appels à to_thread
        assert len(calls) == 3


class TestBatchProcessorDataLoading:
    """Tests for data loading."""

    def test_from_json_list(self):
        """Test: Convert JSON to DataFrame."""
        data = [
            {"id": "v1", "cvss_score": 9.0, "cve_id": "CVE-2024-0001"},
            {"id": "v2", "cvss_score": 7.5, "cve_id": "CVE-2024-0002"},
        ]

        df = BatchProcessor.from_json_list(data)

        assert len(df) == 2
        assert "cvss_score" in df.columns
        assert df["cvss_score"][0] == 9.0

    def test_from_csv(self):
        """Test: Loading a CSV file."""
        csv_content = """id,cvss_score,cve_id
v1,9.0,CVE-2024-0001
v2,7.5,CVE-2024-0002
v3,4.0,CVE-2024-0003"""

        df = BatchProcessor.from_csv(csv_content)

        assert len(df) == 3
        assert df["cvss_score"][0] == 9.0
        assert df["cve_id"][1] == "CVE-2024-0002"

    def test_from_csv_malformed_raises_value_error(self):
        """B-12: un CSV totalement illisible lève ValueError (et non une exception Polars brute)."""
        with pytest.raises(ValueError):
            BatchProcessor.from_csv(b"")
