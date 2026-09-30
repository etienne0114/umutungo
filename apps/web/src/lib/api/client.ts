import type {
  Asset,
  AssetCreate,
  AssetUpdate,
  AdminUser,
  Disposition,
  InspectionCreate,
  InspectionRecord,
  InstitutionTreeReport,
  MaintenanceCreate,
  MaintenanceRecord,
  Outcome,
  OperationsReport,
  Recommendation,
  RecommendationEvent,
  RiskLevel,
  TriageItem,
  TriageRun,
} from "./types";
import type {
  CatalogSyncResult,
  Institution,
  InstitutionCreate,
  InstitutionMembership,
  InstitutionMembershipCreate,
  InstitutionUpdate,
} from "./institutions";
import { getSupabaseBrowserClient, supabaseIsConfigured } from "@/lib/supabase/client";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

let activeInstitutionId: number | null = null;

export function setActiveInstitutionId(institutionId: number | null) {
  activeInstitutionId = institutionId;
}

function scopedPath(path: string) {
  if (
    activeInstitutionId === null ||
    !path.startsWith("/api/v1/") ||
    path.startsWith("/api/v1/admin/") ||
    path === "/api/v1/institutions"
  ) {
    return path;
  }

  const [pathname, query = ""] = path.split("?", 2);
  const params = new URLSearchParams(query);
  if (!params.has("institution_id")) {
    params.set("institution_id", String(activeInstitutionId));
  }
  return `${pathname}?${params.toString()}`;
}

async function authorizationHeaders(): Promise<Record<string, string>> {
  if (!supabaseIsConfigured()) return {};
  const { data, error } = await getSupabaseBrowserClient().auth.getSession();
  if (error) throw error;
  if (!data.session) throw new Error("Your session has expired. Sign in again.");
  return { Authorization: `Bearer ${data.session.access_token}` };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await authorizationHeaders();
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${scopedPath(path)}`, {
      ...init,
      headers: {
        ...authHeaders,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    const isLocalApi =
      API_BASE_URL.startsWith("http://localhost") ||
      API_BASE_URL.startsWith("http://127.0.0.1");
    throw new Error(
      isLocalApi
        ? `Could not reach the local API at ${API_BASE_URL}. Start both services with "npm run dev" from apps/web, then confirm ${API_BASE_URL}/health returns status ok.`
        : `Could not complete the API request at ${API_BASE_URL}. Check the API address, network connection, and that this frontend origin is allowed by the API's CORS_ORIGINS.`,
    );
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : null;
    if (typeof detail === "string") throw new Error(detail);
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((issue) => {
        if (typeof issue !== "object" || issue === null || !("msg" in issue)) return [];
        return typeof issue.msg === "string" ? [issue.msg] : [];
      });
      if (messages.length) throw new Error(messages.join(" "));
    }
    throw new Error(`Request failed (${response.status}).`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function checkApiHealth(): Promise<boolean> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE_URL}.`);
  }
  if (!response.ok) throw new Error(`The API health check failed (${response.status}).`);
  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("status" in payload) ||
    payload.status !== "ok"
  ) {
    throw new Error("The API returned an unexpected health response.");
  }
  return true;
}

async function downloadCsv(dataset: "assets" | "maintenance" | "inspections") {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${scopedPath(`/api/v1/exports/${dataset}.csv`)}`, {
      headers: await authorizationHeaders(),
      cache: "no-store",
    });
  } catch {
    throw new Error(
      `Could not complete the API request at ${API_BASE_URL}. Check the API address, network connection, and that this frontend origin is allowed by the API's CORS_ORIGINS.`,
    );
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? payload.detail
        : null;
    throw new Error(typeof detail === "string" ? detail : `Export failed (${response.status}).`);
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `umutungo-${dataset}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function queryString(values: Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  checkApiHealth,
  getOperationsReport: (institutionId?: number, includeDescendants = false) =>
    request<OperationsReport>(
      `/api/v1/reports/operations${queryString({
        institution_id: institutionId,
        include_descendants: includeDescendants || undefined,
      })}`,
    ),
  getInstitutionTreeReport: () =>
    request<InstitutionTreeReport>("/api/v1/reports/institution-tree"),
  downloadCsv,
  listAdminUsers: (page = 1, perPage = 100) =>
    request<AdminUser[]>(`/api/v1/admin/users${queryString({ page, per_page: perPage })}`),
  setUserAccess: (userId: string, approved: boolean) =>
    request<AdminUser>(`/api/v1/admin/users/${encodeURIComponent(userId)}/access`, {
      method: "PUT",
      body: JSON.stringify({ approved }),
    }),
  listInstitutions: () => request<Institution[]>("/api/v1/institutions"),
  listAdminInstitutions: () => request<Institution[]>("/api/v1/admin/institutions"),
  syncOfficialInstitutionCatalog: () =>
    request<CatalogSyncResult>("/api/v1/admin/institutions/sync-official-catalog", {
      method: "POST",
    }),
  createInstitution: (payload: InstitutionCreate) =>
    request<Institution>("/api/v1/admin/institutions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateInstitution: (institutionId: number, payload: InstitutionUpdate) =>
    request<Institution>(`/api/v1/admin/institutions/${institutionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listInstitutionMemberships: (institutionId?: number) =>
    request<InstitutionMembership[]>(
      `/api/v1/admin/memberships${queryString({ institution_id: institutionId })}`,
    ),
  createInstitutionMembership: (payload: InstitutionMembershipCreate) =>
    request<InstitutionMembership>("/api/v1/admin/memberships", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateInstitutionMembership: (
    userId: string,
    institutionId: number,
    role: InstitutionMembership["role"],
  ) =>
    request<InstitutionMembership>(
      `/api/v1/admin/memberships/${encodeURIComponent(userId)}/${institutionId}`,
      { method: "PATCH", body: JSON.stringify({ role }) },
    ),
  deleteInstitutionMembership: (userId: string, institutionId: number) =>
    request<void>(
      `/api/v1/admin/memberships/${encodeURIComponent(userId)}/${institutionId}`,
      { method: "DELETE" },
    ),
  listAssets: () => request<Asset[]>("/api/v1/assets?active=true"),
  createAsset: (payload: AssetCreate) =>
    request<Asset>("/api/v1/assets", { method: "POST", body: JSON.stringify(payload) }),
  updateAsset: (id: number, payload: AssetUpdate) =>
    request<Asset>(`/api/v1/assets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getAsset: (id: number) => request<Asset>(`/api/v1/assets/${id}`),
  listTriage: (riskLevel?: RiskLevel) =>
    request<TriageItem[]>(`/api/v1/triage${queryString({ risk_level: riskLevel })}`),
  createTriageRun: () => request<TriageRun>("/api/v1/triage-runs", { method: "POST" }),
  listTriageRuns: () => request<TriageRun[]>("/api/v1/triage-runs?limit=100"),
  listRecommendations: (runId?: number) =>
    request<Recommendation[]>(`/api/v1/recommendations${queryString({ run_id: runId, limit: 500 })}`),
  listRecommendationEvents: (recommendationId: number) =>
    request<RecommendationEvent[]>(`/api/v1/recommendations/${recommendationId}/events`),
  listInspections: (assetId: number) =>
    request<InspectionRecord[]>(`/api/v1/assets/${assetId}/inspections`),
  createInspection: (assetId: number, payload: InspectionCreate) =>
    request<InspectionRecord>(`/api/v1/assets/${assetId}/inspections`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listMaintenance: (assetId: number) =>
    request<MaintenanceRecord[]>(`/api/v1/assets/${assetId}/maintenance`),
  createMaintenance: (assetId: number, payload: MaintenanceCreate) =>
    request<MaintenanceRecord>(`/api/v1/assets/${assetId}/maintenance`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addReview: (recommendationId: number, disposition: Disposition, reason: string) =>
    request<RecommendationEvent>(`/api/v1/recommendations/${recommendationId}/events`, {
      method: "POST",
      body: JSON.stringify({ event_type: "review", disposition, reason }),
    }),
  addOutcome: (
    recommendationId: number,
    outcome: Outcome,
    occurredOn: string,
    reason?: string,
  ) =>
    request<RecommendationEvent>(`/api/v1/recommendations/${recommendationId}/events`, {
      method: "POST",
      body: JSON.stringify({
        event_type: "outcome",
        outcome,
        occurred_on: occurredOn,
        reason: reason || undefined,
      }),
    }),
};
