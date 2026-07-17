"""Intégration bout en bout : upload SBOM puis évaluation batch avec sbom_*."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio

FIXTURES = Path(__file__).parent / "fixtures"

TREE = {
    "nodes": [
        {"id": "in-1", "type": "input", "label": "Component present?",
         "config": {"field": "sbom_component_present"},
         "conditions": [
             {"label": "present", "operator": "eq", "value": True},
             {"label": "absent", "operator": "eq", "value": False},
             {"label": "unknown", "operator": "is_null", "value": None},
         ]},
        {"id": "out-act", "type": "output", "label": "Act",
         "config": {"decision": "Act", "color": "#dc2626"}},
        {"id": "out-track", "type": "output", "label": "Track",
         "config": {"decision": "Track", "color": "#22c55e"}},
        {"id": "out-attend", "type": "output", "label": "Attend",
         "config": {"decision": "Attend", "color": "#f97316"}},
    ],
    "edges": [
        {"id": "e0", "source": "in-1", "target": "out-act", "source_handle": "handle-0"},
        {"id": "e1", "source": "in-1", "target": "out-track", "source_handle": "handle-1"},
        {"id": "e2", "source": "in-1", "target": "out-attend", "source_handle": "handle-2"},
    ],
}


async def test_batch_avec_matching_sbom(admin_client):
    # Arbre par défaut + asset + SBOM
    resp = await admin_client.post("/api/v1/tree",
                                   json={"name": "SBOM eval", "structure": TREE})
    tree_id = resp.json()["id"]
    await admin_client.put(f"/api/v1/tree/{tree_id}/set-default")
    await admin_client.post(
        f"/api/v1/assets?tree_id={tree_id}",
        json={"asset_id": "srv-001", "criticality": "High"},
    )
    content = (FIXTURES / "sbom_cyclonedx.json").read_bytes()
    resp = await admin_client.post(
        f"/api/v1/assets/srv-001/sbom?tree_id={tree_id}",
        files={"file": ("bom.json", content, "application/json")},
    )
    assert resp.status_code == 201, resp.text

    resp = await admin_client.post("/api/v1/evaluate", json={
        "vulnerabilities": [
            # lodash présent dans le SBOM -> Act
            {"cve_id": "CVE-2024-0001", "asset_id": "srv-001",
             "purl": "pkg:npm/lodash@4.17.21"},
            # composant inconnu -> Track
            {"cve_id": "CVE-2024-0002", "asset_id": "srv-001",
             "purl": "pkg:npm/left-pad@1.0.0"},
            # asset sans SBOM -> null -> Attend
            {"cve_id": "CVE-2024-0003", "asset_id": "srv-999",
             "purl": "pkg:npm/lodash@4.17.21"},
        ],
    })
    assert resp.status_code == 200, resp.text
    decisions = [r["decision"] for r in resp.json()["results"]]
    assert decisions == ["Act", "Track", "Attend"]
