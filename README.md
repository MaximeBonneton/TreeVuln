# TreeVuln - SSVC Decision Tree Builder

Outil de priorisation de vulnérabilités basé sur la méthodologie **SSVC** (Stakeholder-Specific Vulnerability Categorization).

Construisez graphiquement vos arbres de décision et utilisez-les pour traiter automatiquement des volumes massifs de vulnérabilités.

## Fonctionnalités

- **Éditeur visuel** : Construisez vos arbres de décision par glisser-déposer
- **Méthodologie SSVC** : Arbre par défaut implémentant les 4 critères SSVC
- **API REST** : Évaluez vos vulnérabilités en batch via API
- **Audit trail** : Tracez le chemin de décision complet pour chaque évaluation
- **Multi-arbres** : Gérez plusieurs arbres avec contextes isolés
- **Référentiel d'assets** : Enrichissez vos décisions avec la criticité des assets

## Installation rapide

### Prérequis

- Docker et Docker Compose

### Démarrage

```bash
# Cloner le repository
git clone <repository-url>
cd TreeVuln

# Lancer l'application
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps
```

### Accès

| Service | URL |
|---------|-----|
| Application | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentation API | http://localhost:8000/docs |

## Guide d'utilisation

### 1. Interface principale

L'interface se compose de 3 zones :

```
┌─────────────────────────────────────────────────────────────┐
│  Toolbar (Sauvegarder, Annuler, Historique, Test)          │
├──────────┬─────────────────────────────────┬───────────────┤
│          │                                 │               │
│ Sidebar  │      Zone de travail            │    Panel de   │
│ (Arbres) │      (React Flow)               │ configuration │
│          │                                 │               │
└──────────┴─────────────────────────────────┴───────────────┘
```

### 2. Créer un arbre de décision

#### Types de nœuds disponibles

| Type | Description | Utilisation |
|------|-------------|-------------|
| **Input** | Lit un champ de la vulnérabilité | CVSS, EPSS, KEV, etc. |
| **Lookup** | Recherche dans une table externe | Criticité d'un asset |
| **Output** | Décision finale | Act, Attend, Track*, Track |

#### Ajouter un nœud

1. Cliquez sur un type de nœud dans la barre d'outils
2. Le nœud apparaît dans la zone de travail
3. Glissez-le à la position souhaitée

#### Configurer un nœud

1. Cliquez sur un nœud pour ouvrir le panneau de configuration
2. Définissez le champ à évaluer (pour Input/Lookup)
3. Ajoutez des conditions de sortie avec leurs opérateurs

#### Connecter les nœuds

1. Cliquez sur un handle de sortie (rond à droite du nœud)
2. Glissez vers le nœud cible
3. Relâchez sur le handle d'entrée (rond à gauche)

### 3. Conditions de sortie

Chaque nœud (sauf Output) définit des conditions qui déterminent la branche à suivre.

#### Opérateurs disponibles

| Opérateur | Description | Exemple |
|-----------|-------------|---------|
| `=` | Égal | `kev = true` |
| `≠` | Différent | `status ≠ "closed"` |
| `>` | Supérieur | `cvss_score > 7` |
| `>=` | Supérieur ou égal | `epss_score >= 0.2` |
| `<` | Inférieur | `cvss_score < 4` |
| `<=` | Inférieur ou égal | `epss_score <= 0.1` |
| `in` | Dans une liste | `criticality in ["High", "Critical"]` |
| `contains` | Contient | `description contains "RCE"` |
| `is_null` | Est null/vide | `kev is_null` |
| `regex` | Expression régulière | `cve_id regex "CVE-2024-.*"` |

#### Types de valeurs

L'éditeur de conditions supporte 3 types de valeurs :
- **Texte** : `"High"`, `"CVE-2024-1234"`
- **Nombre** : `9.0`, `0.2`
- **Booléen** : `true`, `false`

### 4. Tester l'arbre

1. Cliquez sur **Test** dans la toolbar
2. Saisissez un JSON de vulnérabilité :

```json
{
  "cve_id": "CVE-2024-1234",
  "kev": true,
  "epss_score": 0.5,
  "cvss_score": 9.8,
  "asset_criticality": "High"
}
```

3. Cliquez sur **Évaluer**
4. Le chemin de décision s'affiche avec la décision finale

### 5. Gérer les assets

Le référentiel d'assets permet d'enrichir les décisions avec des données contextuelles.

1. Cliquez sur l'onglet **Assets** dans la sidebar
2. Ajoutez vos assets avec leur criticité (Low, Medium, High, Critical)
3. Utilisez un nœud **Lookup** pour récupérer la criticité via `asset_id`

## Arbre SSVC par défaut

L'application inclut un arbre SSVC complet évaluant 4 critères :

### Critères d'évaluation

| Critère | Champ | Valeurs |
|---------|-------|---------|
| **Exploitation** | `kev` | null → None, false → PoC, true → Active |
| **Automatable** | `epss_score` | < 0.2 → No, >= 0.2 → Yes |
| **Technical Impact** | `cvss_score` | < 9 → Partial, >= 9 → Total |
| **Mission & Well-being** | `asset_criticality` | Low, Medium, High, Critical |

### Décisions possibles

| Décision | Couleur | Signification |
|----------|---------|---------------|
| **Act** | Rouge | Action immédiate requise |
| **Attend** | Orange | Surveillance active, planifier correction |
| **Track*** | Jaune | Suivre de près |
| **Track** | Vert | Suivre dans le flux normal |

## Utilisation de l'API

### Évaluer une vulnérabilité

```bash
curl -X POST 'http://localhost:8000/api/v1/evaluate/single' \
  -H 'Content-Type: application/json' \
  -d '{
    "vulnerability": {
      "cve_id": "CVE-2024-1234",
      "kev": true,
      "epss_score": 0.5,
      "cvss_score": 9.8,
      "asset_criticality": "High"
    }
  }'
```

**Réponse :**

```json
{
  "vuln_id": "CVE-2024-1234",
  "decision": "Act",
  "decision_color": "#dc2626",
  "path": [
    {
      "node_id": "exploitation",
      "node_label": "Exploitation",
      "field_evaluated": "kev",
      "value_found": true,
      "condition_matched": "Active"
    },
    ...
  ]
}
```

### Évaluer un batch

```bash
curl -X POST 'http://localhost:8000/api/v1/evaluate' \
  -H 'Content-Type: application/json' \
  -d '{
    "vulnerabilities": [
      {"cve_id": "CVE-2024-001", "kev": true, "epss_score": 0.5, "cvss_score": 9.8, "asset_criticality": "High"},
      {"cve_id": "CVE-2024-002", "kev": false, "epss_score": 0.1, "cvss_score": 5.0, "asset_criticality": "Low"}
    ]
  }'
```

### Évaluer un fichier CSV

```bash
curl -X POST 'http://localhost:8000/api/v1/evaluate/csv' \
  -F 'file=@vulnerabilities.csv'
```

Format CSV attendu :
```csv
cve_id,kev,epss_score,cvss_score,asset_criticality
CVE-2024-001,true,0.5,9.8,High
CVE-2024-002,false,0.1,5.0,Low
```

### Endpoints principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/trees` | Liste tous les arbres |
| GET | `/api/v1/tree` | Récupère l'arbre par défaut |
| POST | `/api/v1/tree` | Sauvegarde l'arbre |
| POST | `/api/v1/evaluate/single` | Évalue 1 vulnérabilité |
| POST | `/api/v1/evaluate` | Évalue un batch JSON |
| POST | `/api/v1/evaluate/csv` | Évalue un fichier CSV |
| GET | `/api/v1/assets` | Liste les assets |

## Configuration avancée

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | (voir docker-compose) | URL PostgreSQL |
| `BACKEND_PORT` | 8000 | Port du backend |
| `FRONTEND_PORT` | 3000 | Port du frontend |

### Multi-arbres

Chaque arbre peut avoir :
- Son propre référentiel d'assets (contexte isolé)
- Une API dédiée via un slug personnalisé

```bash
# Activer l'API dédiée pour un arbre
curl -X PUT 'http://localhost:8000/api/v1/tree/1/api-config' \
  -H 'Content-Type: application/json' \
  -d '{"api_enabled": true, "api_slug": "mon-arbre"}'

# Évaluer via l'URL dédiée
curl -X POST 'http://localhost:8000/api/v1/evaluate/tree/mon-arbre' \
  -H 'Content-Type: application/json' \
  -d '{"vulnerability": {...}}'
```

## Commandes utiles

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Voir les logs
docker compose logs -f backend

# Réinitialiser la base de données
docker compose down -v && docker compose up -d

# Reconstruire après modification du code
docker compose up -d --build
```

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | React 18, TypeScript, React Flow, TailwindCSS, Zustand |
| Backend | FastAPI, Pydantic v2, Polars, SQLAlchemy 2.0 async |
| Base de données | PostgreSQL 15 |
| Déploiement | Docker Compose |

## Licence

[À définir]

## Support

Pour signaler un bug ou demander une fonctionnalité, ouvrez une issue sur le repository.
