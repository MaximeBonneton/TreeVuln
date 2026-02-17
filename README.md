# TreeVuln - SSVC Decision Tree Builder

Outil de priorisation de vulnérabilités basé sur la méthodologie **SSVC** (Stakeholder-Specific Vulnerability Categorization).

Construisez graphiquement vos arbres de décision et utilisez-les pour traiter automatiquement des volumes massifs de vulnérabilités.

## Fonctionnalités

- **Editeur visuel** : Construisez vos arbres de décision par glisser-deposer
- **Methodologie SSVC** : Arbre par defaut implementant les 4 criteres SSVC
- **4 types de noeuds** : Input, Lookup, Equation et Output
- **Conditions composees** : Combinez plusieurs criteres avec AND/OR sur les branches
- **Noeuds multi-entrees** : Optimisez vos arbres en mutualisant les noeuds similaires
- **Noeud Equation** : Calculez des scores personnalises via formules mathematiques avec mapping texte vers nombre
- **Parsing CVSS** : Extrayez les metriques individuelles des vecteurs CVSS (v3.1 et v4.0)
- **Multi-arbres** : Gerez plusieurs arbres avec contextes isoles et API dediee par arbre
- **Referentiel d'assets** : Enrichissez vos decisions avec la criticite des assets
- **Import/Export** : Import bulk d'assets (CSV/JSON) et export des resultats d'evaluation
- **Webhooks sortants** : Notifications vers ticketing/SIEM (HMAC-SHA256, retry, logs)
- **Webhooks entrants** : Ingestion temps reel avec mapping de champs et cle API
- **Audit trail** : Tracez le chemin de decision complet pour chaque evaluation
- **Versioning** : Historique des modifications avec restauration

## Installation rapide

### Prerequis

- Docker et Docker Compose

### Demarrage

```bash
# Cloner le repository
git clone <repository-url>
cd TreeVuln

# Lancer l'application
docker compose up -d

# Verifier que tout fonctionne
docker compose ps
```

### Acces

| Service | URL |
|---------|-----|
| Application | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentation API | http://localhost:8000/docs |

## Guide d'utilisation

### 1. Interface principale

L'interface se compose de 3 zones :

```
+-------------------------------------------------------------+
|  Toolbar (Sauvegarder, Annuler, Historique, Test)            |
+----------+---------------------------------+-----------------+
|          |                                 |                 |
| Sidebar  |      Zone de travail            |    Panel de     |
| (Arbres) |      (React Flow)               | configuration   |
|          |                                 |                 |
+----------+---------------------------------+-----------------+
```

### 2. Creer un arbre de decision

#### Types de noeuds disponibles

| Type | Description | Utilisation |
|------|-------------|-------------|
| **Input** | Lit un champ de la vulnerabilite | CVSS, EPSS, KEV, etc. |
| **Lookup** | Recherche dans une table externe | Criticite d'un asset |
| **Equation** | Calcule un score via formule | Score de risque composite |
| **Output** | Decision finale | Act, Attend, Track*, Track |

#### Ajouter un noeud

1. Cliquez sur un type de noeud dans la palette
2. Le noeud apparait dans la zone de travail
3. Glissez-le a la position souhaitee

#### Configurer un noeud

1. Cliquez sur un noeud pour ouvrir le panneau de configuration
2. Definissez le champ a evaluer (pour Input/Lookup) ou la formule (pour Equation)
3. Ajoutez des conditions de sortie avec leurs operateurs

#### Connecter les noeuds

1. Cliquez sur un handle de sortie (rond a droite du noeud)
2. Glissez vers le noeud cible
3. Relachez sur le handle d'entree (rond a gauche)

### 3. Conditions de sortie

Chaque noeud (sauf Output) definit des conditions qui determinent la branche a suivre.

#### Operateurs disponibles

| Operateur | Description | Exemple |
|-----------|-------------|---------|
| `=` | Egal | `kev = true` |
| `!=` | Different | `status != "closed"` |
| `>` | Superieur | `cvss_score > 7` |
| `>=` | Superieur ou egal | `epss_score >= 0.2` |
| `<` | Inferieur | `cvss_score < 4` |
| `<=` | Inferieur ou egal | `epss_score <= 0.1` |
| `in` | Dans une liste | `criticality in ["High", "Critical"]` |
| `contains` | Contient | `description contains "RCE"` |
| `is_null` | Est null/vide | `kev is_null` |
| `regex` | Expression reguliere | `cve_id regex "CVE-2024-.*"` |

#### Types de valeurs

L'editeur de conditions supporte 3 types de valeurs :
- **Texte** : `"High"`, `"CVE-2024-1234"`
- **Nombre** : `9.0`, `0.2`
- **Booleen** : `true`, `false`

#### Conditions composees (AND/OR)

Pour des regles plus complexes, basculez en **mode Compose** pour combiner plusieurs criteres :

1. Cliquez sur le bouton **Compose** dans l'editeur de condition
2. Choisissez la logique : **AND** (toutes vraies) ou **OR** (au moins une vraie)
3. Ajoutez vos criteres avec le bouton **+ Ajouter critere**

Chaque critere peut evaluer un champ different :

```
+-- Branche "Critical Network Risk" ----------------+
| Logique: AND                                       |
|                                                    |
| +-- Critere 1 ---------------------------------+  |
| | Champ: cvss_av  |  =  |  Network             |  |
| +-----------------------------------------------+  |
| +-- Critere 2 ---------------------------------+  |
| | Champ: cvss_ac  |  =  |  Low                 |  |
| +-----------------------------------------------+  |
+----------------------------------------------------+
```

Cette branche ne sera suivie que si `cvss_av = "Network"` **ET** `cvss_ac = "Low"`.

### 4. Noeud Equation

Le noeud Equation permet de calculer un score numerique a partir d'une formule combinant plusieurs champs.

#### Configuration

1. Saisissez une **formule** dans le champ dedie (ex: `cvss_score * 0.4 + epss_score * 100 * 0.3`)
2. Les **variables** sont detectees automatiquement depuis la formule
3. Cliquez sur les champs disponibles pour les inserer dans la formule
4. Definissez un **label de sortie** (ex: "Risk Score")
5. Ajoutez des **conditions de seuil** pour router vers les noeuds suivants

#### Syntaxe des formules

| Element | Exemples |
|---------|----------|
| Operateurs | `+ - * / ** %` |
| Fonctions | `min() max() abs() round()` |
| Ternaire | `condition ? val_true : val_false` |
| Comparaisons | `< > <= >= == !=` |
| Logique | `and or not` |

Exemples :
```
cvss_score * 0.4 + epss_score * 100 * 0.3
max(cvss_score, epss_score * 10)
kev ? 30 : 0
```

#### Mapping de valeurs (texte vers nombre)

Les champs textuels comme `asset_criticality` ne peuvent pas etre utilises directement dans une formule. Le **mapping de valeurs** permet de leur associer une valeur numerique.

Dans la section "Mapping de valeurs" du noeud Equation :
1. Depliez la variable textuelle (ex: `asset_criticality`)
2. Ajoutez les correspondances :

| Texte | Valeur |
|-------|--------|
| Low | 1 |
| Medium | 2 |
| High | 3 |
| Critical | 4 |
| **Defaut** | **0** |

Lors de l'evaluation, `asset_criticality = "High"` sera automatiquement remplace par `3` avant le calcul de la formule. Si la valeur n'est pas trouvee dans la table, la valeur par defaut est utilisee.

### 5. Metriques CVSS

TreeVuln peut parser les vecteurs CVSS (v3.1 et v4.0) pour extraire les metriques individuelles.

#### Utilisation

1. Incluez le champ `cvss_vector` dans vos donnees de vulnerabilite :
```json
{
  "cve_id": "CVE-2024-1234",
  "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
}
```

2. Dans un noeud Input, selectionnez une metrique CVSS (groupee sous "Metriques CVSS") :

| Champ | Description | Valeurs possibles |
|-------|-------------|-------------------|
| `cvss_av` | Attack Vector | Network, Adjacent, Local, Physical |
| `cvss_ac` | Attack Complexity | Low, High |
| `cvss_pr` | Privileges Required | None, Low, High |
| `cvss_ui` | User Interaction | None, Required |
| `cvss_s` | Scope | Unchanged, Changed |
| `cvss_c` | Confidentiality Impact | None, Low, High |
| `cvss_i` | Integrity Impact | None, Low, High |
| `cvss_a` | Availability Impact | None, Low, High |

CVSS 4.0 ajoute des metriques supplementaires (`cvss_at`, `cvss_vc`, `cvss_vi`, `cvss_va`, `cvss_sc`, `cvss_si`, `cvss_sa`).

### 6. Noeuds multi-entrees

Les noeuds peuvent avoir plusieurs entrees pour mutualiser la logique de decision.

#### Configuration

Dans le panneau de configuration d'un noeud Input ou Lookup, definissez le nombre d'entrees souhaite. Chaque entree :
- Recoit une connexion independante depuis un noeud precedent
- Evalue les memes conditions
- Produit ses propres sorties vers les noeuds suivants

#### Avantage

Un arbre SSVC classique necessite ~26 noeuds. Avec les noeuds multi-entrees, le meme arbre n'en requiert que 8, tout en conservant la meme logique de decision.

### 7. Tester l'arbre

1. Cliquez sur **Test** dans la toolbar
2. Saisissez un JSON de vulnerabilite :

```json
{
  "cve_id": "CVE-2024-1234",
  "kev": true,
  "epss_score": 0.5,
  "cvss_score": 9.8,
  "asset_criticality": "High"
}
```

3. Cliquez sur **Evaluer**
4. Le chemin de decision s'affiche avec la decision finale

### 8. Gerer les assets

Le referentiel d'assets permet d'enrichir les decisions avec des donnees contextuelles.

1. Cliquez sur l'onglet **Assets** dans la sidebar
2. Ajoutez vos assets avec leur criticite (Low, Medium, High, Critical)
3. Utilisez un noeud **Lookup** pour recuperer la criticite via `asset_id`

#### Import bulk

Importez vos assets depuis un fichier CSV ou JSON :

1. Cliquez sur **Importer** dans l'onglet Assets
2. Selectionnez votre fichier
3. Previewez et mappez les colonnes
4. Validez l'import

### 9. Export des resultats

Apres une evaluation batch, exportez les resultats avec l'audit trail complet :

```bash
# Evaluer et exporter en CSV
curl -X POST 'http://localhost:8000/api/v1/evaluate/export' \
  -H 'Content-Type: application/json' \
  -d '{
    "vulnerabilities": [...],
    "format": "csv"
  }' -o results.csv

# Evaluer un CSV et exporter
curl -X POST 'http://localhost:8000/api/v1/evaluate/export/csv' \
  -F 'file=@vulns.csv' \
  -F 'format=json' -o results.json
```

### 10. Webhooks sortants

Envoyez automatiquement les resultats d'evaluation vers vos outils (ticketing, SIEM, etc.).

#### Configuration

1. Ouvrez les parametres d'un arbre
2. Ajoutez un webhook avec l'URL cible
3. Configurez les options : evenements, secret HMAC-SHA256, retry

#### Securite

Les webhooks sont signes avec HMAC-SHA256. Le header `X-Webhook-Signature` permet au destinataire de verifier l'authenticite du payload.

### 11. Webhooks entrants (ingestion)

Recevez des vulnerabilites en temps reel depuis des sources externes.

#### Configuration

1. Creez un endpoint d'ingestion pour un arbre
2. Configurez le mapping des champs (adaptation du format source)
3. Une cle API est generee automatiquement

#### Utilisation

```bash
curl -X POST 'http://localhost:8000/api/v1/ingest/mon-endpoint' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <cle-api>' \
  -d '{"cve": "CVE-2024-1234", "score": 9.8, ...}'
```

Les vulnerabilites sont evaluees automatiquement par l'arbre associe.

## Arbre SSVC par defaut

L'application inclut un arbre SSVC complet evaluant 4 criteres :

### Criteres d'evaluation

| Critere | Champ | Valeurs |
|---------|-------|---------|
| **Exploitation** | `kev` | null -> None, false -> PoC, true -> Active |
| **Automatable** | `epss_score` | < 0.2 -> No, >= 0.2 -> Yes |
| **Technical Impact** | `cvss_score` | < 9 -> Partial, >= 9 -> Total |
| **Mission & Well-being** | `asset_criticality` | Low, Medium, High, Critical |

### Decisions possibles

| Decision | Couleur | Signification |
|----------|---------|---------------|
| **Act** | Rouge | Action immediate requise |
| **Attend** | Orange | Surveillance active, planifier correction |
| **Track*** | Jaune | Suivre de pres |
| **Track** | Vert | Suivre dans le flux normal |

## Utilisation de l'API

### Evaluer une vulnerabilite

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

**Reponse :**

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
    }
  ]
}
```

### Evaluer un batch

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

### Evaluer un fichier CSV

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

#### Gestion des arbres

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/trees` | Liste tous les arbres |
| GET | `/api/v1/tree` | Recupere l'arbre par defaut |
| POST | `/api/v1/tree` | Sauvegarde l'arbre |
| GET | `/api/v1/tree/{id}/versions` | Historique des versions |
| POST | `/api/v1/tree/{id}/restore/{version_id}` | Restaurer une version |
| POST | `/api/v1/tree/{id}/duplicate` | Dupliquer un arbre |
| PUT | `/api/v1/tree/{id}/api-config` | Configurer l'API dediee |
| PUT | `/api/v1/tree/{id}/set-default` | Definir comme arbre par defaut |

#### Evaluation

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/evaluate/single` | Evaluer 1 vulnerabilite |
| POST | `/api/v1/evaluate` | Evaluer un batch JSON |
| POST | `/api/v1/evaluate/csv` | Evaluer un fichier CSV |
| POST | `/api/v1/evaluate/export` | Evaluer batch et exporter CSV/JSON |
| POST | `/api/v1/evaluate/export/csv` | Evaluer CSV et exporter CSV/JSON |
| POST | `/api/v1/evaluate/tree/{slug}` | Evaluer via API dediee d'un arbre |
| POST | `/api/v1/evaluate/tree/{slug}/batch` | Evaluer batch via API dediee |

#### Assets

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/assets?tree_id=X` | Lister les assets d'un arbre |
| POST | `/api/v1/assets` | Creer un asset |
| POST | `/api/v1/assets/import` | Import bulk depuis CSV/JSON |
| POST | `/api/v1/assets/import/preview` | Preview colonnes d'un fichier |

#### Webhooks sortants

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/tree/{tree_id}/webhooks` | Lister les webhooks d'un arbre |
| POST | `/api/v1/tree/{tree_id}/webhooks` | Creer un webhook |
| PUT | `/api/v1/webhooks/{id}` | Modifier un webhook |
| DELETE | `/api/v1/webhooks/{id}` | Supprimer un webhook |
| POST | `/api/v1/webhooks/{id}/test` | Tester un webhook |
| GET | `/api/v1/webhooks/{id}/logs` | Historique des envois |

#### Webhooks entrants (ingestion)

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/ingest/{slug}` | Recevoir et evaluer (auth X-API-Key) |
| GET | `/api/v1/tree/{tree_id}/ingest-endpoints` | Lister les endpoints |
| POST | `/api/v1/tree/{tree_id}/ingest-endpoints` | Creer un endpoint |
| PUT | `/api/v1/ingest-endpoints/{id}` | Modifier un endpoint |
| DELETE | `/api/v1/ingest-endpoints/{id}` | Supprimer un endpoint |
| POST | `/api/v1/ingest-endpoints/{id}/regenerate-key` | Regenerer cle API |
| GET | `/api/v1/ingest-endpoints/{id}/logs` | Historique des receptions |

#### Field mapping

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/mapping` | Field mapping de l'arbre |
| PUT | `/api/v1/mapping` | Mettre a jour le mapping |
| POST | `/api/v1/mapping/scan` | Scanner un fichier pour detecter les champs |
| GET | `/api/v1/mapping/cvss-fields` | Definitions des champs CVSS |

## Configuration avancee

### Variables d'environnement

| Variable | Defaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | (voir docker-compose) | URL PostgreSQL |
| `BACKEND_PORT` | 8000 | Port du backend |
| `FRONTEND_PORT` | 3000 | Port du frontend |

### Multi-arbres

Chaque arbre peut avoir :
- Son propre referentiel d'assets (contexte isole)
- Une API dediee via un slug personnalise
- Ses propres webhooks sortants et endpoints d'ingestion

```bash
# Activer l'API dediee pour un arbre
curl -X PUT 'http://localhost:8000/api/v1/tree/1/api-config' \
  -H 'Content-Type: application/json' \
  -d '{"api_enabled": true, "api_slug": "mon-arbre"}'

# Evaluer via l'URL dediee
curl -X POST 'http://localhost:8000/api/v1/evaluate/tree/mon-arbre' \
  -H 'Content-Type: application/json' \
  -d '{"vulnerability": {...}}'
```

## Commandes utiles

```bash
# Demarrer
docker compose up -d

# Arreter
docker compose down

# Voir les logs
docker compose logs -f backend

# Reinitialiser la base de donnees
docker compose down -v && docker compose up -d

# Reconstruire apres modification du code
docker compose up -d --build
```

## Developpement local (sans Docker)

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8000

# Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev
```

Necessite une instance PostgreSQL locale avec les variables d'environnement configurees.

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | React 18, TypeScript, React Flow, TailwindCSS, Zustand |
| Backend | FastAPI, Pydantic v2, Polars, SQLAlchemy 2.0 async |
| Base de donnees | PostgreSQL 15 (JSONB pour arbres) |
| Deploiement | Docker Compose |

## Structure du projet

```
TreeVuln/
├── docker-compose.yml
├── scripts/
│   └── init_db.sql
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── engine/          # Moteur d'inference (nodes, formula, inference, batch)
│       ├── services/
│       └── api/routes/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── components/
        │   ├── TreeBuilder/     # Interface drag & drop
        │   └── panels/          # Panneaux de configuration
        ├── stores/              # Etat Zustand
        ├── api/                 # Clients API
        └── types/               # Types TypeScript
```

## Licence

Ce projet est sous licence [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).

Cela signifie que vous pouvez librement utiliser, modifier et distribuer ce logiciel, a condition de :
- Conserver la meme licence pour les oeuvres derivees
- Rendre le code source disponible si vous deployez une version modifiee accessible via reseau

## Support

Pour signaler un bug ou demander une fonctionnalite, ouvrez une issue sur le repository.
