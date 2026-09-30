"use client";

import {
  Children,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { Icon, IconName } from "@/components/icons";
import { AccessManagement } from "@/features/admin/access-management";
import { ProfilePanel, avatarInitials } from "@/features/profile/profile-panel";
import { OperationsReportView } from "@/features/reports/operations-report";
import { api } from "@/lib/api/client";
import type {
  Asset,
  AssetCondition,
  AssetCreate,
  Disposition,
  InspectionRecord,
  MaintenanceRecord,
  Outcome,
  Recommendation,
  RecommendationEvent,
  RiskLevel,
  TriageItem,
} from "@/lib/api/types";

type View = "overview" | "assets" | "recommendations" | "reports" | "users";

const navigation: { id: Exclude<View, "users">; label: string; icon: IconName }[] = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "assets", label: "Asset register", icon: "assets" },
  { id: "recommendations", label: "Recommendations", icon: "recommendations" },
  { id: "reports", label: "Data quality", icon: "reports" },
];

const riskOrder: RiskLevel[] = ["critical", "high", "medium", "low", "insufficient_data"];

function displayDate(value: string | null | undefined) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export function Dashboard({
  user,
  onSignOut,
}: {
  user: User;
  onSignOut: () => Promise<void>;
}) {
  const [view, setView] = useState<View>("overview");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [triage, setTriage] = useState<TriageItem[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof api.listTriageRuns>>>([]);
  const [activeRun, setActiveRun] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(
    null,
  );
  const [showProfile, setShowProfile] = useState(false);
  const [showAssetForm, setShowAssetForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const reportError = useCallback((message: string) => setError(message), []);
  const email = user.email ?? "Signed-in user";
  const displayName =
    typeof user.user_metadata.full_name === "string" && user.user_metadata.full_name.trim()
      ? user.user_metadata.full_name.trim()
      : email;
  const isApproved = user.app_metadata.govasset_access === "approved";
  const isAdmin = user.app_metadata.govasset_role === "admin";

  const fetchDashboardData = useCallback(
    () => Promise.all([api.listAssets(), api.listTriage()]),
    [],
  );

  const loadData = useCallback(
    async (background = false) => {
      if (background) setRefreshing(true);
      try {
        const [nextAssets, nextTriage] = await fetchDashboardData();
        setAssets(nextAssets);
        setTriage(nextTriage);
        setError("");
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [fetchDashboardData],
  );

  useEffect(() => {
    let cancelled = false;
    fetchDashboardData()
      .then(([nextAssets, nextTriage]) => {
        if (!cancelled) {
          setAssets(nextAssets);
          setTriage(nextTriage);
          setError("");
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchDashboardData]);

  const filteredTriage = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return triage.filter((item) => {
      const matchesRisk = riskFilter === "all" || item.risk_level === riskFilter;
      const matchesSearch =
        !normalizedSearch ||
        [item.asset.asset_code, item.asset.asset_type, item.asset.make, item.asset.model]
          .filter(Boolean)
          .some((value) => value!.toLowerCase().includes(normalizedSearch));
      return matchesRisk && matchesSearch;
    });
  }, [riskFilter, search, triage]);

  const filteredAssets = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return assets.filter((asset) =>
      [asset.asset_code, asset.asset_type, asset.make, asset.model]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(normalizedSearch)),
    );
  }, [assets, search]);

  const riskCounts = useMemo(
    () =>
      triage.reduce(
        (counts, item) => {
          counts[item.risk_level] += 1;
          return counts;
        },
        {
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          insufficient_data: 0,
        } satisfies Record<RiskLevel, number>,
      ),
    [triage],
  );

  async function openAsset(asset: Asset) {
    setError("");
    try {
      setSelectedAsset(await api.getAsset(asset.id));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  function openRecommendation(recommendation: Recommendation) {
    setSelectedRecommendation(recommendation);
  }

  async function generateRecommendations() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const run = await api.createTriageRun();
      const nextRecommendations = await api.listRecommendations(run.id);
      setRuns((currentRuns) => [run, ...currentRuns.filter((current) => current.id !== run.id)]);
      setActiveRun(run.id);
      setRecommendations(nextRecommendations);
      setView("recommendations");
      setNotice(`Saved ${run.recommendation_count} recommendations in run ${run.id}.`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function loadLatestRecommendations() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const nextRuns = await api.listTriageRuns();
      setRuns(nextRuns);
      const latestRun = nextRuns[0]?.id ?? null;
      setActiveRun(latestRun);
      setRecommendations(latestRun === null ? [] : await api.listRecommendations(latestRun));
      setView("recommendations");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function selectRun(runId: number) {
    setBusy(true);
    setError("");
    try {
      setRecommendations(await api.listRecommendations(runId));
      setActiveRun(runId);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function createAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: AssetCreate = {
      asset_code: String(form.get("asset_code") ?? "").trim(),
      asset_type: String(form.get("asset_type") ?? "").trim(),
      make: String(form.get("make") ?? "").trim() || null,
      model: String(form.get("model") ?? "").trim() || null,
      acquisition_date: String(form.get("acquisition_date") ?? "") || null,
      last_service_date: String(form.get("last_service_date") ?? "") || null,
      next_service_due: String(form.get("next_service_due") ?? "") || null,
      condition: String(form.get("condition") ?? "unknown") as AssetCondition,
    };
    setBusy(true);
    setError("");
    try {
      await api.createAsset(payload);
      setShowAssetForm(false);
      setNotice("Asset added to the register.");
      await loadData(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Umutungo home">
          <span className="brand-mark">
            <Icon name="activity" />
          </span>
          <span className="brand-name">
            Umutungo
          </span>
        </Link>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="primary-nav" aria-label="Main navigation">
          {[...navigation, ...(isAdmin ? [{ id: "users" as const, label: "User access", icon: "users" as const }] : [])].map((item) => (
            <button
              className={`nav-item ${view === item.id ? "active" : ""}`}
              key={item.id}
              onClick={() => {
                setView(item.id);
                setSearch("");
                setError("");
              }}
              type="button"
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.id === "assets" && <span className="nav-count">{assets.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="pilot-note">
            <div className="pilot-note-icon">
              <Icon name="warning" />
            </div>
            <strong>Decision support only</strong>
            <p>Recommendations are rule-based and require staff review.</p>
          </div>
          <button
            aria-label="Open user profile"
            className="profile profile-button"
            onClick={() => setShowProfile(true)}
            type="button"
          >
            <div className="avatar">{avatarInitials(displayName)}</div>
            <div className="profile-copy">
              <strong>{displayName}</strong>
              <span>{isApproved ? "Approved account" : "Pending approval"}</span>
            </div>
            <span
              className={`online-dot ${isApproved ? "" : "pending"}`}
              title={isApproved ? "Account approved" : "Awaiting administrator approval"}
            />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <Icon name="chevron" />
            <strong>
              {view === "overview"
                ? "Overview"
                : view === "assets"
                  ? "Asset register"
                  : view === "recommendations"
                    ? "Recommendations"
                      : view === "reports"
                        ? "Data quality"
                        : "User access"}
            </strong>
          </div>
          <div className="topbar-actions">
            <span className="local-badge">
              <span /> Local pilot
            </span>
            <button
              aria-label="Refresh data"
              className={`icon-button ${refreshing ? "spinning" : ""}`}
              disabled={refreshing || loading}
              onClick={() => void loadData(true)}
              type="button"
            >
              <Icon name="refresh" />
            </button>
            <button
              className="signout-button"
              onClick={() => void onSignOut().catch((error: unknown) => setError(getErrorMessage(error)))}
              type="button"
            >
              Sign out
            </button>
            <button
              aria-label="Open user profile"
              className="avatar avatar-small avatar-button"
              onClick={() => setShowProfile(true)}
              type="button"
            >
              {avatarInitials(displayName)}
            </button>
          </div>
        </header>

        <div className="page-content">
          {error && (
            <div className="feedback-banner error-banner" role="alert">
              <Icon name="warning" />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")} type="button">
                <Icon name="close" />
              </button>
            </div>
          )}
          {notice && (
            <div className="feedback-banner success-banner" role="status">
              <Icon name="check" />
              <span>{notice}</span>
              <button aria-label="Dismiss notification" onClick={() => setNotice("")} type="button">
                <Icon name="close" />
              </button>
            </div>
          )}

          {view === "overview" && (
            <Overview
              assets={assets}
              busy={busy}
              filteredTriage={filteredTriage}
              loading={loading}
              onAddAsset={() => setShowAssetForm(true)}
              onGenerate={() => void generateRecommendations()}
              onOpenAsset={(asset) => void openAsset(asset)}
              onRiskFilter={setRiskFilter}
              onSearch={setSearch}
              onViewAllAssets={() => {
                setView("assets");
                setSearch("");
              }}
              riskCounts={riskCounts}
              riskFilter={riskFilter}
              search={search}
              triage={triage}
            />
          )}
          {view === "assets" && (
            <AssetRegister
              assets={filteredAssets}
              loading={loading}
              onAdd={() => setShowAssetForm(true)}
              onOpen={(asset) => void openAsset(asset)}
              onSearch={setSearch}
              search={search}
            />
          )}
          {view === "recommendations" && (
            <RecommendationList
              activeRun={activeRun}
              busy={busy}
              onGenerate={() => void generateRecommendations()}
              onLoadLatest={() => void loadLatestRecommendations()}
              onOpen={(recommendation) => void openRecommendation(recommendation)}
              onSelectRun={(runId) => void selectRun(runId)}
              recommendations={recommendations}
              runs={runs}
            />
          )}
          {view === "users" && isAdmin && <AccessManagement currentUserId={user.id} />}
          {view === "reports" && <OperationsReportView />}
        </div>
      </main>

      {selectedAsset && (
        <AssetDrawer
          asset={selectedAsset}
          onClose={() => setSelectedAsset(null)}
          onError={reportError}
          onSaved={async (message) => {
            setSelectedAsset(await api.getAsset(selectedAsset.id));
            setNotice(message);
            await loadData(true);
          }}
        />
      )}
      {selectedRecommendation && (
        <RecommendationDrawer
          recommendation={selectedRecommendation}
          onClose={() => setSelectedRecommendation(null)}
          onError={(message) => setError(message)}
          onSaved={(message) => setNotice(message)}
        />
      )}
      {showProfile && <ProfilePanel user={user} onClose={() => setShowProfile(false)} />}
      {showAssetForm && (
        <Modal title="Add an asset" onClose={() => setShowAssetForm(false)}>
          <form className="form-stack" onSubmit={(event) => void createAsset(event)}>
            <div className="form-grid">
              <Field label="Asset code" name="asset_code" required placeholder="e.g. GOV-00125" />
              <Field label="Asset type" name="asset_type" required placeholder="e.g. Vehicle" />
              <Field label="Make" name="make" placeholder="e.g. Toyota" />
              <Field label="Model" name="model" placeholder="e.g. Land Cruiser" />
              <Field label="Acquisition date" name="acquisition_date" type="date" />
              <SelectField
                label="Recorded condition"
                name="condition"
                options={["unknown", "good", "fair", "poor", "critical"]}
              />
              <Field label="Last service" name="last_service_date" type="date" />
              <Field label="Next service due" name="next_service_due" type="date" />
            </div>
            <p className="form-hint">
              Use the official asset identifier assigned by the source institution.
            </p>
            <div className="modal-actions">
              <button className="button button-secondary" onClick={() => setShowAssetForm(false)} type="button">
                Cancel
              </button>
              <button className="button button-primary" disabled={busy} type="submit">
                {busy ? "Saving…" : "Add asset"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Overview({
  assets,
  busy,
  filteredTriage,
  loading,
  onAddAsset,
  onGenerate,
  onOpenAsset,
  onRiskFilter,
  onSearch,
  onViewAllAssets,
  riskCounts,
  riskFilter,
  search,
  triage,
}: {
  assets: Asset[];
  busy: boolean;
  filteredTriage: TriageItem[];
  loading: boolean;
  onAddAsset: () => void;
  onGenerate: () => void;
  onOpenAsset: (asset: Asset) => void;
  onRiskFilter: (value: RiskLevel | "all") => void;
  onSearch: (value: string) => void;
  onViewAllAssets: () => void;
  riskCounts: Record<RiskLevel, number>;
  riskFilter: RiskLevel | "all";
  search: string;
  triage: TriageItem[];
}) {
  const attentionCount = riskCounts.critical + riskCounts.high;
  const upcomingCount = riskCounts.medium;
  const coveredPercent = triage.length
    ? Math.round(
        ((triage.length - riskCounts.insufficient_data) / triage.length) * 100,
      )
    : 0;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">FLEET OPERATIONS</div>
          <h1>Good morning</h1>
          <p className="page-subtitle">
            Here&apos;s your asset overview and maintenance triage for today.
          </p>
        </div>
        <div className="heading-actions">
          <button className="button button-secondary" onClick={onAddAsset} type="button">
            <Icon name="plus" /> Add asset
          </button>
          <button
            className="button button-primary"
            disabled={busy || loading || assets.length === 0}
            onClick={onGenerate}
            type="button"
          >
            <Icon name="activity" />
            {busy ? "Generating…" : "Save triage run"}
          </button>
        </div>
      </section>

      <section aria-label="Asset summary" className="metric-grid">
        <MetricCard
          accent="navy"
          icon="assets"
          label="Active assets"
          value={loading ? "—" : assets.length.toLocaleString()}
          foot={<span className="metric-foot neutral">In the local register</span>}
        />
        <MetricCard
          accent="red"
          icon="warning"
          label="Priority review"
          value={loading ? "—" : attentionCount.toString()}
          foot={<span className="metric-foot danger">{riskCounts.critical} critical · {riskCounts.high} high</span>}
        />
        <MetricCard
          accent="amber"
          icon="clock"
          label="Upcoming attention"
          value={loading ? "—" : upcomingCount.toString()}
          foot={<span className="metric-foot neutral">Due soon or fair condition</span>}
        />
        <MetricCard
          accent="green"
          icon="check"
          label="Triage coverage"
          value={loading ? "—" : `${coveredPercent}%`}
          foot={
            <span className={`metric-foot ${riskCounts.insufficient_data ? "warning-text" : "positive"}`}>
              {riskCounts.insufficient_data} insufficient data
            </span>
          }
        />
      </section>

      <section className="insight-banner">
        <div className="insight-icon"><Icon name="activity" /></div>
        <div className="insight-copy">
          <strong>Transparent rules. Human decisions.</strong>
          <p>
            Priority bands use recorded condition and service dates. They are not failure predictions;
            confirm each recommendation with an authorized maintenance officer.
          </p>
        </div>
        <span className="rule-version">RULE SET · V1</span>
      </section>

      <section className="panel queue-panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title-row">
              <h2>Maintenance triage</h2>
              <span className="count-pill">{triage.length}</span>
            </div>
            <p>Assets ranked for staff review using the current rule set.</p>
          </div>
          <button className="text-button" onClick={onViewAllAssets} type="button">
            Asset register <Icon name="arrow" />
          </button>
        </div>
        <div className="table-toolbar">
          <label className="search-field">
            <Icon name="search" />
            <input
              aria-label="Search assets"
              onChange={(event) => onSearch(event.target.value)}
              placeholder="Search asset, type or make…"
              value={search}
            />
            {search && (
              <button aria-label="Clear search" onClick={() => onSearch("")} type="button">
                <Icon name="close" />
              </button>
            )}
          </label>
          <label className="filter-select">
            <span>Priority</span>
            <select
              aria-label="Filter by priority"
              onChange={(event) => onRiskFilter(event.target.value as RiskLevel | "all")}
              value={riskFilter}
            >
              <option value="all">All levels</option>
              {riskOrder.map((risk) => <option key={risk} value={risk}>{titleCase(risk)}</option>)}
            </select>
          </label>
        </div>
        <TriageTable items={filteredTriage} loading={loading} onOpenAsset={onOpenAsset} />
        {!loading && filteredTriage.length === 0 && (
          <EmptyState
            title={triage.length ? "No matching assets" : "No assets in the triage queue"}
            detail={triage.length ? "Try another search or priority filter." : "Add assets to begin reviewing maintenance priorities."}
          />
        )}
        <div className="table-footer">
          Showing <strong>{filteredTriage.length}</strong> of <strong>{triage.length}</strong> active assets
          <span className="footer-dot" />
          As of {displayDate(new Date().toISOString().slice(0, 10))}
        </div>
      </section>
    </>
  );
}

function MetricCard({
  accent,
  foot,
  icon,
  label,
  value,
}: {
  accent: string;
  foot: ReactNode;
  icon: IconName;
  label: string;
  value: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${accent}`}><Icon name={icon} /></span>
      </div>
      <strong className="metric-value">{value}</strong>
      {foot}
    </article>
  );
}

function TriageTable({
  items,
  loading,
  onOpenAsset,
}: {
  items: TriageItem[];
  loading: boolean;
  onOpenAsset: (asset: Asset) => void;
}) {
  if (loading) {
    return (
      <div className="loading-state">
        <span className="spinner" /> Loading asset data…
      </div>
    );
  }
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Priority</th>
            <th>Condition</th>
            <th>Next service</th>
            <th>Reason for flag</th>
            <th><span className="sr-only">Open asset details</span></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.asset.id}>
              <td>
                <div className="asset-cell">
                  <span className="asset-avatar">{item.asset.asset_type.slice(0, 1).toUpperCase()}</span>
                  <button className="asset-link" onClick={() => onOpenAsset(item.asset)} type="button">
                    <strong>{item.asset.asset_code}</strong>
                    <small>{[item.asset.make, item.asset.model].filter(Boolean).join(" ") || titleCase(item.asset.asset_type)}</small>
                  </button>
                </div>
              </td>
              <td><RiskBadge level={item.risk_level} /></td>
              <td><ConditionBadge condition={item.asset.condition} /></td>
              <td className="muted-cell">{displayDate(item.asset.next_service_due)}</td>
              <td className="reason-cell">{item.reasons.join(" ")}</td>
              <td><button className="row-open" aria-label={`Open ${item.asset.asset_code}`} onClick={() => onOpenAsset(item.asset)} type="button"><Icon name="chevron" /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssetRegister({
  assets,
  loading,
  onAdd,
  onOpen,
  onSearch,
  search,
}: {
  assets: Asset[];
  loading: boolean;
  onAdd: () => void;
  onOpen: (asset: Asset) => void;
  onSearch: (value: string) => void;
  search: string;
}) {
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">FLEET OPERATIONS</div>
          <h1>Asset register</h1>
          <p className="page-subtitle">Browse active assets and review their recorded history.</p>
        </div>
        <button className="button button-primary" onClick={onAdd} type="button">
          <Icon name="plus" /> Add asset
        </button>
      </section>
      <section className="panel queue-panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title-row">
              <h2>Registered assets</h2>
              <span className="count-pill">{assets.length}</span>
            </div>
            <p>Asset details are kept in this prototype&apos;s local database.</p>
          </div>
        </div>
        <div className="table-toolbar">
          <label className="search-field">
            <Icon name="search" />
            <input
              aria-label="Search asset register"
              onChange={(event) => onSearch(event.target.value)}
              placeholder="Search asset, type or make…"
              value={search}
            />
          </label>
        </div>
        {loading ? (
          <div className="loading-state"><span className="spinner" /> Loading assets…</div>
        ) : assets.length === 0 ? (
          <EmptyState title="No assets found" detail="Try a different search or add an asset to the register." />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Asset</th><th>Type</th><th>Condition</th><th>Last inspection</th><th>Next service</th><th /></tr></thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>
                      <div className="asset-cell">
                        <span className="asset-avatar">{asset.asset_type.slice(0, 1).toUpperCase()}</span>
                        <button className="asset-link" onClick={() => onOpen(asset)} type="button"><strong>{asset.asset_code}</strong><small>{[asset.make, asset.model].filter(Boolean).join(" ") || "Make and model not recorded"}</small></button>
                      </div>
                    </td>
                    <td>{titleCase(asset.asset_type)}</td>
                    <td><ConditionBadge condition={asset.condition} /></td>
                    <td className="muted-cell">{displayDate(asset.last_inspected_on)}</td>
                    <td className="muted-cell">{displayDate(asset.next_service_due)}</td>
                    <td><button className="row-open" aria-label={`Open ${asset.asset_code}`} onClick={() => onOpen(asset)} type="button"><Icon name="chevron" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-footer">Showing <strong>{assets.length}</strong> active assets</div>
      </section>
    </>
  );
}

function RecommendationList({
  activeRun,
  busy,
  onGenerate,
  onLoadLatest,
  onOpen,
  onSelectRun,
  recommendations,
  runs,
}: {
  activeRun: number | null;
  busy: boolean;
  onGenerate: () => void;
  onLoadLatest: () => void;
  onOpen: (recommendation: Recommendation) => void;
  onSelectRun: (runId: number) => void;
  recommendations: Recommendation[];
  runs: Awaited<ReturnType<typeof api.listTriageRuns>>;
}) {
  const counts = recommendations.reduce<Record<RiskLevel, number>>(
    (result, recommendation) => {
      result[recommendation.risk_level] += 1;
      return result;
    },
    { critical: 0, high: 0, medium: 0, low: 0, insufficient_data: 0 },
  );
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">DECISION HISTORY</div>
          <h1>Recommendations</h1>
          <p className="page-subtitle">Saved rule-based triage runs and their review history.</p>
        </div>
        <div className="heading-actions">
          <button className="button button-secondary" disabled={busy} onClick={onLoadLatest} type="button">
            <Icon name="clock" /> Load saved runs
          </button>
          <button className="button button-primary" disabled={busy} onClick={onGenerate} type="button">
            <Icon name="activity" /> {busy ? "Generating…" : "Save triage run"}
          </button>
        </div>
      </section>
      <div className="recommendation-callout">
        <Icon name="warning" />
        <span>These are transparent scheduling/condition rules, not AI predictions. Review with qualified staff before action.</span>
      </div>
      <section className="panel queue-panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title-row">
              <h2>{activeRun ? `Run ${activeRun}` : "Saved recommendations"}</h2>
              <span className="count-pill">{recommendations.length}</span>
            </div>
            <p>
              {recommendations.length
                ? `${counts.critical} critical · ${counts.high} high · ${counts.medium} medium · ${counts.insufficient_data} need data`
                : "Generate a triage run to save a point-in-time recommendation snapshot."}
            </p>
          </div>
          {runs.length > 0 && (
            <label className="run-select">
              <span>Saved run</span>
              <select
                aria-label="Select saved triage run"
                disabled={busy}
                onChange={(event) => onSelectRun(Number(event.target.value))}
                value={activeRun ?? ""}
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    #{run.id} · {displayDate(run.evaluated_on)} · {run.recommendation_count} assets
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {recommendations.length === 0 ? (
          <EmptyState title="No recommendations loaded" detail="Generate a run or load saved recommendations from the local API." />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Asset</th><th>Priority</th><th>Recorded condition</th><th>Evaluated</th><th>Reason</th><th /></tr></thead>
              <tbody>
                {recommendations.map((recommendation) => (
                  <tr key={recommendation.id}>
                    <td>
                      <div className="asset-cell">
                        <span className="asset-avatar">{recommendation.asset_snapshot.asset_type.slice(0, 1).toUpperCase()}</span>
                        <button className="asset-link" onClick={() => onOpen(recommendation)} type="button"><strong>{recommendation.asset_snapshot.asset_code}</strong><small>Run {recommendation.run_id}</small></button>
                      </div>
                    </td>
                    <td><RiskBadge level={recommendation.risk_level} /></td>
                    <td><ConditionBadge condition={recommendation.asset_snapshot.condition} /></td>
                    <td className="muted-cell">{displayDate(recommendation.evaluated_on)}</td>
                    <td className="reason-cell">{recommendation.reasons.join(" ")}</td>
                    <td><button className="row-open" aria-label={`Review ${recommendation.asset_snapshot.asset_code}`} onClick={() => onOpen(recommendation)} type="button"><Icon name="chevron" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function AssetDrawer({
  asset,
  onClose,
  onError,
  onSaved,
}: {
  asset: Asset;
  onClose: () => void;
  onError: (message: string) => void;
  onSaved: (message: string) => Promise<void>;
}) {
  const [tab, setTab] = useState<"overview" | "inspections" | "maintenance">("overview");
  const [inspections, setInspections] = useState<InspectionRecord[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRecord[]>([]);
  const [loadedHistoryForAsset, setLoadedHistoryForAsset] = useState<Asset["id"] | null>(null);
  const loadingHistory = loadedHistoryForAsset !== asset.id;
  const [busy, setBusy] = useState(false);
  const [showInspectionForm, setShowInspectionForm] = useState(false);
  const [showMaintenanceForm, setShowMaintenanceForm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listInspections(asset.id), api.listMaintenance(asset.id)])
      .then(([nextInspections, nextMaintenance]) => {
        if (!cancelled) {
          setInspections(nextInspections);
          setMaintenance(nextMaintenance);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) onError(getErrorMessage(error));
      })
      .finally(() => {
        if (!cancelled) setLoadedHistoryForAsset(asset.id);
      });
    return () => {
      cancelled = true;
    };
  }, [asset.id, onError]);

  async function submitInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await api.createInspection(asset.id, {
        inspected_on: String(form.get("inspected_on")),
        condition: String(form.get("condition")) as Exclude<AssetCondition, "unknown">,
        observations: String(form.get("observations") ?? "").trim() || null,
      });
      setShowInspectionForm(false);
      setTab("inspections");
      setInspections(await api.listInspections(asset.id));
      await onSaved("Inspection recorded and asset condition updated.");
    } catch (error) {
      onError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function submitMaintenance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const downtime = String(form.get("downtime_hours") ?? "");
    setBusy(true);
    try {
      await api.createMaintenance(asset.id, {
        event_date: String(form.get("event_date")),
        category: String(form.get("category")),
        description: String(form.get("description") ?? "").trim() || null,
        planned: form.get("planned") === "on",
        downtime_hours: downtime ? Number(downtime) : null,
      });
      setShowMaintenanceForm(false);
      setTab("maintenance");
      setMaintenance(await api.listMaintenance(asset.id));
      await onSaved("Maintenance record added.");
    } catch (error) {
      onError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside aria-label={`Asset ${asset.asset_code}`} aria-modal="true" className="detail-drawer" role="dialog">
        <DrawerHeader
          eyebrow="ASSET PROFILE"
          title={asset.asset_code}
          subtitle={[asset.make, asset.model, titleCase(asset.asset_type)].filter(Boolean).join(" · ")}
          onClose={onClose}
        />
        <div className="drawer-risk-row">
          <ConditionBadge condition={asset.condition} />
          <span className="small-muted">Current recorded condition</span>
        </div>
        <div className="drawer-tabs" role="tablist" aria-label="Asset record sections">
          {(["overview", "inspections", "maintenance"] as const).map((value) => (
            <button
              aria-selected={tab === value}
              className={tab === value ? "selected" : ""}
              key={value}
              onClick={() => setTab(value)}
              role="tab"
              type="button"
            >
              {titleCase(value)}
              {value === "inspections" && <span>{inspections.length}</span>}
              {value === "maintenance" && <span>{maintenance.length}</span>}
            </button>
          ))}
        </div>
        <div className="drawer-content">
          {tab === "overview" && (
            <>
              <div className="detail-section">
                <SectionTitle title="Asset information" />
                <DetailRow label="Asset code" value={asset.asset_code} />
                <DetailRow label="Asset type" value={titleCase(asset.asset_type)} />
                <DetailRow label="Make and model" value={[asset.make, asset.model].filter(Boolean).join(" ") || "Not recorded"} />
                <DetailRow label="Acquired" value={displayDate(asset.acquisition_date)} />
              </div>
              <div className="detail-section">
                <SectionTitle title="Maintenance schedule" />
                <DetailRow label="Last inspection" value={displayDate(asset.last_inspected_on)} />
                <DetailRow label="Last service" value={displayDate(asset.last_service_date)} />
                <DetailRow label="Next service due" value={displayDate(asset.next_service_due)} />
              </div>
              <div className="action-card">
                <strong>Staff review required</strong>
                <p>Verify the record and apply institution maintenance procedures before scheduling work.</p>
              </div>
            </>
          )}
          {tab === "inspections" && (
            <HistorySection
              empty="No inspections have been recorded."
              isLoading={loadingHistory}
              onAdd={() => setShowInspectionForm(true)}
              title="Inspection history"
            >
              {inspections.map((inspection) => (
                <HistoryItem
                  date={displayDate(inspection.inspected_on)}
                  key={inspection.id}
                  label={`Condition: ${titleCase(inspection.condition)}`}
                  detail={inspection.observations || "No additional observations."}
                  tone={inspection.condition}
                />
              ))}
            </HistorySection>
          )}
          {tab === "maintenance" && (
            <HistorySection
              empty="No maintenance history has been recorded."
              isLoading={loadingHistory}
              onAdd={() => setShowMaintenanceForm(true)}
              title="Maintenance history"
            >
              {maintenance.map((record) => (
                <HistoryItem
                  date={displayDate(record.event_date)}
                  key={record.id}
                  label={titleCase(record.category)}
                  detail={`${record.planned ? "Planned" : "Unplanned"}${record.downtime_hours !== null ? ` · ${record.downtime_hours} hours downtime` : ""}${record.description ? ` · ${record.description}` : ""}`}
                  tone={record.planned ? "good" : "fair"}
                />
              ))}
            </HistorySection>
          )}
        </div>
        <div className="drawer-footer">
          <button className="button button-secondary full-width" onClick={onClose} type="button">Close profile</button>
        </div>
        {showInspectionForm && (
          <Modal title="Record inspection" onClose={() => setShowInspectionForm(false)}>
            <form className="form-stack" onSubmit={(event) => void submitInspection(event)}>
              <Field label="Inspection date" name="inspected_on" required type="date" max={new Date().toISOString().slice(0, 10)} />
              <SelectField label="Observed condition" name="condition" options={["good", "fair", "poor", "critical"]} />
              <TextAreaField label="Observations" name="observations" placeholder="Record observed issues or inspection notes" />
              <div className="modal-actions">
                <button className="button button-secondary" onClick={() => setShowInspectionForm(false)} type="button">Cancel</button>
                <button className="button button-primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save inspection"}</button>
              </div>
            </form>
          </Modal>
        )}
        {showMaintenanceForm && (
          <Modal title="Record maintenance" onClose={() => setShowMaintenanceForm(false)}>
            <form className="form-stack" onSubmit={(event) => void submitMaintenance(event)}>
              <Field label="Event date" name="event_date" required type="date" max={new Date().toISOString().slice(0, 10)} />
              <SelectField label="Work category" name="category" options={["inspection", "scheduled_service", "repair", "parts_replacement", "other"]} />
              <Field label="Downtime (hours)" min="0" name="downtime_hours" step="0.25" type="number" />
              <label className="checkbox-field"><input name="planned" type="checkbox" /> This work was planned</label>
              <TextAreaField label="Work notes" name="description" placeholder="Describe work completed or findings" />
              <div className="modal-actions">
                <button className="button button-secondary" onClick={() => setShowMaintenanceForm(false)} type="button">Cancel</button>
                <button className="button button-primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save maintenance"}</button>
              </div>
            </form>
          </Modal>
        )}
      </aside>
    </div>
  );
}

function RecommendationDrawer({
  recommendation,
  onClose,
  onError,
  onSaved,
}: {
  recommendation: Recommendation;
  onClose: () => void;
  onError: (message: string) => void;
  onSaved: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [outcomeReason, setOutcomeReason] = useState("");
  const [outcome, setOutcome] = useState<Outcome>("unscheduled_repair");
  const [outcomeDate, setOutcomeDate] = useState(new Date().toISOString().slice(0, 10));
  const [events, setEvents] = useState<RecommendationEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);

  const refreshEvents = useCallback(
    () =>
      api
        .listRecommendationEvents(recommendation.id)
        .then(setEvents)
        .catch((error: unknown) => onError(getErrorMessage(error)))
        .finally(() => setLoadingEvents(false)),
    [onError, recommendation.id],
  );

  useEffect(() => {
    void refreshEvents();
  }, [refreshEvents]);

  async function submitReview(disposition: Disposition) {
    if (!reason.trim()) {
      onError("Add a reason before recording the review.");
      return;
    }
    setBusy(true);
    try {
      await api.addReview(recommendation.id, disposition, reason.trim());
      setReason("");
      await refreshEvents();
      onSaved(`Recommendation marked ${disposition}.`);
    } catch (error) {
      onError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function submitOutcome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.addOutcome(recommendation.id, outcome, outcomeDate, outcomeReason.trim());
      setOutcomeReason("");
      await refreshEvents();
      onSaved("Verified outcome recorded.");
    } catch (error) {
      onError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  const asset = recommendation.asset_snapshot;
  return (
    <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside aria-label={`Recommendation for ${asset.asset_code}`} aria-modal="true" className="detail-drawer" role="dialog">
        <DrawerHeader
          eyebrow={`SAVED TRIAGE · RUN ${recommendation.run_id}`}
          title={asset.asset_code}
          subtitle={`Evaluated ${displayDate(recommendation.evaluated_on)} · ${recommendation.rule_version}`}
          onClose={onClose}
        />
        <div className="drawer-risk-row">
          <RiskBadge level={recommendation.risk_level} />
          <ConditionBadge condition={asset.condition} />
        </div>
        <div className="drawer-content">
          <div className="detail-section">
            <SectionTitle title="Why this asset was flagged" />
            {recommendation.reasons.map((item) => <div className="reason-detail" key={item}><Icon name="activity" />{item}</div>)}
            <div className="action-card">
              <span className="eyebrow">ADVISORY NEXT STEP</span>
              <p>{recommendation.recommended_action}</p>
            </div>
          </div>
          <div className="detail-section">
            <SectionTitle title="Staff review" />
            <TextAreaField label="Review reason" name="review-reason" onChange={setReason} placeholder="Why accept, defer or reject this recommendation?" value={reason} />
            <div className="disposition-actions">
              {(["accepted", "deferred", "rejected"] as const).map((disposition) => (
                <button
                  className={`button ${disposition === "accepted" ? "button-primary" : "button-secondary"}`}
                  disabled={busy}
                  key={disposition}
                  onClick={() => void submitReview(disposition)}
                  type="button"
                >
                  {titleCase(disposition)}
                </button>
              ))}
            </div>
          </div>
          <div className="detail-section">
            <SectionTitle title="Record verified outcome" />
            <form className="form-stack compact-form" onSubmit={(event) => void submitOutcome(event)}>
              <SelectField
                label="Outcome"
                name="outcome"
                onChange={(value) => setOutcome(value as Outcome)}
                options={["planned_maintenance", "unscheduled_repair", "no_maintenance_found", "other"]}
              />
              <Field label="Outcome date" max={new Date().toISOString().slice(0, 10)} name="outcome_date" onChange={setOutcomeDate} required type="date" value={outcomeDate} />
              <TextAreaField label="Outcome notes" name="outcome_reason" onChange={setOutcomeReason} placeholder="Optional verified finding" value={outcomeReason} />
              <button className="button button-secondary" disabled={busy} type="submit">{busy ? "Saving…" : "Save outcome"}</button>
            </form>
          </div>
          <div className="detail-section">
            <SectionTitle title="Decision history" />
            {loadingEvents ? (
              <div className="loading-state compact"><span className="spinner" /> Loading events…</div>
            ) : events.length ? (
              <div className="event-feed">
                {events.map((event) => (
                  <article className="event-item" key={event.id}>
                    <div className="event-heading">
                      <strong>{event.event_type === "review" ? `Review ${titleCase(event.disposition ?? "")}` : `Outcome · ${titleCase(event.outcome ?? "")}`}</strong>
                      <time>{displayDate(event.occurred_on ?? event.created_at.slice(0, 10))}</time>
                    </div>
                    {event.reason && <p>{event.reason}</p>}
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty-inline">No decisions or verified outcomes recorded yet.</p>
            )}
          </div>
        </div>
        <div className="drawer-footer">
          <button className="button button-secondary full-width" onClick={onClose} type="button">Close recommendation</button>
        </div>
      </aside>
    </div>
  );
}

function DrawerHeader({
  eyebrow,
  onClose,
  subtitle,
  title,
}: {
  eyebrow: string;
  onClose: () => void;
  subtitle: string;
  title: string;
}) {
  return (
    <div className="drawer-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <button aria-label="Close panel" className="icon-button" onClick={onClose} type="button"><Icon name="close" /></button>
    </div>
  );
}

function HistorySection({
  children,
  empty,
  isLoading,
  onAdd,
  title,
}: {
  children: ReactNode;
  empty: string;
  isLoading: boolean;
  onAdd: () => void;
  title: string;
}) {
  return (
    <section>
      <div className="history-heading">
        <SectionTitle title={title} />
        <button className="button button-secondary button-small" onClick={onAdd} type="button"><Icon name="plus" /> Add</button>
      </div>
      {isLoading ? <div className="loading-state compact"><span className="spinner" /> Loading history…</div> : (
        <div className="history-list">
          {Children.count(children) ? children : <p className="empty-inline">{empty}</p>}
        </div>
      )}
    </section>
  );
}

function HistoryItem({
  date,
  detail,
  label,
  tone,
}: {
  date: string;
  detail: string;
  label: string;
  tone: string;
}) {
  return (
    <article className="history-item">
      <span className={`timeline-dot tone-${tone}`} />
      <div className="history-copy">
        <div><strong>{label}</strong><time>{date}</time></div>
        <p>{detail}</p>
      </div>
    </article>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h3 className="section-title">{title}</h3>;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return <div className="detail-row"><span>{label}</span><strong>{value}</strong></div>;
}

function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk-badge risk-${level}`}><span />{titleCase(level)}</span>;
}

function ConditionBadge({ condition }: { condition: AssetCondition }) {
  return <span className={`condition-badge condition-${condition}`}>{titleCase(condition)}</span>;
}

function EmptyState({ detail, title }: { detail: string; title: string }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name="search" /></span><strong>{title}</strong><p>{detail}</p></div>;
}

function Modal({
  children,
  onClose,
  title,
}: {
  children: ReactNode;
  onClose: () => void;
  title: string;
}) {
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="modal-title" aria-modal="true" className="modal-card" role="dialog">
        <div className="modal-heading">
          <h2 id="modal-title">{title}</h2>
          <button aria-label="Close dialog" className="icon-button" onClick={onClose} type="button"><Icon name="close" /></button>
        </div>
        {children}
      </section>
    </div>
  );
}

function Field({
  label,
  max,
  min,
  name,
  onChange,
  placeholder,
  required,
  step,
  type = "text",
  value,
}: {
  label: string;
  max?: string;
  min?: string;
  name: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  step?: string;
  type?: string;
  value?: string;
}) {
  return (
    <label className="field">
      <span>{label}{required && <b> *</b>}</span>
      <input
        max={max}
        min={min}
        name={name}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
        placeholder={placeholder}
        required={required}
        step={step}
        type={type}
        value={value}
      />
    </label>
  );
}

function SelectField({
  label,
  name,
  onChange,
  options,
}: {
  label: string;
  name: string;
  onChange?: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select defaultValue={options[0]} name={name} onChange={(event) => onChange?.(event.target.value)}>
        {options.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
      </select>
    </label>
  );
}

function TextAreaField({
  label,
  name,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  name: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  value?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea name={name} onChange={onChange ? (event) => onChange(event.target.value) : undefined} placeholder={placeholder} rows={3} value={value} />
    </label>
  );
}
