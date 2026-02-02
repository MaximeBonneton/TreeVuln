#!/usr/bin/env python3
"""
Générateur de données de test pour TreeVuln.

Génère des vulnérabilités et assets fictifs en grande quantité
pour tester les performances du système.
"""

import argparse
import csv
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Données de référence pour la génération
VENDORS = [
    "Microsoft", "Cisco", "Palo Alto", "Fortinet", "VMware",
    "Adobe", "Oracle", "SAP", "IBM", "Red Hat",
    "Apache", "Nginx", "Jenkins", "GitLab", "Docker"
]

PRODUCTS = [
    "Windows Server", "Windows 11", "Exchange", "SharePoint",
    "ASA", "Firepower", "PAN-OS", "FortiOS", "FortiManager",
    "vCenter", "ESXi", "Commerce", "WebLogic", "ERP",
    "RHEL", "HTTP Server", "Tomcat", "Jenkins", "Runner"
]

EXPLOIT_TYPES = [
    "RCE", "SQLi", "XSS", "Auth Bypass", "Privilege Escalation",
    "DoS", "Info Disclosure", "Path Traversal", "XXE",
    "SSRF", "Command Injection", "Deserialization", "Buffer Overflow"
]

CRITICALITIES = ["Critical", "High", "Medium", "Low"]
ENVIRONMENTS = ["production", "staging", "development", "network", "corporate"]
CATEGORIES = ["Server", "Network", "Workstation", "Mobile", "Cloud"]
REGULATIONS = ["PCI-DSS", "RGPD", "SOC2", "ISO27001", "HIPAA", "N/A"]

BUSINESS_UNITS = [
    "IT Infrastructure", "Engineering", "E-Commerce", "Sales",
    "Finance", "Human Resources", "Operations", "Security"
]


def generate_cve_id(year: int = 2024) -> str:
    """Génère un ID CVE aléatoire."""
    return f"CVE-{year}-{random.randint(10000, 99999)}"


def generate_asset_id(category: str, index: int) -> str:
    """Génère un ID d'asset."""
    prefixes = {
        "Server": "srv",
        "Network": "net",
        "Workstation": "ws",
        "Mobile": "mob",
        "Cloud": "cloud"
    }
    prefix = prefixes.get(category, "asset")
    return f"{prefix}-{index:04d}"


def generate_ip() -> str:
    """Génère une adresse IP aléatoire."""
    return f"10.{random.randint(0, 255)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def generate_mac() -> str:
    """Génère une adresse MAC aléatoire."""
    return ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))


def generate_vulnerability(asset_ids: list[str]) -> dict:
    """Génère une vulnérabilité aléatoire."""
    cvss = round(random.uniform(1.0, 10.0), 1)

    # Probabilité de KEV basée sur la sévérité
    kev_prob = {
        "critical": 0.4,
        "high": 0.2,
        "medium": 0.05,
        "low": 0.01
    }
    severity = "critical" if cvss >= 9 else "high" if cvss >= 7 else "medium" if cvss >= 4 else "low"
    kev = random.random() < kev_prob[severity]

    # EPSS corrélé avec CVSS (avec du bruit)
    epss_base = cvss / 10
    epss = min(0.99, max(0.001, epss_base * random.uniform(0.5, 1.5)))

    return {
        "cve_id": generate_cve_id(random.choice([2023, 2024, 2025])),
        "cvss_score": cvss,
        "epss_score": round(epss, 3),
        "kev": kev,
        "exploit_type": random.choice(EXPLOIT_TYPES),
        "asset_id": random.choice(asset_ids),
        "vendor": random.choice(VENDORS),
        "product": random.choice(PRODUCTS),
        "description": f"Simulated vulnerability in {random.choice(PRODUCTS)}"
    }


def generate_asset(index: int) -> dict:
    """Génère un asset aléatoire."""
    category = random.choice(CATEGORIES)
    criticality = random.choices(
        CRITICALITIES,
        weights=[0.1, 0.2, 0.4, 0.3]  # Distribution réaliste
    )[0]

    environment = random.choice(ENVIRONMENTS)
    if criticality == "Critical":
        environment = random.choice(["production", "network"])
    elif criticality == "Low":
        environment = random.choice(["development", "staging"])

    return {
        "asset_id": generate_asset_id(category, index),
        "name": f"{category} {index:04d}",
        "hostname": f"{category.lower()}-{index:04d}.example.com",
        "ip_address": generate_ip() if category != "Mobile" else "N/A",
        "mac_address": generate_mac() if category != "Mobile" else "N/A",
        "criticality": criticality,
        "environment": environment,
        "location": f"DC{random.randint(1, 3)}-Rack-{chr(65 + random.randint(0, 5))}{random.randint(1, 10):02d}",
        "owner": f"Team {random.randint(1, 20)}",
        "business_unit": random.choice(BUSINESS_UNITS),
        "os": random.choice(["Ubuntu 22.04", "RHEL 9", "Windows Server 2022", "Windows 11"]),
        "os_version": f"{random.randint(1, 10)}.{random.randint(0, 9)}",
        "category": category,
        "subcategory": random.choice(["Web", "Database", "Application", "Management"]),
        "regulations": random.sample(REGULATIONS, k=random.randint(0, 3)),
        "tags": random.sample(["critical-infra", "internet-facing", "customer-data", "internal"], k=random.randint(1, 3)),
        "last_scan": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat() + "Z",
        "created_at": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat() + "Z"
    }


def generate_vulnerabilities_csv(output_path: Path, count: int, asset_ids: list[str]):
    """Génère un fichier CSV de vulnérabilités."""
    fieldnames = [
        "cve_id", "cvss_score", "epss_score", "kev", "exploit_type",
        "asset_id", "asset_name", "asset_ip", "asset_criticality",
        "regulation", "description"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(count):
            vuln = generate_vulnerability(asset_ids)
            row = {
                "cve_id": vuln["cve_id"],
                "cvss_score": vuln["cvss_score"],
                "epss_score": vuln["epss_score"],
                "kev": str(vuln["kev"]).lower(),
                "exploit_type": vuln["exploit_type"],
                "asset_id": vuln["asset_id"],
                "asset_name": vuln["product"],
                "asset_ip": generate_ip(),
                "asset_criticality": random.choice(CRITICALITIES),
                "regulation": random.choice(REGULATIONS),
                "description": vuln["description"]
            }
            writer.writerow(row)

            if (i + 1) % 1000 == 0:
                print(f"  Généré {i + 1}/{count} vulnérabilités...")

    print(f"Fichier créé: {output_path}")


def generate_cmdb_json(output_path: Path, count: int):
    """Génère un fichier CMDB JSON."""
    assets = [generate_asset(i) for i in range(1, count + 1)]

    cmdb = {
        "assets": assets,
        "metadata": {
            "version": "1.0",
            "last_updated": datetime.now().isoformat() + "Z",
            "total_assets": count,
            "source": "Generated test data"
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cmdb, f, indent=2, ensure_ascii=False)

    print(f"Fichier créé: {output_path}")
    return [a["asset_id"] for a in assets]


def main():
    parser = argparse.ArgumentParser(description="Génère des données de test pour TreeVuln")
    parser.add_argument("--vulns", type=int, default=1000, help="Nombre de vulnérabilités")
    parser.add_argument("--assets", type=int, default=100, help="Nombre d'assets")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "data", help="Dossier de sortie")
    parser.add_argument("--prefix", default="generated", help="Préfixe des fichiers")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Génération de données de test")
    print(f"  Assets: {args.assets}")
    print(f"  Vulnérabilités: {args.vulns}")
    print(f"  Dossier: {args.output_dir}")
    print()

    # Génère les assets
    cmdb_path = args.output_dir / f"{args.prefix}_cmdb.json"
    print(f"Génération de {args.assets} assets...")
    asset_ids = generate_cmdb_json(cmdb_path, args.assets)

    # Génère les vulnérabilités
    vulns_path = args.output_dir / f"{args.prefix}_vulnerabilities.csv"
    print(f"Génération de {args.vulns} vulnérabilités...")
    generate_vulnerabilities_csv(vulns_path, args.vulns, asset_ids)

    print()
    print("Génération terminée!")
    print(f"  CMDB: {cmdb_path}")
    print(f"  Vulnérabilités: {vulns_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
