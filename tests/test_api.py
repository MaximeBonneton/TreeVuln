#!/usr/bin/env python3
"""
Script de test de l'API TreeVuln.

Permet de :
- Tester l'évaluation de vulnérabilités individuelles
- Tester l'évaluation en batch (JSON et CSV)
- Mesurer les performances
- Valider les résultats attendus
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

# Configuration
DEFAULT_API_URL = "http://localhost:8000/api/v1"
DATA_DIR = Path(__file__).parent / "data"

# Variable globale pour l'URL de l'API
api_base_url = DEFAULT_API_URL


@dataclass
class TestResult:
    """Résultat d'un test."""
    name: str
    passed: bool
    duration_ms: float
    details: str = ""

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour l'export."""
        return {
            "name": self.name,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
        }


def load_vulnerabilities_from_csv(filepath: Path) -> list[dict]:
    """Charge les vulnérabilités depuis un fichier CSV."""
    vulns = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vuln = {
                "cve_id": row["cve_id"],
                "cvss_score": float(row["cvss_score"]),
                "epss_score": float(row["epss_score"]),
                "kev": row["kev"].lower() == "true",
                "asset_id": row["asset_id"],
                "extra": {
                    "exploit_type": row.get("exploit_type", ""),
                    "asset_name": row.get("asset_name", ""),
                    "asset_ip": row.get("asset_ip", ""),
                    "regulation": row.get("regulation", ""),
                    "description": row.get("description", ""),
                }
            }
            vulns.append(vuln)
    return vulns


def test_health_check() -> TestResult:
    """Teste que l'API est accessible."""
    start = time.time()
    try:
        response = requests.get(f"{api_base_url}/tree", timeout=5)
        duration = (time.time() - start) * 1000
        if response.status_code == 200:
            return TestResult("Health Check", True, duration, "API accessible")
        return TestResult("Health Check", False, duration, f"Status: {response.status_code}")
    except Exception as e:
        return TestResult("Health Check", False, 0, str(e))


def test_single_evaluation(vuln: dict) -> TestResult:
    """Teste l'évaluation d'une vulnérabilité."""
    start = time.time()
    try:
        response = requests.post(
            f"{api_base_url}/evaluate/single",
            json={"vulnerability": vuln},
            timeout=10
        )
        duration = (time.time() - start) * 1000

        if response.status_code == 200:
            result = response.json()
            decision = result.get("decision", "N/A")
            path_len = len(result.get("path", []))
            return TestResult(
                f"Single: {vuln['cve_id']}",
                True,
                duration,
                f"Decision: {decision}, Path: {path_len} nodes"
            )
        return TestResult(
            f"Single: {vuln['cve_id']}",
            False,
            duration,
            f"Status: {response.status_code}, Body: {response.text[:100]}"
        )
    except Exception as e:
        return TestResult(f"Single: {vuln['cve_id']}", False, 0, str(e))


def test_batch_evaluation(vulns: list[dict]) -> TestResult:
    """Teste l'évaluation en batch."""
    start = time.time()
    try:
        response = requests.post(
            f"{api_base_url}/evaluate",
            json={"vulnerabilities": vulns},
            timeout=30
        )
        duration = (time.time() - start) * 1000

        if response.status_code == 200:
            results = response.json()
            total = len(results.get("results", []))
            errors = sum(1 for r in results.get("results", []) if r.get("error"))
            return TestResult(
                f"Batch ({len(vulns)} vulns)",
                True,
                duration,
                f"Processed: {total}, Errors: {errors}, Rate: {len(vulns)/(duration/1000):.1f} vulns/s"
            )
        return TestResult(
            f"Batch ({len(vulns)} vulns)",
            False,
            duration,
            f"Status: {response.status_code}"
        )
    except Exception as e:
        return TestResult(f"Batch ({len(vulns)} vulns)", False, 0, str(e))


def test_csv_upload(filepath: Path) -> TestResult:
    """Teste l'upload et l'évaluation d'un fichier CSV."""
    start = time.time()
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{api_base_url}/evaluate/csv",
                files={"file": (filepath.name, f, "text/csv")},
                timeout=60
            )
        duration = (time.time() - start) * 1000

        if response.status_code == 200:
            results = response.json()
            total = len(results.get("results", []))
            return TestResult(
                "CSV Upload",
                True,
                duration,
                f"Processed: {total} vulnerabilities"
            )
        return TestResult(
            "CSV Upload",
            False,
            duration,
            f"Status: {response.status_code}, Body: {response.text[:200]}"
        )
    except Exception as e:
        return TestResult("CSV Upload", False, 0, str(e))


def test_expected_decisions(vulns: list[dict]) -> list[TestResult]:
    """
    Teste que certaines vulnérabilités retournent les décisions attendues.
    Basé sur l'arbre SSVC par défaut.
    """
    results = []

    # Cas de test avec décisions attendues
    test_cases = [
        # CVE critique + KEV = Act
        {
            "vuln": {"cve_id": "TEST-001", "cvss_score": 9.8, "kev": True, "asset_id": "srv-prod-001"},
            "expected": "Act",
            "reason": "Critical CVSS + In KEV"
        },
        # CVE critique + pas KEV = Attend
        {
            "vuln": {"cve_id": "TEST-002", "cvss_score": 9.5, "kev": False, "asset_id": "srv-prod-001"},
            "expected": "Attend",
            "reason": "Critical CVSS + Not KEV + Critical Asset"
        },
        # CVE medium + asset critical = Attend
        {
            "vuln": {"cve_id": "TEST-003", "cvss_score": 5.5, "kev": False, "asset_id": "srv-prod-001"},
            "expected": "Attend",
            "reason": "Medium CVSS + Critical Asset"
        },
        # CVE medium + asset medium = Track*
        {
            "vuln": {"cve_id": "TEST-004", "cvss_score": 5.5, "kev": False, "asset_id": "srv-staging-001"},
            "expected": "Track*",
            "reason": "Medium CVSS + Medium Asset"
        },
        # CVE low = Track
        {
            "vuln": {"cve_id": "TEST-005", "cvss_score": 3.0, "kev": False, "asset_id": "srv-prod-001"},
            "expected": "Track",
            "reason": "Low CVSS"
        },
    ]

    for tc in test_cases:
        start = time.time()
        try:
            response = requests.post(
                f"{api_base_url}/evaluate/single",
                json={"vulnerability": tc["vuln"]},
                timeout=10
            )
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                result = response.json()
                actual = result.get("decision")
                passed = actual == tc["expected"]
                results.append(TestResult(
                    f"Expected: {tc['vuln']['cve_id']}",
                    passed,
                    duration,
                    f"Expected: {tc['expected']}, Got: {actual} ({tc['reason']})"
                ))
            else:
                results.append(TestResult(
                    f"Expected: {tc['vuln']['cve_id']}",
                    False,
                    duration,
                    f"API Error: {response.status_code}"
                ))
        except Exception as e:
            results.append(TestResult(
                f"Expected: {tc['vuln']['cve_id']}",
                False,
                0,
                str(e)
            ))

    return results


def test_performance(vulns: list[dict], iterations: int = 3) -> TestResult:
    """Teste les performances avec plusieurs itérations."""
    times = []
    total_vulns = len(vulns)

    for i in range(iterations):
        start = time.time()
        try:
            response = requests.post(
                f"{api_base_url}/evaluate",
                json={"vulnerabilities": vulns},
                timeout=60
            )
            if response.status_code == 200:
                times.append(time.time() - start)
        except Exception:
            pass

    if not times:
        return TestResult("Performance", False, 0, "All iterations failed")

    avg_time = sum(times) / len(times) * 1000
    min_time = min(times) * 1000
    max_time = max(times) * 1000
    rate = total_vulns / (avg_time / 1000)

    return TestResult(
        f"Performance ({iterations} iterations)",
        True,
        avg_time,
        f"Avg: {avg_time:.1f}ms, Min: {min_time:.1f}ms, Max: {max_time:.1f}ms, Rate: {rate:.1f} vulns/s"
    )


def test_assets_api() -> TestResult:
    """Teste l'API des assets."""
    start = time.time()
    try:
        response = requests.get(f"{api_base_url}/assets", timeout=5)
        duration = (time.time() - start) * 1000

        if response.status_code == 200:
            assets = response.json()
            return TestResult(
                "Assets API",
                True,
                duration,
                f"Found {len(assets)} assets"
            )
        return TestResult("Assets API", False, duration, f"Status: {response.status_code}")
    except Exception as e:
        return TestResult("Assets API", False, 0, str(e))


def test_tree_api() -> TestResult:
    """Teste l'API de l'arbre."""
    start = time.time()
    try:
        response = requests.get(f"{api_base_url}/tree", timeout=5)
        duration = (time.time() - start) * 1000

        if response.status_code == 200:
            tree = response.json()
            nodes = len(tree.get("structure", {}).get("nodes", []))
            edges = len(tree.get("structure", {}).get("edges", []))
            return TestResult(
                "Tree API",
                True,
                duration,
                f"Tree: {tree.get('name', 'N/A')}, Nodes: {nodes}, Edges: {edges}"
            )
        return TestResult("Tree API", False, duration, f"Status: {response.status_code}")
    except Exception as e:
        return TestResult("Tree API", False, 0, str(e))


def print_results(results: list[TestResult]) -> bool:
    """Affiche les résultats des tests."""
    print("\n" + "=" * 80)
    print("RESULTATS DES TESTS")
    print("=" * 80)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for r in results:
        status = "✓" if r.passed else "✗"
        color = "\033[92m" if r.passed else "\033[91m"
        reset = "\033[0m"
        print(f"{color}{status}{reset} {r.name:<40} [{r.duration_ms:>8.1f}ms] {r.details}")

    print("=" * 80)
    color = "\033[92m" if passed == total else "\033[93m"
    reset = "\033[0m"
    print(f"{color}Total: {passed}/{total} tests passed{reset}")
    print("=" * 80)

    return passed == total


def export_results(results: list[TestResult], filepath: Path) -> None:
    """Exporte les résultats dans un fichier CSV ou JSON."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    # Métadonnées du rapport
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_url": api_base_url,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round(passed / total * 100, 1) if total > 0 else 0,
        },
        "results": [r.to_dict() for r in results],
    }

    if filepath.suffix.lower() == ".json":
        # Export JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    else:
        # Export CSV (par défaut)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # En-tête avec métadonnées
            writer.writerow(["# TreeVuln API Test Report"])
            writer.writerow(["# Timestamp", report["timestamp"]])
            writer.writerow(["# API URL", report["api_url"]])
            writer.writerow(["# Total", total, "Passed", passed, "Failed", total - passed])
            writer.writerow([])
            # Résultats
            writer.writerow(["Test Name", "Passed", "Duration (ms)", "Details"])
            for r in results:
                writer.writerow([r.name, "OK" if r.passed else "FAIL", round(r.duration_ms, 2), r.details])
            writer.writerow([])
            writer.writerow(["# Success Rate", f"{report['summary']['success_rate']}%"])

    print(f"\nRésultats exportés vers: {filepath}")


def main():
    global api_base_url

    parser = argparse.ArgumentParser(description="Test de l'API TreeVuln")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="URL de base de l'API")
    parser.add_argument("--csv", type=Path, default=DATA_DIR / "vulnerabilities.csv", help="Fichier CSV")
    parser.add_argument("--quick", action="store_true", help="Tests rapides uniquement")
    parser.add_argument("--perf", action="store_true", help="Tests de performance uniquement")
    parser.add_argument("--iterations", type=int, default=3, help="Nombre d'itérations pour les tests de perf")
    parser.add_argument("--export", type=Path, help="Exporter les résultats (CSV ou JSON selon l'extension)")
    args = parser.parse_args()

    api_base_url = args.url

    results: list[TestResult] = []

    print(f"\nTreeVuln API Tests")
    print(f"API URL: {api_base_url}")
    print(f"CSV File: {args.csv}")

    # Test de connectivité
    print("\n[1/6] Test de connectivité...")
    results.append(test_health_check())

    if not results[-1].passed:
        print("\n✗ API non accessible. Arrêt des tests.")
        print_results(results)
        return 1

    # Tests des endpoints
    print("[2/6] Test des endpoints API...")
    results.append(test_tree_api())
    results.append(test_assets_api())

    # Chargement des vulnérabilités
    vulns = []
    if args.csv.exists():
        vulns = load_vulnerabilities_from_csv(args.csv)
        print(f"\nChargé {len(vulns)} vulnérabilités depuis {args.csv}")

    if args.perf:
        # Tests de performance uniquement
        print("\n[PERF] Tests de performance...")
        if vulns:
            results.append(test_performance(vulns, args.iterations))
            # Test avec multiplication des données
            for multiplier in [10, 100]:
                large_vulns = vulns * multiplier
                results.append(test_performance(large_vulns, args.iterations))
    else:
        # Tests standards
        print("[3/6] Tests d'évaluation individuelle...")
        if vulns:
            # Test quelques vulnérabilités individuellement
            for vuln in vulns[:5]:
                results.append(test_single_evaluation(vuln))

        print("[4/6] Tests des décisions attendues...")
        results.extend(test_expected_decisions(vulns))

        if not args.quick:
            print("[5/6] Test d'évaluation en batch...")
            if vulns:
                results.append(test_batch_evaluation(vulns))

            print("[6/6] Test d'upload CSV...")
            if args.csv.exists():
                results.append(test_csv_upload(args.csv))

    # Affichage des résultats
    success = print_results(results)

    # Export si demandé
    if args.export:
        export_results(results, args.export)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
