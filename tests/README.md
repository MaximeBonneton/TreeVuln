# Tests TreeVuln

Ce dossier contient les données et scripts de test pour TreeVuln.

## Structure

```
tests/
├── data/
│   ├── vulnerabilities.csv    # 30 vulnérabilités réalistes
│   └── cmdb.json              # 24 assets fictifs détaillés
├── test_api.py                # Tests fonctionnels de l'API
├── sync_cmdb.py               # Synchronisation CMDB → TreeVuln
├── generate_data.py           # Génération de données massives
└── README.md
```

## Prérequis

```bash
pip install requests
```

## Utilisation

### 1. Tests de l'API

```bash
# Tests complets
python tests/test_api.py

# Tests rapides (sans batch/CSV)
python tests/test_api.py --quick

# Tests de performance uniquement
python tests/test_api.py --perf --iterations 5

# Avec une autre URL
python tests/test_api.py --url http://localhost:8000/api/v1
```

**Sortie exemple :**
```
✓ Health Check                           [   12.3ms] API accessible
✓ Tree API                               [   15.7ms] Tree: SSVC Default Tree, Nodes: 7, Edges: 10
✓ Assets API                             [   10.2ms] Found 8 assets
✓ Single: CVE-2024-21762                 [   25.4ms] Decision: Act, Path: 3 nodes
✓ Expected: TEST-001                     [   18.9ms] Expected: Act, Got: Act (Critical CVSS + In KEV)
✓ Batch (30 vulns)                       [  120.5ms] Processed: 30, Errors: 0, Rate: 249.0 vulns/s
================================================================================
Total: 15/15 tests passed
```

### 2. Synchronisation CMDB

```bash
# Voir les changements (dry-run)
python tests/sync_cmdb.py --dry-run

# Synchroniser
python tests/sync_cmdb.py

# Avec un fichier CMDB personnalisé
python tests/sync_cmdb.py --cmdb tests/data/my_cmdb.json
```

### 3. Génération de données massives

```bash
# Générer 1000 vulns et 100 assets
python tests/generate_data.py --vulns 1000 --assets 100

# Générer 10000 vulns pour test de charge
python tests/generate_data.py --vulns 10000 --assets 500 --prefix large
```

Les fichiers générés seront dans `tests/data/`:
- `generated_cmdb.json`
- `generated_vulnerabilities.csv`

## Données de test incluses

### vulnerabilities.csv

30 vulnérabilités réalistes basées sur des CVE récents (2024) :

| Champ | Description |
|-------|-------------|
| cve_id | Identifiant CVE |
| cvss_score | Score CVSS (0-10) |
| epss_score | Score EPSS (0-1) |
| kev | Dans la liste KEV CISA (true/false) |
| exploit_type | Type d'exploit (RCE, SQLi, etc.) |
| asset_id | Référence vers la CMDB |
| asset_name | Nom de l'asset |
| asset_ip | Adresse IP |
| asset_criticality | Criticité de l'asset |
| regulation | Réglementation applicable |
| description | Description de la vulnérabilité |

### cmdb.json

24 assets représentant une infrastructure typique :

- **Serveurs production** : Web, DB, Application, E-Commerce
- **Infrastructure réseau** : Firewalls, VPN, Switches
- **Serveurs internes** : AD, VMware, CI/CD, Backup, ITSM
- **Postes de travail** : Admin, Users
- **Environnements non-prod** : Staging, Development

Chaque asset contient :
- Identifiants (asset_id, hostname, IP, MAC)
- Classification (criticality, environment, category)
- Métadonnées (owner, business_unit, location)
- Conformité (regulations, tags)

## Cas de test attendus

L'arbre SSVC par défaut produit ces décisions :

| CVSS | KEV | Asset Criticality | Décision |
|------|-----|-------------------|----------|
| ≥9 | Oui | * | **Act** |
| ≥9 | Non | * | Attend |
| 7-9 | Oui | * | **Act** |
| 7-9 | Non | * | Attend |
| 4-7 | * | Critical/High | Attend |
| 4-7 | * | Medium | Track* |
| 4-7 | * | Low | Track |
| <4 | * | * | Track |

## Test de charge

Pour tester les performances avec 10 000 vulnérabilités :

```bash
# Générer les données
python tests/generate_data.py --vulns 10000 --assets 500

# Synchroniser les assets
python tests/sync_cmdb.py --cmdb tests/data/generated_cmdb.json

# Tester les performances
python tests/test_api.py --csv tests/data/generated_vulnerabilities.csv --perf
```

Objectif : traiter 10 000 vulnérabilités/jour (soit ~7 vulns/minute en continu).
