"""La route des champs virtuels expose aussi les champs sbom_*."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_cvss_fields_inclut_les_champs_sbom(admin_client):
    resp = await admin_client.get("/api/v1/mapping/cvss-fields")
    assert resp.status_code == 200
    names = {f["name"] for f in resp.json()}
    assert {
        "sbom_component_present",
        "sbom_name_present",
        "sbom_component_version",
        "sbom_match_type",
    } <= names
    # Les champs CVSS existants restent présents
    assert "cvss_av" in names
