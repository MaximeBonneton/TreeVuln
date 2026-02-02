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

-- Insertion d'un arbre de décision SSVC (arbre par défaut)
-- Critères : Exploitation (KEV), Automatable (EPSS >= 0.2), Technical Impact (CVSS >= 9), Mission & Well-being (asset_criticality)
INSERT INTO trees (name, description, is_default, api_enabled, api_slug, structure) VALUES (
    'Default Tree',
    'Arbre SSVC - Priorisation des vulnerabilites',
    TRUE,  -- is_default
    FALSE,  -- api_enabled (désactivé par défaut)
    NULL,  -- api_slug
    '{
        "nodes": [
            {"id": "exploitation", "type": "input", "label": "Exploitation", "position": {"x": -705, "y": 225}, "config": {"field": "kev"}, "conditions": [{"operator": "is_null", "value": "none", "label": "None"}, {"operator": "eq", "value": false, "label": "PoC"}, {"operator": "eq", "value": true, "label": "Active"}]},
            {"id": "automatable", "type": "input", "label": "Automatable", "position": {"x": -360, "y": 45}, "config": {"field": "epss_score"}, "conditions": [{"operator": "lt", "value": 0.2, "label": "No"}, {"operator": "gte", "value": 0.2, "label": "Yes"}]},
            {"id": "tech-impact-no", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": -165}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "output-act", "type": "output", "label": "Act", "position": {"x": 765, "y": 570}, "config": {"color": "#dc2626", "decision": "Act"}, "conditions": []},
            {"id": "output-attend", "type": "output", "label": "Attend", "position": {"x": 765, "y": 30}, "config": {"color": "#f97316", "decision": "Attend"}, "conditions": []},
            {"id": "output-track-star", "type": "output", "label": "Track*", "position": {"x": 765, "y": -150}, "config": {"color": "#eab308", "decision": "Track*"}, "conditions": []},
            {"id": "output-track", "type": "output", "label": "Track", "position": {"x": 765, "y": -60}, "config": {"color": "#22c55e", "decision": "Track"}, "conditions": []},
            {"id": "mission-1", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": -120}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "automatable-poc", "type": "input", "label": "Automatable", "position": {"x": -360, "y": 375}, "config": {"field": "epss_score"}, "conditions": [{"operator": "lt", "value": 0.2, "label": "No"}, {"operator": "gte", "value": 0.2, "label": "Yes"}]},
            {"id": "automatable-active", "type": "input", "label": "Automatable", "position": {"x": -360, "y": 225}, "config": {"field": "epss_score"}, "conditions": [{"operator": "lt", "value": 0.2, "label": "No"}, {"operator": "gte", "value": 0.2, "label": "Yes"}]},
            {"id": "tech-impact-yes", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": 45}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "tech-impact-active-no", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": 180}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "tech-impact-active-yes", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": 345}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "tech-impact-poc-no", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": 510}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "tech-impact-poc-yes", "type": "input", "label": "Technical Impact", "position": {"x": -15, "y": 675}, "config": {"field": "cvss_score"}, "conditions": [{"operator": "lt", "value": 9, "label": "Partial"}, {"operator": "gte", "value": 9, "label": "Total"}]},
            {"id": "output-track-2", "type": "output", "label": "Track", "position": {"x": 765, "y": -240}, "config": {"color": "#22c55e", "decision": "Track"}, "conditions": []},
            {"id": "mission-2", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": -30}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-3", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 330}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-4", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 420}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-5", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 60}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-6", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 150}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-7", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 240}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "output-track-3", "type": "output", "label": "Track", "position": {"x": 765, "y": 390}, "config": {"color": "#22c55e", "decision": "Track"}, "conditions": []},
            {"id": "output-track-4", "type": "output", "label": "Track", "position": {"x": 765, "y": 120}, "config": {"color": "#22c55e", "decision": "Track"}, "conditions": []},
            {"id": "mission-8", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 510}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-9", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 705}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-10", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 795}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "mission-11", "type": "input", "label": "Mission & Well-being", "position": {"x": 375, "y": 600}, "config": {"field": "asset_criticality"}, "conditions": [{"operator": "eq", "value": "Low", "label": "Low"}, {"operator": "eq", "value": "Medium", "label": "Medium"}, {"operator": "in", "value": ["High", "Critical"], "label": "High"}]},
            {"id": "output-track-star-2", "type": "output", "label": "Track*", "position": {"x": 765, "y": 210}, "config": {"color": "#eab308", "decision": "Track*"}, "conditions": []},
            {"id": "output-attend-2", "type": "output", "label": "Attend", "position": {"x": 765, "y": 300}, "config": {"color": "#f97316", "decision": "Attend"}, "conditions": []},
            {"id": "output-attend-3", "type": "output", "label": "Attend", "position": {"x": 765, "y": 480}, "config": {"color": "#f97316", "decision": "Attend"}, "conditions": []},
            {"id": "output-act-2", "type": "output", "label": "Act", "position": {"x": 765, "y": 795}, "config": {"color": "#dc2626", "decision": "Act"}, "conditions": []},
            {"id": "output-attend-4", "type": "output", "label": "Attend", "position": {"x": 765, "y": 675}, "config": {"color": "#f97316", "decision": "Attend"}, "conditions": []}
        ],
        "edges": [
            {"id": "e-exploit-active", "source": "exploitation", "target": "automatable-poc", "source_handle": "handle-2"},
            {"id": "e-exploit-poc", "source": "exploitation", "target": "automatable-active", "source_handle": "handle-1"},
            {"id": "e-exploit-none", "source": "exploitation", "target": "automatable", "source_handle": "handle-0"},
            {"id": "e-auto-no", "source": "automatable", "target": "tech-impact-no", "source_handle": "handle-0"},
            {"id": "e-auto-yes", "source": "automatable", "target": "tech-impact-yes", "source_handle": "handle-1"},
            {"id": "e-active-no", "source": "automatable-active", "target": "tech-impact-active-no", "source_handle": "handle-0"},
            {"id": "e-active-yes", "source": "automatable-active", "target": "tech-impact-active-yes", "source_handle": "handle-1"},
            {"id": "e-poc-no", "source": "automatable-poc", "target": "tech-impact-poc-no", "source_handle": "handle-0"},
            {"id": "e-poc-yes", "source": "automatable-poc", "target": "tech-impact-poc-yes", "source_handle": "handle-1"},
            {"id": "e-tech-no-partial", "source": "tech-impact-no", "target": "output-track-2", "source_handle": "handle-0"},
            {"id": "e-tech-no-total", "source": "tech-impact-no", "target": "mission-1", "source_handle": "handle-1"},
            {"id": "e-m1-low", "source": "mission-1", "target": "output-track-2", "source_handle": "handle-0"},
            {"id": "e-m1-med", "source": "mission-1", "target": "output-track-2", "source_handle": "handle-1"},
            {"id": "e-m1-high", "source": "mission-1", "target": "output-track-star", "source_handle": "handle-2"},
            {"id": "e-tech-yes-partial", "source": "tech-impact-yes", "target": "mission-2", "source_handle": "handle-0"},
            {"id": "e-tech-yes-total", "source": "tech-impact-yes", "target": "mission-5", "source_handle": "handle-1"},
            {"id": "e-m2-low", "source": "mission-2", "target": "output-track", "source_handle": "handle-0"},
            {"id": "e-m2-med", "source": "mission-2", "target": "output-track", "source_handle": "handle-1"},
            {"id": "e-m2-high", "source": "mission-2", "target": "output-attend", "source_handle": "handle-2"},
            {"id": "e-m5-low", "source": "mission-5", "target": "output-track", "source_handle": "handle-0"},
            {"id": "e-m5-med", "source": "mission-5", "target": "output-track", "source_handle": "handle-1"},
            {"id": "e-m5-high", "source": "mission-5", "target": "output-attend", "source_handle": "handle-2"},
            {"id": "e-tech-active-no-partial", "source": "tech-impact-active-no", "target": "mission-6", "source_handle": "handle-0"},
            {"id": "e-tech-active-no-total", "source": "tech-impact-active-no", "target": "mission-7", "source_handle": "handle-1"},
            {"id": "e-tech-active-yes-partial", "source": "tech-impact-active-yes", "target": "mission-3", "source_handle": "handle-0"},
            {"id": "e-tech-active-yes-total", "source": "tech-impact-active-yes", "target": "mission-4", "source_handle": "handle-1"},
            {"id": "e-tech-poc-no-partial", "source": "tech-impact-poc-no", "target": "mission-8", "source_handle": "handle-0"},
            {"id": "e-tech-poc-no-total", "source": "tech-impact-poc-no", "target": "mission-11", "source_handle": "handle-1"},
            {"id": "e-tech-poc-yes-partial", "source": "tech-impact-poc-yes", "target": "mission-9", "source_handle": "handle-0"},
            {"id": "e-tech-poc-yes-total", "source": "tech-impact-poc-yes", "target": "mission-10", "source_handle": "handle-1"},
            {"id": "e-m6-low", "source": "mission-6", "target": "output-track-4", "source_handle": "handle-0"},
            {"id": "e-m6-med", "source": "mission-6", "target": "output-track-4", "source_handle": "handle-1"},
            {"id": "e-m6-high", "source": "mission-6", "target": "output-track-star-2", "source_handle": "handle-2"},
            {"id": "e-m7-low", "source": "mission-7", "target": "output-track-4", "source_handle": "handle-0"},
            {"id": "e-m7-med", "source": "mission-7", "target": "output-track-star-2", "source_handle": "handle-1"},
            {"id": "e-m7-high", "source": "mission-7", "target": "output-attend-2", "source_handle": "handle-2"},
            {"id": "e-m3-low", "source": "mission-3", "target": "output-track-3", "source_handle": "handle-0"},
            {"id": "e-m3-med", "source": "mission-3", "target": "output-track-3", "source_handle": "handle-1"},
            {"id": "e-m3-high", "source": "mission-3", "target": "output-attend-3", "source_handle": "handle-2"},
            {"id": "e-m4-low", "source": "mission-4", "target": "output-track-3", "source_handle": "handle-0"},
            {"id": "e-m4-med", "source": "mission-4", "target": "output-track-3", "source_handle": "handle-1"},
            {"id": "e-m4-high", "source": "mission-4", "target": "output-attend-3", "source_handle": "handle-2"},
            {"id": "e-m8-low", "source": "mission-8", "target": "output-track-3", "source_handle": "handle-0"},
            {"id": "e-m8-med", "source": "mission-8", "target": "output-track-3", "source_handle": "handle-1"},
            {"id": "e-m8-high", "source": "mission-8", "target": "output-attend-3", "source_handle": "handle-2"},
            {"id": "e-m11-low", "source": "mission-11", "target": "output-track-3", "source_handle": "handle-0"},
            {"id": "e-m11-med", "source": "mission-11", "target": "output-attend-3", "source_handle": "handle-1"},
            {"id": "e-m11-high", "source": "mission-11", "target": "output-act", "source_handle": "handle-2"},
            {"id": "e-m9-low", "source": "mission-9", "target": "output-attend-4", "source_handle": "handle-0"},
            {"id": "e-m9-med", "source": "mission-9", "target": "output-attend-4", "source_handle": "handle-1"},
            {"id": "e-m9-high", "source": "mission-9", "target": "output-act-2", "source_handle": "handle-2"},
            {"id": "e-m10-low", "source": "mission-10", "target": "output-attend-4", "source_handle": "handle-0"},
            {"id": "e-m10-med", "source": "mission-10", "target": "output-act-2", "source_handle": "handle-1"},
            {"id": "e-m10-high", "source": "mission-10", "target": "output-act-2", "source_handle": "handle-2"}
        ],
        "metadata": {
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "field_mapping": {
                "fields": [
                    {
                        "name": "cve_id",
                        "label": "CVE ID",
                        "type": "string",
                        "description": "Identifiant CVE de la vulnerabilite",
                        "examples": ["CVE-2024-1234", "CVE-2023-5678"],
                        "required": false
                    },
                    {
                        "name": "kev",
                        "label": "KEV Status",
                        "type": "boolean",
                        "description": "Presence dans la liste KEV de CISA (true = exploit actif)",
                        "examples": [true, false],
                        "required": true
                    },
                    {
                        "name": "epss_score",
                        "label": "Score EPSS",
                        "type": "number",
                        "description": "Score EPSS (0-1). >= 0.2 = automatisable",
                        "examples": [0.95, 0.12, 0.003],
                        "required": true
                    },
                    {
                        "name": "cvss_score",
                        "label": "Score CVSS",
                        "type": "number",
                        "description": "Score CVSS (0-10). >= 9 = impact total",
                        "examples": [9.8, 7.5, 4.2],
                        "required": true
                    },
                    {
                        "name": "asset_criticality",
                        "label": "Asset Criticality",
                        "type": "string",
                        "description": "Criticite de l asset (Low, Medium, High, Critical)",
                        "examples": ["Low", "Medium", "High", "Critical"],
                        "required": true
                    }
                ],
                "source": "default",
                "version": 2
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
