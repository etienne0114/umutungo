import type { Institution } from "./institutions";

export type AssetCondition = "good" | "fair" | "poor" | "critical" | "unknown";
export type AssetCriticality = "standard" | "important" | "mission_critical";
export type RiskLevel = "critical" | "high" | "medium" | "low" | "insufficient_data";
export type Disposition = "accepted" | "deferred" | "rejected";
export type Outcome =
  | "planned_maintenance"
  | "unscheduled_repair"
  | "no_maintenance_found"
  | "other";

export interface Asset {
  id: number;
  institution_id: number | null;
  asset_code: string;
  asset_type: string;
  make: string | null;
  model: string | null;
  registration_number: string | null;
  manufacture_year: number | null;
  criticality: AssetCriticality;
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
  odometer_km: number | null;
  cost_amount: number | null;
  currency: string;
  provider_name: string | null;
  work_order_reference: string | null;
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
  run_name?: string | null;
  status?: string;
  engine_version?: string | null;
  total_institutions?: number;
  total_assets?: number;
  high_risk_assets?: number;
  critical_assets?: number;
  maintenance_candidates?: number;
  replacement_candidates?: number;
}

export type MaintenancePriority = "urgent" | "high" | "medium" | "low" | "monitor";

export interface AssetAssessment {
  asset_id: number;
  institution_id: number | null;
  institution_name: string | null;
  asset_code: string;
  asset_type: string;
  make: string | null;
  model: string | null;
  registration_number: string | null;
  criticality: AssetCriticality;
  condition: AssetCondition;
  asset_age_years: number | null;
  maintenance_count: number;
  maintenance_frequency: number | null;
  days_since_last_maintenance: number | null;
  recent_window_count: number;
  recent_repeat_count: number;
  unplanned_share: number | null;
  total_downtime_hours: number;
  has_maintenance_history: boolean;
  risk_score: number | null;
  risk_level: RiskLevel;
  factor_scores: Record<string, number>;
  priority_score: number;
  maintenance_priority: MaintenancePriority;
  replacement_score: number;
  replacement_candidate: boolean;
  recommendation: string;
  reasons: string[];
  evidence: string[];
}

export interface InstitutionAssessment {
  institution_id: number | null;
  institution_name: string;
  institution_code: string | null;
  total_assets: number;
  high_risk_assets: number;
  critical_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  insufficient_data_assets: number;
  maintenance_candidates: number;
  replacement_candidates: number;
  maintenance_events: number;
  average_age_years: number | null;
  events_per_asset: number | null;
  maintenance_frequency: number | null;
  high_risk_ratio: number;
  critical_ratio: number;
  replacement_ratio: number | null;
  priority_score: number;
  priority_level: MaintenancePriority;
  reasons: string[];
}

export interface TriageSummary {
  total_institutions: number;
  total_assets: number;
  high_risk_assets: number;
  critical_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  insufficient_data_assets: number;
  maintenance_candidates: number;
  replacement_candidates: number;
  maintenance_events: number;
  assets_with_maintenance_history: number;
  data_quality_notes: string[];
}

export interface TriageAnalysis {
  generated_on: string;
  scope_name: string;
  engine_version: string;
  persisted_run_id: number | null;
  summary: TriageSummary;
  institutions: InstitutionAssessment[];
  assets: AssetAssessment[];
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
  institution_id?: number | null;
  asset_code?: string | null;
  risk_score?: number | null;
  factor_scores?: Record<string, number> | null;
  maintenance_priority?: MaintenancePriority | null;
  priority_score?: number | null;
  replacement_score?: number | null;
  replacement_candidate?: boolean;
  maintenance_count?: number;
  maintenance_frequency?: number | null;
  asset_age_years?: number | null;
  days_since_last_maintenance?: number | null;
  recent_window_count?: number;
  recent_repeat_count?: number;
  unplanned_share?: number | null;
  total_downtime_hours?: number;
  has_maintenance_history?: boolean;
  evidence?: string[] | null;
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

export interface OperationsReport {
  generated_on: string;
  scope_institution_id: number | null;
  scope_name: string;
  included_institutions: number;
  total_assets: number;
  active_assets: number;
  inactive_assets: number;
  condition_recorded_assets: number;
  condition_unknown_assets: number;
  missing_acquisition_date: number;
  missing_inspection_date: number;
  missing_service_schedule: number;
  inconsistent_service_dates: number;
  assets_with_maintenance_history: number;
  inspection_records: number;
  maintenance_records: number;
  service_due_assets: number;
  overdue_service_assets: number;
  risk_counts: Record<RiskLevel, number>;
  planned_maintenance_records: number;
  unplanned_maintenance_records: number;
  downtime_hours_recorded: number;
  maintenance_records_without_downtime: number;
  untracked_domains: string[];
}

export interface InstitutionReportRow {
  institution: Institution;
  descendant_count: number;
  report: OperationsReport;
}

export interface InstitutionTreeReport {
  generated_on: string;
  root_count: number;
  unassigned_assets: number;
  rows: InstitutionReportRow[];
}

export interface AssetCreate {
  asset_code: string;
  asset_type: string;
  make?: string | null;
  model?: string | null;
  registration_number?: string | null;
  manufacture_year?: number | null;
  criticality?: AssetCriticality;
  acquisition_date?: string | null;
  last_service_date?: string | null;
  next_service_due?: string | null;
  condition?: AssetCondition;
  active?: boolean;
}

export type AssetUpdate = Partial<AssetCreate>;

export interface MaintenanceCreate {
  event_date: string;
  category: string;
  description?: string | null;
  planned: boolean;
  downtime_hours?: number | null;
  odometer_km?: number | null;
  cost_amount?: number | null;
  currency?: string;
  provider_name?: string | null;
  work_order_reference?: string | null;
}

export interface InspectionCreate {
  inspected_on: string;
  condition: Exclude<AssetCondition, "unknown">;
  observations?: string | null;
}

// Triage run insights types
export interface TriageRunInsights {
  run_id: number;
  evaluated_on: string;
  total_recommendations: number;
  summary: {
    risk_distribution: Record<string, number>;
    condition_distribution: Record<string, number>;
  };
  assets_by_condition: Record<string, string[]>;
}
