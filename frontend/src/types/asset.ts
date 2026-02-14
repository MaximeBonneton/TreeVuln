// Asset
export interface Asset {
  id: number;
  asset_id: string;
  name: string | null;
  criticality: string;
  tags: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AssetCreate {
  asset_id: string;
  name?: string;
  criticality?: string;
  tags?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AssetUpdate {
  name?: string;
  criticality?: string;
  tags?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AssetImportError {
  row: number;
  asset_id: string | null;
  error: string;
}

export interface AssetImportResult {
  total_rows: number;
  created: number;
  updated: number;
  errors: number;
  error_details: AssetImportError[];
}

export interface AssetImportPreview {
  columns: string[];
  row_count: number;
  preview: Record<string, unknown>[];
}
