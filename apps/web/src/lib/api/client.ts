import type {
  Asset,
  AssetCreate,
  AdminUser,
  Disposition,
  InspectionCreate,
  InspectionRecord,
  MaintenanceCreate,
  MaintenanceRecord,
  Outcome,
  Recommendation,
  RecommendationEvent,
  RiskLevel,
  TriageItem,
  TriageRun,
} from "./types";
import { supabaseIsConfigured, getSupabaseBrowserClient } from "@/lib/supabase/client";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders: Record<string, string> = {};
  if (supabaseIsConfigured()) {
    const { data, error } = await getSupabaseBrowserClient().auth.getSession();
    if (error) throw error;
    if (!data.session) throw new Error("Your session has expired. Sign in again.");
    authHeaders.Authorization = `Bearer ${data.session.access_token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...authHeaders,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
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
        ? (payload as { detail: unknown }).detail
        : null;
    if (typeof detail === "string") throw new Error(detail);
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((issue) => {
        if (typeof issue !== "object" || issue === null || !("msg" in issue)) return [];
        const message = issue.msg;
        return typeof message === "string" ? [message] : [];
      });
      if (messages.length) throw new Error(messages.join(" "));
    }
    throw new Error(`Request failed (${response.status}).`);
  }

  return (await response.json()) as T;
}

function queryString(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  listAdminUsers: () => request<AdminUser[]>("/api/v1/admin/users"),
  setUserAccess: (userId: string, approved: boolean) =>
    request<AdminUser>(`/api/v1/admin/users/${encodeURIComponent(userId)}/access`, {
      method: "PUT",
      body: JSON.stringify({ approved }),
    }),
  listAssets: () => request<Asset[]>("/api/v1/assets?active=true"),
  createAsset: (payload: AssetCreate) =>
    request<Asset>("/api/v1/assets", { method: "POST", body: JSON.stringify(payload) }),
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
