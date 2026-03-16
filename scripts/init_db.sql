-- Script d'initialisation de la base de données TreeVuln
-- Ce script crée les tables et insère des données de test pour le développement

-- Création de la table trees
CREATE TABLE IF NOT EXISTS trees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'Main Tree',
    description VARCHAR(1000),
    structure JSONB NOT NULL DEFAULT '{}',
    -- Multi-arbres: gestion du défaut et API
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    api_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    api_slug VARCHAR(100) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour l'arbre par défaut (un seul autorisé)
CREATE UNIQUE INDEX IF NOT EXISTS idx_trees_default ON trees(is_default) WHERE is_default = TRUE;
-- Index pour la recherche par slug API
CREATE INDEX IF NOT EXISTS idx_trees_api_slug ON trees(api_slug) WHERE api_slug IS NOT NULL;

-- Création de la table tree_versions
CREATE TABLE IF NOT EXISTS tree_versions (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    structure_snapshot JSONB NOT NULL,
    comment VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tree_versions_tree_id ON tree_versions(tree_id);

-- Création de la table assets
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    -- Multi-arbres: FK vers l'arbre propriétaire
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    asset_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    criticality VARCHAR(50) NOT NULL DEFAULT 'Medium',
    tags JSONB NOT NULL DEFAULT '{}',
    extra_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Contrainte unique sur (tree_id, asset_id) au lieu de asset_id seul
    CONSTRAINT assets_tree_asset_unique UNIQUE (tree_id, asset_id)
);

-- Index pour la recherche d'assets par arbre et asset_id
CREATE INDEX IF NOT EXISTS idx_assets_tree_asset_id ON assets(tree_id, asset_id);

-- Création de la table webhooks
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    secret VARCHAR(255),
    headers JSONB NOT NULL DEFAULT '{}',
    events TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_tree_id ON webhooks(tree_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_tree_active ON webhooks(tree_id, is_active);

-- Création de la table webhook_logs
CREATE TABLE IF NOT EXISTS webhook_logs (
    id SERIAL PRIMARY KEY,
    webhook_id INTEGER NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    status_code INTEGER,
    request_body JSONB NOT NULL DEFAULT '{}',
    response_body VARCHAR(10000),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message VARCHAR(2000),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created ON webhook_logs(webhook_id, created_at);

-- Création de la table ingest_endpoints
CREATE TABLE IF NOT EXISTS ingest_endpoints (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    api_key VARCHAR(255) NOT NULL,
    field_mapping JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    auto_evaluate BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_endpoints_slug ON ingest_endpoints(slug);
CREATE INDEX IF NOT EXISTS idx_ingest_endpoints_tree_id ON ingest_endpoints(tree_id);

-- Création de la table ingest_logs
CREATE TABLE IF NOT EXISTS ingest_logs (
    id SERIAL PRIMARY KEY,
    endpoint_id INTEGER NOT NULL REFERENCES ingest_endpoints(id) ON DELETE CASCADE,
    source_ip VARCHAR(45),
    payload_size INTEGER,
    vuln_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_logs_endpoint_id ON ingest_logs(endpoint_id);

-- Insertion d'un arbre de décision SSVC OPTIMISE avec multi-input (arbre par défaut)
-- Critères : Exploitation (KEV), Automatable (EPSS >= 0.2), Technical Impact (CVSS >= 9), Mission & Well-being (asset_criticality)
-- Structure optimisée : 8 nœuds au lieu de 26 grâce aux entrées multiples
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'Default Tree',
    'Arbre SSVC optimise - Priorisation des vulnerabilites avec multi-input',
    TRUE,
    FALSE,
    NULL,
    '{
        "nodes": [
            {
                "id": "exploitation",
                "type": "input",
                "label": "Exploitation",
                "position": {"x": -465, "y": 300},
                "config": {"field": "kev"},
                "conditions": [
                    {"operator": "is_null", "value": null, "label": "None"},
                    {"operator": "eq", "value": false, "label": "PoC"},
                    {"operator": "eq", "value": true, "label": "Active"}
                ]
            },
            {
                "id": "automatable",
                "type": "input",
                "label": "Automatable",
                "position": {"x": -120, "y": 300},
                "config": {"field": "epss_score", "input_count": 3},
                "conditions": [
                    {"operator": "lt", "value": 0.2, "label": "No"},
                    {"operator": "gte", "value": 0.2, "label": "Yes"}
                ]
            },
            {
                "id": "tech-impact",
                "type": "input",
                "label": "Technical Impact",
                "position": {"x": 225, "y": 300},
                "config": {"field": "cvss_score", "input_count": 6},
                "conditions": [
                    {"operator": "lt", "value": 9, "label": "Partial"},
                    {"operator": "gte", "value": 9, "label": "Total"}
                ]
            },
            {
                "id": "mission",
                "type": "input",
                "label": "Mission & Well-being",
                "position": {"x": 660, "y": 300},
                "config": {"field": "asset_criticality", "input_count": 12},
                "conditions": [
                    {"operator": "eq", "value": "Low", "label": "Low"},
                    {"operator": "eq", "value": "Medium", "label": "Medium"},
                    {"operator": "in", "value": ["High", "Critical"], "label": "High"}
                ]
            },
            {
                "id": "output-track",
                "type": "output",
                "label": "Track",
                "position": {"x": 1170, "y": 330},
                "config": {"decision": "Track", "color": "#22c55e"},
                "conditions": []
            },
            {
                "id": "output-track-star",
                "type": "output",
                "label": "Track*",
                "position": {"x": 1170, "y": 525},
                "config": {"decision": "Track*", "color": "#eab308"},
                "conditions": []
            },
            {
                "id": "output-attend",
                "type": "output",
                "label": "Attend",
                "position": {"x": 1170, "y": 765},
                "config": {"decision": "Attend", "color": "#f97316"},
                "conditions": []
            },
            {
                "id": "output-act",
                "type": "output",
                "label": "Act",
                "position": {"x": 1170, "y": 1005},
                "config": {"decision": "Act", "color": "#dc2626"},
                "conditions": []
            }
        ],
        "edges": [
            {"id": "e-exp-none", "source": "exploitation", "target": "automatable", "source_handle": "handle-0", "target_handle": "input-0"},
            {"id": "e-exp-poc", "source": "exploitation", "target": "automatable", "source_handle": "handle-1", "target_handle": "input-1"},
            {"id": "e-exp-active", "source": "exploitation", "target": "automatable", "source_handle": "handle-2", "target_handle": "input-2"},

            {"id": "e-auto-0-no", "source": "automatable", "target": "tech-impact", "source_handle": "handle-0-0", "target_handle": "input-0"},
            {"id": "e-auto-0-yes", "source": "automatable", "target": "tech-impact", "source_handle": "handle-0-1", "target_handle": "input-1"},
            {"id": "e-auto-1-no", "source": "automatable", "target": "tech-impact", "source_handle": "handle-1-0", "target_handle": "input-2"},
            {"id": "e-auto-1-yes", "source": "automatable", "target": "tech-impact", "source_handle": "handle-1-1", "target_handle": "input-3"},
            {"id": "e-auto-2-no", "source": "automatable", "target": "tech-impact", "source_handle": "handle-2-0", "target_handle": "input-4"},
            {"id": "e-auto-2-yes", "source": "automatable", "target": "tech-impact", "source_handle": "handle-2-1", "target_handle": "input-5"},

            {"id": "e-tech-0-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-0-0", "target_handle": "input-0"},
            {"id": "e-tech-0-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-0-1", "target_handle": "input-1"},
            {"id": "e-tech-1-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-1-0", "target_handle": "input-2"},
            {"id": "e-tech-1-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-1-1", "target_handle": "input-3"},
            {"id": "e-tech-2-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-2-0", "target_handle": "input-4"},
            {"id": "e-tech-2-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-2-1", "target_handle": "input-5"},
            {"id": "e-tech-3-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-3-0", "target_handle": "input-6"},
            {"id": "e-tech-3-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-3-1", "target_handle": "input-7"},
            {"id": "e-tech-4-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-4-0", "target_handle": "input-8"},
            {"id": "e-tech-4-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-4-1", "target_handle": "input-9"},
            {"id": "e-tech-5-p", "source": "tech-impact", "target": "mission", "source_handle": "handle-5-0", "target_handle": "input-10"},
            {"id": "e-tech-5-t", "source": "tech-impact", "target": "mission", "source_handle": "handle-5-1", "target_handle": "input-11"},

            {"id": "e-m0-l", "source": "mission", "target": "output-track", "source_handle": "handle-0-0"},
            {"id": "e-m0-m", "source": "mission", "target": "output-track", "source_handle": "handle-0-1"},
            {"id": "e-m0-h", "source": "mission", "target": "output-track", "source_handle": "handle-0-2"},
            {"id": "e-m1-l", "source": "mission", "target": "output-track", "source_handle": "handle-1-0"},
            {"id": "e-m1-m", "source": "mission", "target": "output-track", "source_handle": "handle-1-1"},
            {"id": "e-m1-h", "source": "mission", "target": "output-track-star", "source_handle": "handle-1-2"},
            {"id": "e-m2-l", "source": "mission", "target": "output-track", "source_handle": "handle-2-0"},
            {"id": "e-m2-m", "source": "mission", "target": "output-track", "source_handle": "handle-2-1"},
            {"id": "e-m2-h", "source": "mission", "target": "output-attend", "source_handle": "handle-2-2"},
            {"id": "e-m3-l", "source": "mission", "target": "output-track", "source_handle": "handle-3-0"},
            {"id": "e-m3-m", "source": "mission", "target": "output-track", "source_handle": "handle-3-1"},
            {"id": "e-m3-h", "source": "mission", "target": "output-attend", "source_handle": "handle-3-2"},
            {"id": "e-m4-l", "source": "mission", "target": "output-track", "source_handle": "handle-4-0"},
            {"id": "e-m4-m", "source": "mission", "target": "output-track", "source_handle": "handle-4-1"},
            {"id": "e-m4-h", "source": "mission", "target": "output-track-star", "source_handle": "handle-4-2"},
            {"id": "e-m5-l", "source": "mission", "target": "output-track", "source_handle": "handle-5-0"},
            {"id": "e-m5-m", "source": "mission", "target": "output-track-star", "source_handle": "handle-5-1"},
            {"id": "e-m5-h", "source": "mission", "target": "output-attend", "source_handle": "handle-5-2"},
            {"id": "e-m6-l", "source": "mission", "target": "output-track", "source_handle": "handle-6-0"},
            {"id": "e-m6-m", "source": "mission", "target": "output-track", "source_handle": "handle-6-1"},
            {"id": "e-m6-h", "source": "mission", "target": "output-attend", "source_handle": "handle-6-2"},
            {"id": "e-m7-l", "source": "mission", "target": "output-track", "source_handle": "handle-7-0"},
            {"id": "e-m7-m", "source": "mission", "target": "output-track", "source_handle": "handle-7-1"},
            {"id": "e-m7-h", "source": "mission", "target": "output-attend", "source_handle": "handle-7-2"},
            {"id": "e-m8-l", "source": "mission", "target": "output-track", "source_handle": "handle-8-0"},
            {"id": "e-m8-m", "source": "mission", "target": "output-track", "source_handle": "handle-8-1"},
            {"id": "e-m8-h", "source": "mission", "target": "output-attend", "source_handle": "handle-8-2"},
            {"id": "e-m9-l", "source": "mission", "target": "output-track", "source_handle": "handle-9-0"},
            {"id": "e-m9-m", "source": "mission", "target": "output-attend", "source_handle": "handle-9-1"},
            {"id": "e-m9-h", "source": "mission", "target": "output-act", "source_handle": "handle-9-2"},
            {"id": "e-m10-l", "source": "mission", "target": "output-attend", "source_handle": "handle-10-0"},
            {"id": "e-m10-m", "source": "mission", "target": "output-attend", "source_handle": "handle-10-1"},
            {"id": "e-m10-h", "source": "mission", "target": "output-act", "source_handle": "handle-10-2"},
            {"id": "e-m11-l", "source": "mission", "target": "output-attend", "source_handle": "handle-11-0"},
            {"id": "e-m11-m", "source": "mission", "target": "output-act", "source_handle": "handle-11-1"},
            {"id": "e-m11-h", "source": "mission", "target": "output-act", "source_handle": "handle-11-2"}
        ],
        "metadata": {
            "viewport": {"x": 0, "y": 0, "zoom": 0.8},
            "field_mapping": {
                "fields": [
                    {"name": "cve_id", "label": "CVE ID", "type": "string", "description": "Identifiant CVE de la vulnerabilite", "examples": ["CVE-2024-1234", "CVE-2023-5678"], "required": false},
                    {"name": "kev", "label": "KEV Status", "type": "boolean", "description": "Presence dans la liste KEV de CISA (true = exploit actif, false = PoC, null = aucune info)", "examples": [true, false, null], "required": false},
                    {"name": "epss_score", "label": "Score EPSS", "type": "number", "description": "Score EPSS (0-1). >= 0.2 = automatisable", "examples": [0.95, 0.12, 0.003], "required": true},
                    {"name": "cvss_score", "label": "Score CVSS", "type": "number", "description": "Score CVSS (0-10). >= 9 = impact total", "examples": [9.8, 7.5, 4.2], "required": true},
                    {"name": "cvss_vector", "label": "Vecteur CVSS", "type": "string", "description": "Vecteur CVSS complet (3.1 ou 4.0). Permet d extraire les metriques individuelles", "examples": ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"], "required": false},
                    {"name": "asset_criticality", "label": "Asset Criticality", "type": "string", "description": "Criticite de l asset (Low, Medium, High, Critical)", "examples": ["Low", "Medium", "High", "Critical"], "required": true}
                ],
                "source": "default",
                "version": 3
            }
        }
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Insertion d'assets de test (liés à l'arbre par défaut)
-- On utilise une sous-requête pour récupérer l'ID de l'arbre par défaut
INSERT INTO assets (tree_id, asset_id, name, criticality, tags, extra_data)
SELECT
    (SELECT id FROM trees WHERE is_default = TRUE),
    asset_id, name, criticality, tags::jsonb, extra_data::jsonb
FROM (VALUES
    ('srv-prod-001', 'Production Web Server', 'Critical', '{"environment": "production", "team": "platform"}', '{"os": "Ubuntu 22.04", "role": "web"}'),
    ('srv-prod-002', 'Production DB Server', 'Critical', '{"environment": "production", "team": "data"}', '{"os": "Ubuntu 22.04", "role": "database"}'),
    ('srv-staging-001', 'Staging Web Server', 'Medium', '{"environment": "staging", "team": "platform"}', '{"os": "Ubuntu 22.04", "role": "web"}'),
    ('srv-dev-001', 'Development Server', 'Low', '{"environment": "development", "team": "dev"}', '{"os": "Ubuntu 22.04", "role": "dev"}'),
    ('ws-admin-001', 'Admin Workstation', 'High', '{"environment": "corporate", "team": "it"}', '{"os": "Windows 11", "role": "workstation"}'),
    ('ws-user-001', 'User Workstation', 'Medium', '{"environment": "corporate", "team": "sales"}', '{"os": "Windows 11", "role": "workstation"}'),
    ('net-fw-001', 'Main Firewall', 'Critical', '{"environment": "network", "team": "security"}', '{"vendor": "Palo Alto", "role": "firewall"}'),
    ('net-sw-001', 'Core Switch', 'High', '{"environment": "network", "team": "network"}', '{"vendor": "Cisco", "role": "switch"}')
) AS t(asset_id, name, criticality, tags, extra_data)
ON CONFLICT (tree_id, asset_id) DO NOTHING;

-- =============================================================================
-- Arbre VEX Triage — Determine l'exploitabilite d'une vulnerabilite dans son contexte
-- Criteres : composant deploye, code atteignable, exposition reseau, controle compensatoire
-- Sorties : not_affected, in_triage, exploitable (statuts CycloneDX VEX)
-- =============================================================================
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'VEX Triage',
    'Arbre de triage VEX — Determine si une vulnerabilite est reellement exploitable dans le contexte du produit. Produit des statuts CycloneDX VEX standardises.',
    FALSE,
    TRUE,
    'vex-triage',
    '{
        "nodes": [
            {
                "id": "component-deployed",
                "type": "input",
                "label": "Composant deploye ?",
                "position": {"x": 0, "y": 300},
                "config": {"field": "component_deployed"},
                "conditions": [
                    {"operator": "eq", "value": false, "label": "Non"},
                    {"operator": "eq", "value": true, "label": "Oui"}
                ]
            },
            {
                "id": "code-reachable",
                "type": "input",
                "label": "Code atteignable ?",
                "position": {"x": 350, "y": 300},
                "config": {"field": "code_reachable"},
                "conditions": [
                    {"operator": "eq", "value": "unknown", "label": "Inconnu"},
                    {"operator": "eq", "value": false, "label": "Non"},
                    {"operator": "eq", "value": true, "label": "Oui"}
                ]
            },
            {
                "id": "network-exposed",
                "type": "input",
                "label": "Expose au reseau ?",
                "position": {"x": 700, "y": 300},
                "config": {"field": "network_exposed"},
                "conditions": [
                    {"operator": "eq", "value": false, "label": "Non"},
                    {"operator": "eq", "value": true, "label": "Oui"}
                ]
            },
            {
                "id": "compensating-ctrl-internal",
                "type": "input",
                "label": "Controle compensatoire ?",
                "position": {"x": 1050, "y": 150},
                "config": {"field": "compensating_control"},
                "conditions": [
                    {"operator": "eq", "value": true, "label": "Oui"},
                    {"operator": "eq", "value": false, "label": "Non"}
                ]
            },
            {
                "id": "compensating-ctrl-exposed",
                "type": "input",
                "label": "Controle compensatoire ?",
                "position": {"x": 1050, "y": 500},
                "config": {"field": "compensating_control"},
                "conditions": [
                    {"operator": "eq", "value": true, "label": "Oui"},
                    {"operator": "eq", "value": false, "label": "Non"}
                ]
            },
            {
                "id": "output-not-affected-absent",
                "type": "output",
                "label": "Not Affected (absent)",
                "position": {"x": 1400, "y": 0},
                "config": {"decision": "Not Affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "code_not_present"},
                "conditions": []
            },
            {
                "id": "output-in-triage",
                "type": "output",
                "label": "In Triage",
                "position": {"x": 1400, "y": 120},
                "config": {"decision": "In Triage", "color": "#eab308", "vex_status": "in_triage"},
                "conditions": []
            },
            {
                "id": "output-not-affected-unreachable",
                "type": "output",
                "label": "Not Affected (unreachable)",
                "position": {"x": 1400, "y": 240},
                "config": {"decision": "Not Affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "code_not_reachable"},
                "conditions": []
            },
            {
                "id": "output-not-affected-mitigated",
                "type": "output",
                "label": "Not Affected (mitigated)",
                "position": {"x": 1400, "y": 360},
                "config": {"decision": "Not Affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "protected_by_mitigating_control"},
                "conditions": []
            },
            {
                "id": "output-exploitable-internal",
                "type": "output",
                "label": "Exploitable (internal)",
                "position": {"x": 1400, "y": 480},
                "config": {"decision": "Exploitable", "color": "#f97316", "vex_status": "exploitable"},
                "conditions": []
            },
            {
                "id": "output-not-affected-mitigated-exposed",
                "type": "output",
                "label": "Not Affected (mitigated)",
                "position": {"x": 1400, "y": 600},
                "config": {"decision": "Not Affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "protected_by_mitigating_control"},
                "conditions": []
            },
            {
                "id": "output-exploitable",
                "type": "output",
                "label": "Exploitable",
                "position": {"x": 1400, "y": 720},
                "config": {"decision": "Exploitable", "color": "#dc2626", "vex_status": "exploitable"},
                "conditions": []
            }
        ],
        "edges": [
            {"id": "e-deploy-no", "source": "component-deployed", "target": "output-not-affected-absent", "source_handle": "handle-0"},
            {"id": "e-deploy-yes", "source": "component-deployed", "target": "code-reachable", "source_handle": "handle-1"},

            {"id": "e-reach-unknown", "source": "code-reachable", "target": "output-in-triage", "source_handle": "handle-0"},
            {"id": "e-reach-no", "source": "code-reachable", "target": "output-not-affected-unreachable", "source_handle": "handle-1"},
            {"id": "e-reach-yes", "source": "code-reachable", "target": "network-exposed", "source_handle": "handle-2"},

            {"id": "e-net-no", "source": "network-exposed", "target": "compensating-ctrl-internal", "source_handle": "handle-0"},
            {"id": "e-net-yes", "source": "network-exposed", "target": "compensating-ctrl-exposed", "source_handle": "handle-1"},

            {"id": "e-ctrl-int-yes", "source": "compensating-ctrl-internal", "target": "output-not-affected-mitigated", "source_handle": "handle-0"},
            {"id": "e-ctrl-int-no", "source": "compensating-ctrl-internal", "target": "output-exploitable-internal", "source_handle": "handle-1"},

            {"id": "e-ctrl-exp-yes", "source": "compensating-ctrl-exposed", "target": "output-not-affected-mitigated-exposed", "source_handle": "handle-0"},
            {"id": "e-ctrl-exp-no", "source": "compensating-ctrl-exposed", "target": "output-exploitable", "source_handle": "handle-1"}
        ],
        "metadata": {
            "viewport": {"x": 0, "y": 0, "zoom": 0.7},
            "field_mapping": {
                "fields": [
                    {"name": "cve_id", "type": "string", "description": "Identifiant CVE", "examples": ["CVE-2024-1234"], "required": true},
                    {"name": "component_name", "type": "string", "description": "Nom du composant/librairie affecte", "examples": ["log4j-core", "openssl", "spring-boot"], "required": false},
                    {"name": "component_version", "type": "string", "description": "Version du composant", "examples": ["2.14.1", "3.0.7"], "required": false},
                    {"name": "component_deployed", "type": "boolean", "description": "Le composant est-il deploye dans le produit ?", "examples": [true, false], "required": true},
                    {"name": "code_reachable", "type": "string", "description": "Le code vulnerable est-il atteignable ? (true, false, unknown)", "examples": [true, false, "unknown"], "required": true},
                    {"name": "network_exposed", "type": "boolean", "description": "Le service est-il expose au reseau/internet ?", "examples": [true, false], "required": true},
                    {"name": "compensating_control", "type": "boolean", "description": "Un controle compensatoire est-il en place ? (WAF, isolation, etc.)", "examples": [true, false], "required": true}
                ],
                "source": "default",
                "version": 1
            }
        }
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Exemples de vulnerabilites pour illustrer le triage VEX
-- Ces donnees servent de documentation pour l'arbre VEX Triage
-- Utilisation : POST /api/v1/evaluate/tree/vex-triage avec ces donnees

-- Exemple 1 : Log4Shell dans un composant non deploye → not_affected
-- {"cve_id": "CVE-2021-44228", "component_name": "log4j-core", "component_version": "2.14.1",
--  "component_deployed": false, "code_reachable": true, "network_exposed": true, "compensating_control": false}
-- → Decision: Not Affected (absent) / VEX: not_affected / Justification: code_not_present

-- Exemple 2 : Spring4Shell, code non atteignable → not_affected
-- {"cve_id": "CVE-2022-22965", "component_name": "spring-core", "component_version": "5.3.17",
--  "component_deployed": true, "code_reachable": false, "network_exposed": true, "compensating_control": false}
-- → Decision: Not Affected (unreachable) / VEX: not_affected / Justification: code_not_reachable

-- Exemple 3 : OpenSSL vuln, deploye, atteignable, expose, pas de controle → exploitable
-- {"cve_id": "CVE-2024-5535", "component_name": "openssl", "component_version": "3.0.7",
--  "component_deployed": true, "code_reachable": true, "network_exposed": true, "compensating_control": false}
-- → Decision: Exploitable / VEX: exploitable

-- Exemple 4 : Vuln interne mitigee par WAF → not_affected
-- {"cve_id": "CVE-2024-3094", "component_name": "xz-utils", "component_version": "5.6.1",
--  "component_deployed": true, "code_reachable": true, "network_exposed": true, "compensating_control": true}
-- → Decision: Not Affected (mitigated) / VEX: not_affected / Justification: protected_by_mitigating_control

-- Exemple 5 : Analyse en cours → in_triage
-- {"cve_id": "CVE-2024-9999", "component_name": "internal-lib", "component_version": "1.0.0",
--  "component_deployed": true, "code_reachable": "unknown", "network_exposed": false, "compensating_control": false}
-- → Decision: In Triage / VEX: in_triage

-- Exemple 6 : Vuln interne sans exposition reseau ni controle → exploitable (internal)
-- {"cve_id": "CVE-2024-8888", "component_name": "jackson-databind", "component_version": "2.13.0",
--  "component_deployed": true, "code_reachable": true, "network_exposed": false, "compensating_control": false}
-- → Decision: Exploitable (internal) / VEX: exploitable
