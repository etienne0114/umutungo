export type AssetCondition = "good" | "fair" | "poor" | "critical" | "unknown";
export type RiskLevel = "critical" | "high" | "medium" | "low" | "insufficient_data";
export type Disposition = "accepted" | "deferred" | "rejected";
export type Outcome =
  | "planned_maintenance"
  | "unscheduled_repair"
  | "no_maintenance_found"
  | "other";

export interface Asset {
  id: number;
  asset_code: string;
  asset_type: string;
  make: string | null;
  model: string | null;
  acquisition_date: string | null;
  last_inspected_on: string | null;
  last_service_date: string | null;
  next_service_due: string | null;
  condition: AssetCondition;
  active: boolean;
  created_at: string;
}

export interface MaintenanceRecord {
  id: number;
  asset_id: number;
  event_date: string;
  category: string;
  description: string | null;
  planned: boolean;
  downtime_hours: number | null;
  created_at: string;
}

export interface InspectionRecord {
  id: number;
  asset_id: number;
  inspected_on: string;
  condition: Exclude<AssetCondition, "unknown">;
  observations: string | null;
  created_at: string;
}

export interface TriageItem {
  asset: Asset;
  risk_level: RiskLevel;
  reasons: string[];
  recommended_action: string;
  rule_version: string;
  evaluated_on: string;
}

export interface TriageRun {
  id: number;
  evaluated_on: string;
  rule_version: string;
  created_at: string;
  recommendation_count: number;
}

export interface Recommendation {
  id: number;
  run_id: number;
  asset_id: number;
  risk_level: RiskLevel;
  reasons: string[];
  recommended_action: string;
  rule_version: string;
  evaluated_on: string;
  asset_snapshot: Asset;
  created_at: string;
}

export interface RecommendationEvent {
  id: number;
  recommendation_id: number;
  event_type: "review" | "outcome";
  disposition: Disposition | null;
  outcome: Outcome | null;
  occurred_on: string | null;
  reason: string | null;
  created_at: string;
}

export interface AdminUser {
  id: string;
  email: string | null;
  created_at: string;
  email_confirmed_at: string | null;
  last_sign_in_at: string | null;
  access: "pending" | "approved";
  role: "admin" | "user";
  full_name: string | null;
  organization: string | null;
}

export interface AssetCreate {
  asset_code: string;
  asset_type: string;
  make?: string | null;
  model?: string | null;
  acquisition_date?: string | null;
  last_service_date?: string | null;
  next_service_due?: string | null;
  condition?: AssetCondition;
  active?: boolean;
}

export interface MaintenanceCreate {
  event_date: string;
  category: string;
  description?: string | null;
  planned: boolean;
  downtime_hours?: number | null;
}

export interface InspectionCreate {
  inspected_on: string;
  condition: Exclude<AssetCondition, "unknown">;
  observations?: string | null;
}
