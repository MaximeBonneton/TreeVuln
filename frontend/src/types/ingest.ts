export interface IngestEndpoint {
  id: number;
  tree_id: number;
  name: string;
  slug: string;
  api_key: string;
  field_mapping: Record<string, string>;
  is_active: boolean;
  auto_evaluate: boolean;
  created_at: string;
  updated_at: string;
}

export interface IngestEndpointCreate {
  name: string;
  slug: string;
  field_mapping?: Record<string, string>;
  is_active?: boolean;
  auto_evaluate?: boolean;
}

export interface IngestEndpointUpdate {
  name?: string;
  slug?: string;
  field_mapping?: Record<string, string>;
  is_active?: boolean;
  auto_evaluate?: boolean;
}

export interface IngestLog {
  id: number;
  endpoint_id: number;
  source_ip: string | null;
  payload_size: number | null;
  vuln_count: number;
  success_count: number;
  error_count: number;
  duration_ms: number | null;
  created_at: string;
}
