#!/usr/bin/env python3
"""
Script de synchronisation de la CMDB vers TreeVuln.

Charge les assets depuis le fichier cmdb.json et les synchronise
avec la base de données de TreeVuln via l'API.
"""

import argparse
import json
import sys
from pathlib import Path

import requests

DEFAULT_API_URL = "http://localhost:8000/api/v1"
DATA_DIR = Path(__file__).parent / "data"

api_base_url = DEFAULT_API_URL


def load_cmdb(filepath: Path) -> dict:
    """Charge la CMDB depuis le fichier JSON."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def get_existing_assets() -> dict[str, dict]:
    """Récupère les assets existants depuis l'API."""
    response = requests.get(f"{api_base_url}/assets", timeout=10)
    if response.status_code == 200:
        assets = response.json()
        return {a["asset_id"]: a for a in assets}
    return {}


def create_asset(asset: dict) -> bool:
    """Crée un asset via l'API."""
    payload = {
        "asset_id": asset["asset_id"],
        "name": asset["name"],
        "criticality": asset["criticality"],
        "tags": {
            "environment": asset.get("environment", ""),
            "owner": asset.get("owner", ""),
            "business_unit": asset.get("business_unit", ""),
            "category": asset.get("category", ""),
            "subcategory": asset.get("subcategory", ""),
            "regulations": asset.get("regulations", []),
            "tags": asset.get("tags", []),
        },
        "extra_data": {
            "hostname": asset.get("hostname", ""),
            "ip_address": asset.get("ip_address", ""),
            "mac_address": asset.get("mac_address", ""),
            "location": asset.get("location", ""),
            "os": asset.get("os", ""),
            "os_version": asset.get("os_version", ""),
        }
    }

    response = requests.post(
        f"{api_base_url}/assets",
        json=payload,
        timeout=10
    )
    return response.status_code in (200, 201)


def update_asset(asset_id: str, asset: dict) -> bool:
    """Met à jour un asset via l'API."""
    payload = {
        "name": asset["name"],
        "criticality": asset["criticality"],
        "tags": {
            "environment": asset.get("environment", ""),
            "owner": asset.get("owner", ""),
            "business_unit": asset.get("business_unit", ""),
            "category": asset.get("category", ""),
            "subcategory": asset.get("subcategory", ""),
            "regulations": asset.get("regulations", []),
            "tags": asset.get("tags", []),
        },
        "extra_data": {
            "hostname": asset.get("hostname", ""),
            "ip_address": asset.get("ip_address", ""),
            "mac_address": asset.get("mac_address", ""),
            "location": asset.get("location", ""),
            "os": asset.get("os", ""),
            "os_version": asset.get("os_version", ""),
        }
    }

    response = requests.put(
        f"{api_base_url}/assets/{asset_id}",
        json=payload,
        timeout=10
    )
    return response.status_code == 200


def sync_cmdb(cmdb_path: Path, dry_run: bool = False) -> tuple[int, int, int]:
    """
    Synchronise la CMDB avec TreeVuln.

    Returns:
        Tuple (created, updated, errors)
    """
    cmdb = load_cmdb(cmdb_path)
    existing = get_existing_assets()

    created = 0
    updated = 0
    errors = 0

    print(f"\nCMDB: {len(cmdb['assets'])} assets")
    print(f"Existants: {len(existing)} assets")
    print("-" * 50)

    for asset in cmdb["assets"]:
        asset_id = asset["asset_id"]
        action = "UPDATE" if asset_id in existing else "CREATE"

        if dry_run:
            print(f"[DRY-RUN] {action}: {asset_id} ({asset['name']})")
            if action == "CREATE":
                created += 1
            else:
                updated += 1
            continue

        try:
            if asset_id in existing:
                if update_asset(asset_id, asset):
                    print(f"[UPDATE] {asset_id}: {asset['name']}")
                    updated += 1
                else:
                    print(f"[ERROR] Update failed: {asset_id}")
                    errors += 1
            else:
                if create_asset(asset):
                    print(f"[CREATE] {asset_id}: {asset['name']}")
                    created += 1
                else:
                    print(f"[ERROR] Create failed: {asset_id}")
                    errors += 1
        except Exception as e:
            print(f"[ERROR] {asset_id}: {e}")
            errors += 1

    return created, updated, errors


def main():
    global api_base_url

    parser = argparse.ArgumentParser(description="Synchronise la CMDB avec TreeVuln")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="URL de base de l'API")
    parser.add_argument("--cmdb", type=Path, default=DATA_DIR / "cmdb.json", help="Fichier CMDB")
    parser.add_argument("--dry-run", action="store_true", help="Simule sans modifier")
    args = parser.parse_args()

    api_base_url = args.url

    print(f"TreeVuln CMDB Sync")
    print(f"API URL: {api_base_url}")
    print(f"CMDB File: {args.cmdb}")

    if not args.cmdb.exists():
        print(f"\nErreur: Fichier CMDB non trouvé: {args.cmdb}")
        return 1

    created, updated, errors = sync_cmdb(args.cmdb, args.dry_run)

    print("-" * 50)
    print(f"Résumé: {created} créés, {updated} mis à jour, {errors} erreurs")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
