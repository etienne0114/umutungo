export type InstitutionType =
  | "ministry"
  | "agency"
  | "authority"
  | "commission"
  | "public_institution"
  | "other_government_entity"
  | "province"
  | "city"
  | "district";

export type InstitutionRole =
  | "institution_admin"
  | "fleet_manager"
  | "maintenance_officer"
  | "technician"
  | "driver"
  | "auditor"
  | "viewer";

export interface Institution {
  id: number;
  name: string;
  code: string;
  short_name: string | null;
  institution_type: InstitutionType;
  active: boolean;
  is_official: boolean;
  description: string | null;
  source_url: string | null;
  source_verified_on: string | null;
  parent_institution_id: number | null;
  membership_role: InstitutionRole | null;
}

export interface InstitutionCreate {
  name: string;
  code: string;
  short_name?: string | null;
  description?: string | null;
  institution_type: InstitutionType;
  active: boolean;
  parent_institution_id: number | null;
}

export interface InstitutionUpdate {
  name?: string;
  code?: string;
  short_name?: string | null;
  description?: string | null;
  institution_type?: InstitutionType;
  active?: boolean;
  parent_institution_id?: number | null;
}

export interface InstitutionMembership {
  user_id: string;
  institution_id: number;
  role: InstitutionRole;
}

export interface InstitutionMembershipCreate {
  user_id: string;
  institution_id: number;
  role: InstitutionRole;
}

export interface CatalogSyncResult {
  created: number;
  updated: number;
  unchanged: number;
  total: number;
  verified_on: string;
  source_urls: string[];
}
