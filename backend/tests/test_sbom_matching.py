"""Tests du matching SBOM (fonctions pures : purl, nom/version, champs virtuels)."""

from app.engine.sbom import (
    SBOM_FIELDS,
    compute_sbom_fields,
    is_sbom_field,
    normalize_purl,
    parse_purl,
)

COMPONENTS = [
    {"purl": "pkg:npm/lodash@4.17.21", "name": "lodash", "version": "4.17.21"},
    {
        "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1",
        "name": "log4j-core",
        "version": "2.14.1",
    },
    {"purl": None, "name": "internal-legacy-lib", "version": "0.9.0"},
]


class TestParsePurl:
    def test_purl_simple(self):
        assert parse_purl("pkg:npm/lodash@4.17.21") == ("lodash", "4.17.21")

    def test_purl_avec_namespace(self):
        name, version = parse_purl(
            "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1"
        )
        assert (name, version) == ("log4j-core", "2.14.1")

    def test_purl_avec_qualifiers_et_subpath(self):
        assert parse_purl("pkg:npm/lodash@4.17.21?arch=x64#lib") == ("lodash", "4.17.21")

    def test_purl_sans_version(self):
        assert parse_purl("pkg:npm/lodash") == ("lodash", None)

    def test_non_purl(self):
        assert parse_purl("cpe:2.3:a:lodash:lodash") == (None, None)


class TestNormalizePurl:
    def test_type_et_nom_insensibles_casse_version_sensible(self):
        assert normalize_purl("pkg:NPM/Lodash@4.17.21-Beta") == "pkg:npm/lodash@4.17.21-Beta"

    def test_qualifiers_ignores(self):
        assert normalize_purl("pkg:npm/lodash@4.17.21?os=linux") == "pkg:npm/lodash@4.17.21"


class TestComputeSbomFields:
    def test_match_purl_exact(self):
        fields = compute_sbom_fields({"purl": "pkg:npm/lodash@4.17.21"}, COMPONENTS)
        assert fields["sbom_component_present"] is True
        assert fields["sbom_match_type"] == "purl"
        assert fields["sbom_name_present"] is True
        assert fields["sbom_component_version"] == "4.17.21"

    def test_match_purl_insensible_casse_du_nom(self):
        fields = compute_sbom_fields({"purl": "pkg:npm/LODASH@4.17.21"}, COMPONENTS)
        assert fields["sbom_component_present"] is True

    def test_repli_nom_version(self):
        vuln = {"component_name": "Internal-Legacy-Lib", "component_version": "0.9.0"}
        fields = compute_sbom_fields(vuln, COMPONENTS)
        assert fields["sbom_component_present"] is True
        assert fields["sbom_match_type"] == "name_version"

    def test_nom_present_version_differente(self):
        # Le composant existe mais dans une autre version : name_present True,
        # component_present False -> branche « corrigé/version différente »
        fields = compute_sbom_fields({"purl": "pkg:npm/lodash@3.0.0"}, COMPONENTS)
        assert fields["sbom_component_present"] is False
        assert fields["sbom_name_present"] is True
        assert fields["sbom_component_version"] == "4.17.21"
        assert fields["sbom_match_type"] == "none"

    def test_composant_absent(self):
        fields = compute_sbom_fields({"purl": "pkg:npm/left-pad@1.3.0"}, COMPONENTS)
        assert fields["sbom_component_present"] is False
        assert fields["sbom_name_present"] is False
        assert fields["sbom_component_version"] is None

    def test_null_sans_sbom(self):
        # components None = l'asset n'a pas de SBOM : tout est null
        fields = compute_sbom_fields({"purl": "pkg:npm/lodash@4.17.21"}, None)
        assert all(fields[f] is None for f in SBOM_FIELDS)

    def test_null_sans_identifiant_composant(self):
        fields = compute_sbom_fields({"cve_id": "CVE-2024-0001"}, COMPONENTS)
        assert all(fields[f] is None for f in SBOM_FIELDS)

    def test_identifiants_dans_extra(self):
        vuln = {"extra": {"purl": "pkg:npm/lodash@4.17.21"}}
        fields = compute_sbom_fields(vuln, COMPONENTS)
        assert fields["sbom_component_present"] is True

    def test_sbom_vide_donne_false(self):
        # L'asset A un SBOM (liste vide != None) : réponse ferme, pas null
        fields = compute_sbom_fields({"purl": "pkg:npm/lodash@4.17.21"}, [])
        assert fields["sbom_component_present"] is False


class TestIsSbomField:
    def test_champs_reconnus(self):
        assert all(is_sbom_field(f) for f in SBOM_FIELDS)

    def test_autres_champs(self):
        assert not is_sbom_field("cvss_score")
        assert not is_sbom_field("sbom_autre_chose")
