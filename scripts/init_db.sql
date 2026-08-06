-- Database initialization script for TreeVuln
-- This script creates tables and inserts test data for development

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'operator')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    must_change_pwd BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Server sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Encryption key (singleton)
CREATE TABLE IF NOT EXISTS encryption_keys (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    key_value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trees table
CREATE TABLE IF NOT EXISTS trees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'Main Tree',
    description VARCHAR(1000),
    structure JSONB NOT NULL DEFAULT '{}',
    -- Multi-tree: default and API management
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    api_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    api_slug VARCHAR(100) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for default tree (only one allowed)
CREATE UNIQUE INDEX IF NOT EXISTS idx_trees_default ON trees(is_default) WHERE is_default = TRUE;
-- Index for API slug lookup
CREATE INDEX IF NOT EXISTS idx_trees_api_slug ON trees(api_slug) WHERE api_slug IS NOT NULL;

-- Create tree_versions table
CREATE TABLE IF NOT EXISTS tree_versions (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    structure_snapshot JSONB NOT NULL,
    comment VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tree_versions_tree_id ON tree_versions(tree_id);
-- Unicité du numéro de version au sein d'un arbre (cf. migration 0003)
CREATE UNIQUE INDEX IF NOT EXISTS uq_tree_versions_tree_version ON tree_versions(tree_id, version_number);

-- Create assets table
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    -- Multi-tree: FK to the owning tree
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    asset_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    criticality VARCHAR(50) NOT NULL DEFAULT 'Medium',
    tags JSONB NOT NULL DEFAULT '{}',
    extra_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Unique constraint on (tree_id, asset_id) instead of asset_id alone
    CONSTRAINT assets_tree_asset_unique UNIQUE (tree_id, asset_id)
);

-- Pas d'index séparé sur (tree_id, asset_id) : l'index unique de la
-- contrainte assets_tree_asset_unique sert déjà ces recherches.

-- Create webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    -- TEXT : valeur chiffrée "enc:..." dont la longueur dépasse 255 pour un
    -- secret plaintext un peu long (cf. fix C-10 + revue 2026-07-16 #1)
    secret TEXT,
    headers JSONB NOT NULL DEFAULT '{}',
    events TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index composite (tree_id, is_active) ; son préfixe gauche couvre déjà les
-- recherches par tree_id seul, donc pas d'index séparé idx_webhooks_tree_id.
CREATE INDEX IF NOT EXISTS idx_webhooks_tree_active ON webhooks(tree_id, is_active);

-- Create webhook_logs table
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

-- Create ingest_endpoints table
CREATE TABLE IF NOT EXISTS ingest_endpoints (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES trees(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    -- TEXT : clé API chiffrée "enc:...", même contrainte que webhooks.secret
    api_key TEXT NOT NULL,
    field_mapping JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    auto_evaluate BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_endpoints_slug ON ingest_endpoints(slug);
CREATE INDEX IF NOT EXISTS idx_ingest_endpoints_tree_id ON ingest_endpoints(tree_id);

-- Create ingest_logs table
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

-- Insert optimized SSVC decision tree with multi-input (default tree)
-- Criteria: Exploitation (KEV), Automatable (EPSS >= 0.2), Technical Impact (CVSS >= 9), Mission & Well-being (asset_criticality)
-- Optimized structure: 8 nodes instead of 26 thanks to multi-input
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'SSVC Example',
    'Optimized SSVC tree - Vulnerability prioritization with multi-input',
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
                    {"name": "cve_id", "label": "CVE ID", "type": "string", "description": "CVE identifier of the vulnerability", "examples": ["CVE-2024-1234", "CVE-2023-5678"], "required": false},
                    {"name": "kev", "label": "KEV Status", "type": "boolean", "description": "Presence in the CISA KEV list (true = active exploit, false = PoC, null = no info)", "examples": [true, false, null], "required": false},
                    {"name": "epss_score", "label": "EPSS Score", "type": "number", "description": "EPSS score (0-1). >= 0.2 = automatable", "examples": [0.95, 0.12, 0.003], "required": true},
                    {"name": "cvss_score", "label": "CVSS Score", "type": "number", "description": "CVSS score (0-10). >= 9 = total impact", "examples": [9.8, 7.5, 4.2], "required": true},
                    {"name": "cvss_vector", "label": "CVSS Vector", "type": "string", "description": "Full CVSS vector (3.1 or 4.0). Allows extracting individual metrics", "examples": ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"], "required": false},
                    {"name": "asset_criticality", "label": "Asset Criticality", "type": "string", "description": "Asset criticality level (Low, Medium, High, Critical)", "examples": ["Low", "Medium", "High", "Critical"], "required": true}
                ],
                "source": "default",
                "version": 3
            }
        }
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Insert test assets (linked to the default tree)
-- Uses a subquery to retrieve the default tree ID
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

-- Insert Equation Example tree (non-default)
-- Demonstrates: Equation node with formula, value mapping, compound conditions, CVSS vector parsing
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'Equation Example',
    'Example tree using Equation nodes with formula-based risk scoring',
    FALSE,
    FALSE,
    NULL,
    '{
        "nodes": [
            {
                "id": "input-kev",
                "type": "input",
                "label": "Input",
                "position": {"x": 180, "y": 105},
                "config": {"field": "kev"},
                "conditions": [
                    {"label": "No", "operator": "eq", "value": false},
                    {"label": "Yes", "operator": "eq", "value": true}
                ]
            },
            {
                "id": "input-cvss-av",
                "type": "input",
                "label": "Input",
                "position": {"x": 465, "y": 195},
                "config": {"field": "cvss_av"},
                "conditions": [
                    {"label": "Risque Local", "operator": "neq", "value": "Network"},
                    {"label": "Risque Externe", "operator": "eq", "value": "Network"}
                ]
            },
            {
                "id": "equation-risk",
                "type": "equation",
                "label": "Equation",
                "position": {"x": 730, "y": 300},
                "config": {
                    "formula": "cvss_score * asset_criticality * epss_score",
                    "variables": ["cvss_score", "asset_criticality", "epss_score"],
                    "value_maps": {
                        "asset_criticality": {
                            "entries": [
                                {"text": "Critical", "value": 10},
                                {"text": "High", "value": 8},
                                {"text": "Medium", "value": 5},
                                {"text": "Low", "value": 2}
                            ],
                            "default_value": 10
                        }
                    },
                    "output_label": "Score"
                },
                "conditions": [
                    {"label": "Low", "operator": "lt", "value": 30},
                    {"label": "Important", "logic": "AND", "criteria": [
                        {"field": null, "operator": "gte", "value": 30},
                        {"field": null, "operator": "lt", "value": 50}
                    ]},
                    {"label": "Major", "logic": "AND", "criteria": [
                        {"field": null, "operator": "gte", "value": 50},
                        {"field": null, "operator": "lt", "value": 70}
                    ]},
                    {"label": "Critical", "operator": "gte", "value": 70}
                ]
            },
            {
                "id": "output-low",
                "type": "output",
                "label": "Risque",
                "position": {"x": 1070, "y": 50},
                "config": {"decision": "Low", "color": "#22c55e"},
                "conditions": []
            },
            {
                "id": "output-important",
                "type": "output",
                "label": "Risque",
                "position": {"x": 1065, "y": 225},
                "config": {"decision": "Important", "color": "#eab308"},
                "conditions": []
            },
            {
                "id": "output-major",
                "type": "output",
                "label": "Risque",
                "position": {"x": 1070, "y": 380},
                "config": {"decision": "Major", "color": "#f97316"},
                "conditions": []
            },
            {
                "id": "output-act",
                "type": "output",
                "label": "Risque",
                "position": {"x": 1065, "y": 525},
                "config": {"decision": "Act", "color": "#dc2626"},
                "conditions": []
            }
        ],
        "edges": [
            {"id": "e-kev-no", "source": "input-kev", "target": "output-low", "source_handle": "handle-0"},
            {"id": "e-kev-yes", "source": "input-kev", "target": "input-cvss-av", "source_handle": "handle-1"},
            {"id": "e-av-local", "source": "input-cvss-av", "target": "output-low", "source_handle": "handle-0"},
            {"id": "e-av-network", "source": "input-cvss-av", "target": "equation-risk", "source_handle": "handle-1"},
            {"id": "e-eq-low", "source": "equation-risk", "target": "output-low", "source_handle": "handle-0"},
            {"id": "e-eq-important", "source": "equation-risk", "target": "output-important", "source_handle": "handle-1"},
            {"id": "e-eq-major", "source": "equation-risk", "target": "output-major", "source_handle": "handle-2"},
            {"id": "e-eq-critical", "source": "equation-risk", "target": "output-act", "source_handle": "handle-3"}
        ],
        "metadata": {
            "field_mapping": {
                "fields": [
                    {"name": "cve_id", "type": "string", "label": "CVE ID", "examples": ["CVE-2024-21762", "CVE-2024-3400"], "required": true},
                    {"name": "cvss_score", "type": "number", "label": "CVSS Score", "examples": [9.8, 7.5, 4.2], "required": true},
                    {"name": "cvss_vector", "type": "string", "label": "CVSS Vector", "examples": ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"], "required": false, "description": "Full CVSS vector for metric extraction"},
                    {"name": "epss_score", "type": "number", "label": "EPSS Score", "examples": [0.97, 0.12, 0.003], "required": true},
                    {"name": "kev", "type": "boolean", "label": "KEV Status", "examples": [true, false], "required": true},
                    {"name": "asset_criticality", "type": "string", "label": "Asset Criticality", "examples": ["Critical", "High", "Medium", "Low"], "required": true},
                    {"name": "cvss_av", "type": "string", "label": "CVSS Attack Vector", "examples": ["Network", "Local", "Adjacent"], "required": false, "description": "Derived from cvss_vector. Values: Network, Adjacent, Local, Physical"},
                    {"name": "cvss_ac", "type": "string", "label": "CVSS Attack Complexity", "examples": ["Low", "High"], "required": false, "description": "Derived from cvss_vector. Values: Low, High"},
                    {"name": "cvss_pr", "type": "string", "label": "CVSS Privileges Required", "examples": ["None", "Low", "High"], "required": false, "description": "Derived from cvss_vector. Values: None, Low, High"},
                    {"name": "cvss_ui", "type": "string", "label": "CVSS User Interaction", "examples": ["None", "Required"], "required": false, "description": "Derived from cvss_vector. Values: None, Required"},
                    {"name": "cvss_s", "type": "string", "label": "CVSS Scope", "examples": ["Unchanged", "Changed"], "required": false, "description": "Derived from cvss_vector. Values: Unchanged, Changed"},
                    {"name": "cvss_c", "type": "string", "label": "CVSS Confidentiality Impact", "examples": ["High", "None", "Low"], "required": false, "description": "Derived from cvss_vector. Values: None, Low, High"},
                    {"name": "cvss_i", "type": "string", "label": "CVSS Integrity Impact", "examples": ["High", "None", "Low"], "required": false, "description": "Derived from cvss_vector. Values: None, Low, High"},
                    {"name": "cvss_a", "type": "string", "label": "CVSS Availability Impact", "examples": ["High", "None"], "required": false, "description": "Derived from cvss_vector. Values: None, Low, High"}
                ],
                "source": "default",
                "version": 1
            }
        }
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Insert CSAF VEX Example tree (non-default)
-- Demonstrates: VEX triage workflow for CSAF 2.0 export - all 4 VEX statuses on output nodes,
-- mandatory justification when not_affected (two different justifications), is_null for pending analysis
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'CSAF VEX Example',
    'VEX triage tree for CSAF 2.0 export - component presence, fix status and code reachability drive the VEX status',
    FALSE,
    FALSE,
    NULL,
    '{
        "nodes": [
            {
                "id": "component-present",
                "type": "input",
                "label": "Component present?",
                "position": {"x": -465, "y": 300},
                "config": {"field": "component_present"},
                "conditions": [
                    {"operator": "eq", "value": false, "label": "No"},
                    {"operator": "eq", "value": true, "label": "Yes"}
                ]
            },
            {
                "id": "fix-deployed",
                "type": "input",
                "label": "Fix deployed?",
                "position": {"x": -120, "y": 390},
                "config": {"field": "fix_deployed"},
                "conditions": [
                    {"operator": "eq", "value": true, "label": "Yes"},
                    {"operator": "eq", "value": false, "label": "No"}
                ]
            },
            {
                "id": "code-reachable",
                "type": "input",
                "label": "Vulnerable code reachable?",
                "position": {"x": 225, "y": 480},
                "config": {"field": "code_reachable"},
                "conditions": [
                    {"operator": "eq", "value": true, "label": "Yes"},
                    {"operator": "eq", "value": false, "label": "No"},
                    {"operator": "is_null", "value": null, "label": "Unknown"}
                ]
            },
            {
                "id": "output-not-affected-absent",
                "type": "output",
                "label": "Not affected (absent)",
                "position": {"x": 660, "y": 120},
                "config": {"decision": "Not affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "component_not_present"},
                "conditions": []
            },
            {
                "id": "output-fixed",
                "type": "output",
                "label": "Fixed",
                "position": {"x": 660, "y": 300},
                "config": {"decision": "Fixed", "color": "#6366f1", "vex_status": "fixed"},
                "conditions": []
            },
            {
                "id": "output-affected",
                "type": "output",
                "label": "Affected",
                "position": {"x": 660, "y": 450},
                "config": {"decision": "Affected", "color": "#dc2626", "vex_status": "affected"},
                "conditions": []
            },
            {
                "id": "output-not-affected-unreachable",
                "type": "output",
                "label": "Not affected (unreachable)",
                "position": {"x": 660, "y": 600},
                "config": {"decision": "Not affected", "color": "#22c55e", "vex_status": "not_affected", "vex_justification": "vulnerable_code_not_in_execute_path"},
                "conditions": []
            },
            {
                "id": "output-under-investigation",
                "type": "output",
                "label": "Under investigation",
                "position": {"x": 660, "y": 750},
                "config": {"decision": "Under investigation", "color": "#eab308", "vex_status": "under_investigation"},
                "conditions": []
            }
        ],
        "edges": [
            {"id": "e-comp-no", "source": "component-present", "target": "output-not-affected-absent", "source_handle": "handle-0"},
            {"id": "e-comp-yes", "source": "component-present", "target": "fix-deployed", "source_handle": "handle-1", "target_handle": "input-0"},
            {"id": "e-fix-yes", "source": "fix-deployed", "target": "output-fixed", "source_handle": "handle-0"},
            {"id": "e-fix-no", "source": "fix-deployed", "target": "code-reachable", "source_handle": "handle-1", "target_handle": "input-0"},
            {"id": "e-reach-yes", "source": "code-reachable", "target": "output-affected", "source_handle": "handle-0"},
            {"id": "e-reach-no", "source": "code-reachable", "target": "output-not-affected-unreachable", "source_handle": "handle-1"},
            {"id": "e-reach-unknown", "source": "code-reachable", "target": "output-under-investigation", "source_handle": "handle-2"}
        ],
        "metadata": {
            "viewport": {"x": 0, "y": 0, "zoom": 0.8},
            "field_mapping": {
                "fields": [
                    {"name": "cve_id", "label": "CVE ID", "type": "string", "description": "CVE identifier - required by the CSAF export (rows without a valid CVE are excluded)", "examples": ["CVE-2024-1234", "CVE-2023-5678"], "required": true},
                    {"name": "asset_id", "label": "Asset ID", "type": "string", "description": "Product identifier - required by the CSAF export to build the product tree", "examples": ["srv-prod-001", "ws-admin-001"], "required": true},
                    {"name": "component_present", "label": "Component Present", "type": "boolean", "description": "Is the vulnerable component present in the product? false = not_affected (component_not_present)", "examples": [true, false], "required": true},
                    {"name": "fix_deployed", "label": "Fix Deployed", "type": "boolean", "description": "Has the fix been deployed? true = fixed", "examples": [true, false], "required": true},
                    {"name": "code_reachable", "label": "Code Reachable", "type": "boolean", "description": "Is the vulnerable code reachable? true = affected, false = not_affected (not in execute path), null = under_investigation", "examples": [true, false, null], "required": false}
                ],
                "source": "default",
                "version": 1
            }
        }
    }'::jsonb
) ON CONFLICT DO NOTHING;
