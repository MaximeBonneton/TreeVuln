# TreeVuln — Security Decision Engine

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](docker-compose.yml)

A visual, auditable security decision engine. Build decision trees graphically and use them to automate the processing of massive volumes of vulnerabilities, non-compliance findings, cloud audits, containers, and more.

![TreeVuln — Visual decision tree editor](docs/images/tree-editor.png)

## Why TreeVuln?

Security teams are drowning in alerts. Vulnerability scanners, cloud audits, compliance checks, container reports — every tool produces hundreds of results, but none tells you **what to act on first**.

TreeVuln lets you **design your own decision logic** as a visual tree, then apply it automatically to massive data volumes. Every decision is **transparent** (full audit trail), **auditable** (exportable), and **customizable** (your criteria, your thresholds, your policy).

Whether you need to prioritize CVEs using the SSVC methodology, assess vulnerability exploitability (VEX), triage cloud non-compliance findings, or automate audit controls — TreeVuln is the engine that turns your rules into actionable decisions.

## Quick Start

```bash
git clone <repository-url> && cd TreeVuln
docker compose up -d
```

Open http://localhost:3000 — on first launch, you'll be prompted to create your admin account (no default credentials).

| Service | URL |
|---------|-----|
| Application | http://localhost:3000 |
| API | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |

<details>
<summary>More screenshots</summary>

| Node palette & sidebar | Node configuration |
|:--:|:--:|
| ![Palette](docs/images/node-palette.png) | ![Config](docs/images/node-config.png) |

| Field mapping | Test & audit trail |
|:--:|:--:|
| ![Mapping](docs/images/field-mapping.png) | ![Test](docs/images/test-panel.png) |

</details>

## Features

### Visual Editor

- **Drag & drop**: 4 node types — Input, Lookup, Equation, Output
- **Compound conditions**: combine multiple criteria with AND/OR on branches
- **Multi-input nodes**: share logic to optimize complex trees
- **Auto-layout**: reorganize nodes automatically in one click
- **Image export**: PNG or SVG for your reports and presentations

### Inference Engine

- **Single and batch evaluation**: up to 50,000 items per request
- **CVSS parsing**: automatic extraction of CVSS v3.1 and v4.0 metrics
- **Equation node**: mathematical formulas with text-to-number mapping
- **Audit trail**: full decision path for every evaluation

### Multi-tree & API

- **Isolated contexts**: each tree has its own assets, webhooks, and endpoints
- **Per-tree dedicated API**: configurable endpoint via slug (`/evaluate/tree/my-tree`)
- **Decision-as-Code**: export/import your trees as JSON to version them in Git
- **Versioning**: modification history with restore capability

### Authentication & Access Control

- **Multi-user**: username/password accounts with bcrypt hashing
- **Two roles**: admin (full access) and operator (read + evaluate)
- **Setup wizard**: first admin account created on initial launch
- **Server-side sessions**: stored in PostgreSQL, 24h expiry
- **User management**: create, deactivate, reset password, change role (admin only)

### Integration

- **Outbound webhooks**: HMAC-SHA256 notifications to ticketing/SIEM systems
- **Inbound webhooks**: real-time ingestion with field mapping and API key
- **Import/Export**: assets in CSV/JSON, results with audit trail

## Use Cases

| Domain | Example | Typical Decisions |
|--------|---------|-------------------|
| **Vulnerabilities** | Prioritization based on KEV, EPSS, CVSS, and asset criticality | Act, Attend, Track |
| **VEX** | Actual exploitability of a CVE in the product context | Not Affected, Exploitable, In Triage |
| **Cloud** | Excessive IAM permissions, open security groups, exposed buckets | Remediate, Accept, Investigate |
| **Containers** | Docker images with CVEs, root execution, plaintext secrets | Block, Alert, Ignore |
| **Compliance** | ISO 27001, SOC2, PCI-DSS controls | Compliant, Non-compliant, Exception |
| **Audit** | Maturity assessment, remediation plan | Critical, Needs Improvement, Compliant |

## API Example

Authenticate first, then evaluate a vulnerability with the default SSVC tree:

```bash
# Login (stores session cookie)
curl -c cookies.txt -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "yourpassword"}'

# Evaluate a vulnerability
curl -b cookies.txt -X POST 'http://localhost:8000/api/v1/evaluate/single' \
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

The full API is documented at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18, TypeScript, React Flow, TailwindCSS, Zustand |
| Backend | FastAPI, Pydantic v2, Polars, SQLAlchemy 2.0 async |
| Database | PostgreSQL 15 (JSONB) |
| Deployment | Docker Compose |

## Editions

### Community (free, AGPL-3.0)

Everything you need to build and run your decision trees:

- Full visual editor with drag & drop
- Inference engine (single, batch, CSV)
- Multi-user with admin/operator roles
- Multi-tree, webhooks, ingestion
- Decision-as-Code (JSON export/import)
- Auto-layout and image export (PNG/SVG)
- CVSS v3.1 and v4.0 parsing, audit trail

### Enterprise (commercial license)

For teams that need governance, integrations, and reporting:

- SSO (SAML / OIDC) and RBAC (granular roles)
- Visual Diff between tree versions
- Native connectors (Tenable, Qualys, Jira, ServiceNow)
- Specialized nodes (Threat Intel, external CMDB)
- Advanced audit trail (PDF/JSON decision certificates)
- Multi-tree reporting and What-if simulation

For an Enterprise license, contact us via the repository issues.

## Development

```bash
# Backend
cd backend && pip install -e . && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Tests
cd backend && python -m pytest tests/ -v
cd frontend && npm test
```

<details>
<summary>Useful Docker commands</summary>

```bash
docker compose up -d              # Start
docker compose down               # Stop
docker compose down -v            # Stop + delete data
docker compose up -d --build      # Rebuild
docker compose logs -f backend    # Backend logs
```

</details>

## License

TreeVuln Community source code is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).

Enterprise modules are under a separate commercial license.

## Contributing

Contributions are welcome. To report a bug or suggest a feature, open an issue on the repository.
