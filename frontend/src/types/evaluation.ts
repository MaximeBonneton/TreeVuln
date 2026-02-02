// Entrée vulnérabilité
export interface VulnerabilityInput {
  id?: string;
  cve_id?: string;
  cvss_score?: number;
  cvss_vector?: string;
  epss_score?: number;
  epss_percentile?: number;
  kev?: boolean;
  asset_id?: string;
  asset_criticality?: string;
  hostname?: string;
  ip_address?: string;
  extra?: Record<string, unknown>;
}

// Étape du chemin de décision (audit trail)
export interface DecisionPath {
  node_id: string;
  node_label: string;
  node_type: string;
  field_evaluated: string | null;
  value_found: unknown;
  condition_matched: string | null;
}

// Résultat d'évaluation
export interface EvaluationResult {
  vuln_id: string | null;
  decision: string;
  decision_color: string | null;
  path: DecisionPath[];
  error: string | null;
}

// Requête d'évaluation single
export interface SingleEvaluationRequest {
  vulnerability: VulnerabilityInput;
  include_path?: boolean;
}

// Requête d'évaluation batch
export interface EvaluationRequest {
  vulnerabilities: VulnerabilityInput[];
  include_path?: boolean;
}

// Réponse d'évaluation batch
export interface EvaluationResponse {
  total: number;
  success_count: number;
  error_count: number;
  results: EvaluationResult[];
  decision_summary: Record<string, number>;
}
