"""Tests du parseur SBOM (CycloneDX/SPDX JSON, fonctions pures)."""
import json
from pathlib import Path

import pytest

from app.engine.sbom import ParsedSbom, parse_sbom_file

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestCycloneDx:
    def test_parse_complet(self):
        parsed = parse_sbom_file(_load("sbom_cyclonedx.json"))
        assert parsed.format == "cyclonedx"
        assert parsed.spec_version == "1.5"
        # 4 entrées dans le fichier, 1 sans nom -> ignorée avec warning
        assert len(parsed.components) == 3
        assert len(parsed.warnings) == 1

    def test_composant_avec_purl(self):
        parsed = parse_sbom_file(_load("sbom_cyclonedx.json"))
        lodash = next(c for c in parsed.components if c["name"] == "lodash")
        assert lodash == {
            "purl": "pkg:npm/lodash@4.17.21",
            "name": "lodash",
            "version": "4.17.21",
            "component_type": "library",
        }

    def test_composant_sans_purl_accepte(self):
        parsed = parse_sbom_file(_load("sbom_cyclonedx.json"))
        legacy = next(c for c in parsed.components if c["name"] == "internal-legacy-lib")
        assert legacy["purl"] is None
        assert legacy["version"] == "0.9.0"


class TestSpdx:
    def test_parse_complet(self):
        parsed = parse_sbom_file(_load("sbom_spdx.json"))
        assert parsed.format == "spdx"
        assert parsed.spec_version == "SPDX-2.3"
        assert len(parsed.components) == 2
        assert parsed.warnings == []

    def test_purl_extrait_des_external_refs(self):
        parsed = parse_sbom_file(_load("sbom_spdx.json"))
        openssl = next(c for c in parsed.components if c["name"] == "openssl")
        assert openssl["purl"] == "pkg:generic/openssl@3.0.13"
        assert openssl["version"] == "3.0.13"

    def test_package_sans_purl(self):
        parsed = parse_sbom_file(_load("sbom_spdx.json"))
        zlib = next(c for c in parsed.components if c["name"] == "zlib")
        assert zlib["purl"] is None


class TestErreurs:
    def test_json_invalide(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_sbom_file(b"pas du json {")

    def test_format_inconnu(self):
        with pytest.raises(ValueError, match="Unsupported SBOM format"):
            parse_sbom_file(json.dumps({"hello": "world"}).encode())

    def test_json_non_objet(self):
        with pytest.raises(ValueError, match="expected a JSON object"):
            parse_sbom_file(b"[1, 2, 3]")

    def test_fichier_sans_composant(self):
        # Le parseur retourne une liste vide ; le refus (400) est fait par la route
        parsed = parse_sbom_file(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5"}).encode()
        )
        assert isinstance(parsed, ParsedSbom)
        assert parsed.components == []
