"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { api } from "@/lib/api/client";
import type {
  AssetAssessment,
  InstitutionAssessment,
  MaintenancePriority,
  RiskLevel,
  TriageAnalysis,
  TriageRun,
} from "@/lib/api/types";

type AssetSortKey =
  | "risk_score"
  | "asset_age_years"
  | "maintenance_count"
  | "replacement_score"
  | "maintenance_priority";
type InstitutionSortKey =
  | "priority_score"
  | "high_risk_ratio"
  | "critical_ratio"
  | "maintenance_frequency"
  | "replacement_candidates"
  | "average_age_years";
type BreakdownKind = "assets" | "high" | "maintenance" | "replacement";

const PRIORITY_WEIGHT: Record<MaintenancePriority, number> = {
  urgent: 5,
  high: 4,
  medium: 3,
  low: 2,
  monitor: 1,
};

const RISK_TONE: Record<RiskLevel, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  insufficient_data: "insufficient_data",
};

const PRIORITY_TONE: Record<MaintenancePriority, string> = {
  urgent: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  monitor: "insufficient_data",
};

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatNumber(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatYears(value: number | null) {
  return value === null ? "—" : `${value.toFixed(1)} yrs`;
}

function formatDays(value: number | null) {
  if (value === null) return "No history";
  if (value <= 0) return "Today";
  return `${value} days ago`;
}

function displayDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={`risk-badge risk-${RISK_TONE[level]}`}>
      <span />
      {titleCase(level)}
    </span>
  );
}

function PriorityBadge({ level }: { level: MaintenancePriority }) {
  return (
    <span className={`risk-badge risk-${PRIORITY_TONE[level]}`}>
      <span />
      {titleCase(level)}
    </span>
  );
}

function MetricCard({
  accent,
  foot,
  icon,
  label,
  onOpenBreakdown,
  value,
}: {
  accent: string;
  foot?: string;
  icon: IconName;
  label: string;
  onOpenBreakdown?: () => void;
  value: string;
}) {
  return (
    <article
      className={`metric-card ${onOpenBreakdown ? "metric-card-clickable" : ""}`}
      onClick={onOpenBreakdown}
      onKeyDown={
        onOpenBreakdown
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onOpenBreakdown();
              }
            }
          : undefined
      }
      role={onOpenBreakdown ? "button" : undefined}
      tabIndex={onOpenBreakdown ? 0 : undefined}
      title={onOpenBreakdown ? "View breakdown" : undefined}
    >
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${accent}`}>
          <Icon name={icon} />
        </span>
      </div>
      <strong className="metric-value">{value}</strong>
      {foot && <span className="metric-foot neutral">{foot}</span>}
      {onOpenBreakdown && <span className="metric-hint">View breakdown →</span>}
    </article>
  );
}

function DistributionBar({ label, count, total, tone }: { label: string; count: number; total: number; tone: string }) {
  const percent = total ? Math.round((count / total) * 100) : 0;
  return (
    <div className="dist-row">
      <span className="dist-label">{label}</span>
      <span className="dist-track">
        <span className={`dist-fill dist-${tone}`} style={{ width: `${percent}%` }} />
      </span>
      <span className="dist-value">
        {count} · {percent}%
      </span>
    </div>
  );
}

function SortHeader<T extends string>({
  active,
  label,
  sortKey,
  onSort,
}: {
  active: { key: T; direction: "asc" | "desc" };
  label: string;
  sortKey: T;
  onSort: (key: T) => void;
}) {
  const isActive = active.key === sortKey;
  return (
    <th aria-sort={isActive ? (active.direction === "asc" ? "ascending" : "descending") : "none"}>
      <button className="sort-header" onClick={() => onSort(sortKey)} type="button">
        {label}
        <span className="sort-indicator">{isActive ? (active.direction === "asc" ? "▲" : "▼") : "↕"}</span>
      </button>
    </th>
  );
}

function useRowLimit(initial = 5, step = 5) {
  const [limit, setLimit] = useState(initial);
  return {
    limit,
    step,
    more: () => setLimit((current) => current + step),
    all: (total: number) => setLimit(total),
    reset: () => setLimit(initial),
  };
}

function TablePager({
  pager,
  total,
}: {
  pager: ReturnType<typeof useRowLimit>;
  total: number;
}) {
  const remaining = total - pager.limit;
  return (
    <div className="table-pager">
      <span className="table-pager-count">
        Showing {Math.min(pager.limit, total)} of {total}
      </span>
      <div className="table-pager-actions">
        {remaining > 0 ? (
          <>
            <button className="button button-secondary" onClick={pager.more} type="button">
              Show {Math.min(pager.step, remaining)} more
            </button>
            <button
              className="button button-secondary"
              onClick={() => pager.all(total)}
              type="button"
            >
              Full list
            </button>
          </>
        ) : (
          pager.limit > pager.step && (
            <button className="button button-secondary" onClick={pager.reset} type="button">
              Show less
            </button>
          )
        )}
      </div>
    </div>
  );
}

export function MaintenanceTriage({
  canRunTriage,
  scopeName,
}: {
  canRunTriage: boolean;
  scopeName: string;
}) {
  const [analysis, setAnalysis] = useState<TriageAnalysis | null>(null);
  const [runs, setRuns] = useState<TriageRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<AssetAssessment | null>(null);
  const [assetSort, setAssetSort] = useState<{ key: AssetSortKey; direction: "asc" | "desc" }>({
    key: "risk_score",
    direction: "desc",
  });
  const [institutionSort, setInstitutionSort] = useState<{
    key: InstitutionSortKey;
    direction: "asc" | "desc";
  }>({ key: "priority_score", direction: "desc" });
  const [breakdown, setBreakdown] = useState<BreakdownKind | null>(null);
  const [runLimit, setRunLimit] = useState(5);
  const institutionPager = useRowLimit();
  const assetPager = useRowLimit();
  const replacementPager = useRowLimit();

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [preview, runList] = await Promise.all([
        api.getTriageAnalysis(),
        api.listTriageRuns(),
      ]);
      setAnalysis(preview);
      setRuns(runList);
      setActiveRunId(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load the analysis.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const runList = await api.listTriageRuns();
        if (cancelled) return;
        setRuns(runList);
        if (runList.length > 0) {
          // Open the newest saved snapshot instead of recomputing a live
          // analysis on page open; "Run Triage" performs the full analysis.
          const saved = await api.getTriageRunAnalysis(runList[0].id);
          if (cancelled) return;
          setAnalysis(saved);
          setActiveRunId(runList[0].id);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Could not load the analysis.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function runTriage() {
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const preview = await api.getTriageAnalysis();
      setAnalysis(preview);
      setActiveRunId(null);
      setNotice(
        `Triage completed — ${preview.summary.total_assets} assets across ${preview.summary.total_institutions} institutions analyzed.`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Could not run the triage analysis.");
    } finally {
      setBusy(false);
    }
  }

  async function saveTriageRun() {
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const run = await api.createTriageRun();
      const [saved, runList] = await Promise.all([
        api.getTriageRunAnalysis(run.id),
        api.listTriageRuns(),
      ]);
      setAnalysis(saved);
      setRuns(runList);
      setActiveRunId(run.id);
      setNotice(`Saved triage run #${run.id} — a reproducible snapshot of ${run.total_assets} assets.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save the triage run.");
    } finally {
      setBusy(false);
    }
  }

  async function openRun(runId: number) {
    setBusy(true);
    setError("");
    try {
      const saved = await api.getTriageRunAnalysis(runId);
      setAnalysis(saved);
      setActiveRunId(runId);
      setNotice("");
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "Could not open the saved run.");
    } finally {
      setBusy(false);
    }
  }

  function sortAssets(key: AssetSortKey) {
    setAssetSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "desc" ? "asc" : "desc" }
        : { key, direction: "desc" },
    );
  }

  function sortInstitutions(key: InstitutionSortKey) {
    setInstitutionSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "desc" ? "asc" : "desc" }
        : { key, direction: "desc" },
    );
  }

  const sortedAssets = useMemo(() => {
    if (!analysis) return [];
    const value = (asset: AssetAssessment): number => {
      switch (assetSort.key) {
        case "asset_age_years":
          return asset.asset_age_years ?? -1;
        case "maintenance_count":
          return asset.maintenance_count;
        case "replacement_score":
          return asset.replacement_score;
        case "maintenance_priority":
          return PRIORITY_WEIGHT[asset.maintenance_priority];
        default:
          return asset.risk_score ?? -1;
      }
    };
    return [...analysis.assets].sort((a, b) =>
      assetSort.direction === "desc" ? value(b) - value(a) : value(a) - value(b),
    );
  }, [analysis, assetSort]);

  const sortedInstitutions = useMemo(() => {
    if (!analysis) return [];
    const value = (row: InstitutionAssessment): number => {
      switch (institutionSort.key) {
        case "high_risk_ratio":
          return row.high_risk_ratio;
        case "critical_ratio":
          return row.critical_ratio;
        case "maintenance_frequency":
          return row.maintenance_frequency ?? -1;
        case "replacement_candidates":
          return row.replacement_candidates;
        case "average_age_years":
          return row.average_age_years ?? -1;
        default:
          return row.priority_score;
      }
    };
    return [...analysis.institutions].sort((a, b) =>
      institutionSort.direction === "desc" ? value(b) - value(a) : value(a) - value(b),
    );
  }, [analysis, institutionSort]);

  const replacementRanked = useMemo(() => {
    if (!analysis) return [];
    return [...analysis.assets].sort((a, b) => b.replacement_score - a.replacement_score);
  }, [analysis]);

  const summary = analysis?.summary;
  const distributionTotal = summary
    ? summary.low_risk_assets +
      summary.medium_risk_assets +
      summary.high_risk_assets +
      summary.critical_assets
    : 0;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">PREDICTIVE MAINTENANCE</div>
          <h1>Maintenance Triage</h1>
          <p className="page-subtitle">
            Deterministic, evidence-based analysis of historical maintenance records for{" "}
            {analysis?.scope_name ?? scopeName}.
          </p>
        </div>
        <div className="heading-actions">
          <button
            className="button button-secondary"
            disabled={busy || loading}
            onClick={() => void runTriage()}
            type="button"
          >
            <Icon name="refresh" /> {busy ? "Analyzing…" : "Run Triage"}
          </button>
          {canRunTriage && (
            <button
              className="button button-primary"
              disabled={busy || loading || !analysis || analysis.summary.total_assets === 0}
              onClick={() => void saveTriageRun()}
              type="button"
            >
              <Icon name="check" /> Save Triage Run
            </button>
          )}
        </div>
      </section>

      <section className="insight-banner">
        <div className="insight-icon">
          <Icon name="activity" />
        </div>
        <div className="insight-copy">
          <strong>Data-driven analysis. No AI required.</strong>
          <p>
            AI assistant unavailable. Showing data-driven analysis from historical maintenance
            records — every score is deterministic, explainable, and reproducible.
          </p>
        </div>
        <span className="rule-version">{analysis?.engine_version ?? "risk engine"}</span>
      </section>

      {error && (
        <div className="feedback-banner error-banner" role="alert">
          <Icon name="warning" />
          <span>{error}</span>
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

      {loading ? (
        <div className="loading-state">
          <span className="spinner" /> Analyzing historical maintenance records…
        </div>
      ) : runs.length === 0 && !analysis ? (
        <section className="panel">
          <div className="empty-state">
            <span className="empty-icon">
              <Icon name="activity" />
            </span>
            <h2>No triage runs yet</h2>
            <span>
              Nothing is computed until you ask. Run your first deterministic analysis to score
              every asset and rank institution maintenance priority.
            </span>
            <button
              className="button button-primary"
              onClick={() => void runTriage()}
              type="button"
            >
              <Icon name="refresh" /> Run full analysis
            </button>
          </div>
        </section>
      ) : !summary || summary.total_assets === 0 ? (
        <section className="panel">
          <div className="empty-state">
            <span className="empty-icon">
              <Icon name="assets" />
            </span>
            <h2>Insufficient historical maintenance data</h2>
            <span>
              Data required for predictive analysis:
              <br />• Maintenance history • Vehicle age • Inspection records • Usage information
            </span>
          </div>
        </section>
      ) : (
        <>
          <section aria-label="Asset health summary" className="metric-grid">
            <MetricCard
              accent="navy"
              foot={`${summary.total_institutions} institutions · ${summary.assets_with_maintenance_history} with history`}
              icon="assets"
              label="Assets analyzed"
              onOpenBreakdown={() => setBreakdown("assets")}
              value={formatNumber(summary.total_assets)}
            />
            <MetricCard
              accent="red"
              foot={`${summary.critical_assets} critical · ${summary.high_risk_assets - summary.critical_assets} high`}
              icon="warning"
              label="High risk"
              onOpenBreakdown={() => setBreakdown("high")}
              value={formatNumber(summary.high_risk_assets)}
            />
            <MetricCard
              accent="amber"
              foot="Prioritized for maintenance action"
              icon="maintenance"
              label="Maintenance candidates"
              onOpenBreakdown={() => setBreakdown("maintenance")}
              value={formatNumber(summary.maintenance_candidates)}
            />
            <MetricCard
              accent="green"
              foot={`${summary.maintenance_events} maintenance events analyzed`}
              icon="recommendations"
              label="Replacement candidates"
              onOpenBreakdown={() => setBreakdown("replacement")}
              value={formatNumber(summary.replacement_candidates)}
            />
          </section>

          <div className="triage-columns">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Maintenance risk distribution</h2>
                  <p>Assets by deterministic risk band.</p>
                </div>
              </div>
              <div className="dist-panel">
                <DistributionBar
                  count={summary.critical_assets}
                  label="CRITICAL"
                  tone="critical"
                  total={distributionTotal}
                />
                <DistributionBar
                  count={summary.high_risk_assets - summary.critical_assets}
                  label="HIGH"
                  tone="high"
                  total={distributionTotal}
                />
                <DistributionBar
                  count={summary.medium_risk_assets}
                  label="MEDIUM"
                  tone="medium"
                  total={distributionTotal}
                />
                <DistributionBar
                  count={summary.low_risk_assets}
                  label="LOW"
                  tone="low"
                  total={distributionTotal}
                />
                {summary.insufficient_data_assets > 0 && (
                  <p className="dist-note">
                    {summary.insufficient_data_assets} asset(s) have insufficient data to score.
                  </p>
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Triage run history</h2>
                  <p>Reproducible analytical snapshots.</p>
                </div>
              </div>
              <div className="run-history">
                {activeRunId === null && (
                  <button className="run-history-item active" type="button" onClick={() => void loadPreview()}>
                    <strong>Live analysis</strong>
                    <small>Not saved — run triage and save to persist a snapshot.</small>
                  </button>
                )}
                {runs.length === 0 && (
                  <p className="dist-note">No saved triage runs yet.</p>
                )}
                {runs.slice(0, runLimit).map((run) => (
                  <button
                    className={`run-history-item ${activeRunId === run.id ? "active" : ""}`}
                    key={run.id}
                    onClick={() => void openRun(run.id)}
                    type="button"
                  >
                    <strong>Run #{run.id} · {displayDate(run.evaluated_on)}</strong>
                    <small>
                      {run.total_assets ?? run.recommendation_count} assets · {run.high_risk_assets ?? 0}{" "}
                      high-risk · {run.replacement_candidates ?? 0} replacement
                    </small>
                  </button>
                ))}
                {runs.length > runLimit && (
                  <button
                    className="button button-secondary run-history-more"
                    onClick={() => setRunLimit((current) => current + 5)}
                    type="button"
                  >
                    Show more · {runs.length - runLimit} older run
                    {runs.length - runLimit === 1 ? "" : "s"}
                  </button>
                )}
              </div>
            </section>
          </div>

          {summary.data_quality_notes.length > 0 && (
            <section className="panel analytics-quality-panel">
              <div className="panel-heading">
                <div>
                  <h2>Data quality</h2>
                  <p>Analysis continues using valid records; these gaps are disclosed for transparency.</p>
                </div>
              </div>
              <ul className="analytics-note-list">
                {summary.data_quality_notes.map((note) => (
                  <li key={note}>
                    <Icon name="warning" />
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="panel analytics-comparison-panel">
            <div className="panel-heading">
              <div>
                <h2>Maintenance Priority Analysis</h2>
                <p>
                  Institutions compared using normalized indicators (high-risk ratio, critical ratio,
                  maintenance frequency, replacement ratio) — not raw fleet size.
                </p>
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-table analytics-table">
                <thead>
                  <tr>
                    <th>Institution</th>
                    <th>Assets</th>
                    <SortHeader
                      active={institutionSort}
                      label="High risk"
                      onSort={sortInstitutions}
                      sortKey="high_risk_ratio"
                    />
                    <SortHeader
                      active={institutionSort}
                      label="Critical"
                      onSort={sortInstitutions}
                      sortKey="critical_ratio"
                    />
                    <SortHeader
                      active={institutionSort}
                      label="Frequency"
                      onSort={sortInstitutions}
                      sortKey="maintenance_frequency"
                    />
                    <SortHeader
                      active={institutionSort}
                      label="Replacement"
                      onSort={sortInstitutions}
                      sortKey="replacement_candidates"
                    />
                    <SortHeader
                      active={institutionSort}
                      label="Avg age"
                      onSort={sortInstitutions}
                      sortKey="average_age_years"
                    />
                    <SortHeader
                      active={institutionSort}
                      label="Priority"
                      onSort={sortInstitutions}
                      sortKey="priority_score"
                    />
                  </tr>
                </thead>
                <tbody>
                  {sortedInstitutions.slice(0, institutionPager.limit).map((row) => (
                    <tr key={row.institution_id ?? "unassigned"}>
                      <td>
                        <div className="analytics-rank-cell">
                          <span className="analytics-rank">{row.priority_score}</span>
                          <span>
                            <strong>{row.institution_name}</strong>
                            <small>{row.reasons[0] ?? ""}</small>
                          </span>
                        </div>
                      </td>
                      <td>{row.total_assets}</td>
                      <td>
                        {row.high_risk_assets} · {Math.round(row.high_risk_ratio * 100)}%
                      </td>
                      <td>
                        {row.critical_assets} · {Math.round(row.critical_ratio * 100)}%
                      </td>
                      <td className="muted-cell">
                        {row.maintenance_frequency === null ? "—" : `${row.maintenance_frequency.toFixed(2)}/yr`}
                      </td>
                      <td>{row.replacement_candidates}</td>
                      <td className="muted-cell">{formatYears(row.average_age_years)}</td>
                      <td>
                        <PriorityBadge level={row.priority_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <TablePager pager={institutionPager} total={sortedInstitutions.length} />
          </section>

          <section className="panel analytics-comparison-panel">
            <div className="panel-heading">
              <div>
                <h2>Vehicle maintenance risk</h2>
                <p>Every asset scored from age, maintenance frequency, recency, condition, and downtime.</p>
              </div>
              <span className="count-pill">{sortedAssets.length}</span>
            </div>
            <div className="table-scroll">
              <table className="data-table analytics-table">
                <thead>
                  <tr>
                    <th>Vehicle</th>
                    <th>Institution</th>
                    <SortHeader active={assetSort} label="Age" onSort={sortAssets} sortKey="asset_age_years" />
                    <SortHeader
                      active={assetSort}
                      label="Events"
                      onSort={sortAssets}
                      sortKey="maintenance_count"
                    />
                    <th>Last maintenance</th>
                    <SortHeader active={assetSort} label="Risk" onSort={sortAssets} sortKey="risk_score" />
                    <SortHeader
                      active={assetSort}
                      label="Replacement"
                      onSort={sortAssets}
                      sortKey="replacement_score"
                    />
                    <SortHeader
                      active={assetSort}
                      label="Priority"
                      onSort={sortAssets}
                      sortKey="maintenance_priority"
                    />
                  </tr>
                </thead>
                <tbody>
                  {sortedAssets.slice(0, assetPager.limit).map((asset) => (
                    <tr className="clickable-row" key={asset.asset_id} onClick={() => setSelected(asset)}>
                      <td>
                        <div className="asset-cell">
                          <span className="asset-avatar">
                            {asset.asset_type.slice(0, 1).toUpperCase()}
                          </span>
                          <span className="asset-link">
                            <strong>{asset.asset_code}</strong>
                            <small>
                              {[asset.make, asset.model].filter(Boolean).join(" ") ||
                                titleCase(asset.asset_type)}
                            </small>
                          </span>
                        </div>
                      </td>
                      <td className="muted-cell">{asset.institution_name ?? "Unassigned"}</td>
                      <td className="muted-cell">{formatYears(asset.asset_age_years)}</td>
                      <td>{asset.maintenance_count}</td>
                      <td className="muted-cell">{formatDays(asset.days_since_last_maintenance)}</td>
                      <td>
                        <span className="score-cell">
                          <strong>{asset.risk_score ?? "—"}</strong>
                          <RiskBadge level={asset.risk_level} />
                        </span>
                      </td>
                      <td>
                        <span className="score-cell">
                          <strong>{asset.replacement_score}</strong>
                          {asset.replacement_candidate && <span className="flag-pill">Candidate</span>}
                        </span>
                      </td>
                      <td>
                        <PriorityBadge level={asset.maintenance_priority} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <TablePager pager={assetPager} total={sortedAssets.length} />
          </section>

          <section className="panel analytics-comparison-panel">
            <div className="panel-heading">
              <div>
                <h2>Replacement consideration</h2>
                <p>
                  {summary.replacement_candidates > 0
                    ? "Assets exceeding the replacement threshold, ranked by combined score."
                    : "No asset currently exceeds the replacement threshold. Highest-consideration assets are shown for planning."}
                </p>
              </div>
              <span className="count-pill">{summary.replacement_candidates}</span>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Vehicle</th>
                    <th>Age</th>
                    <th>Events</th>
                    <th>Frequency</th>
                    <th>Consideration</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {replacementRanked.slice(0, replacementPager.limit).map((asset) => (
                    <tr className="clickable-row" key={asset.asset_id} onClick={() => setSelected(asset)}>
                      <td>
                        <strong>{asset.asset_code}</strong>
                        <small className="muted-cell"> {asset.institution_name ?? "Unassigned"}</small>
                      </td>
                      <td className="muted-cell">{formatYears(asset.asset_age_years)}</td>
                      <td>{asset.maintenance_count}</td>
                      <td className="muted-cell">
                        {asset.maintenance_frequency === null
                          ? "—"
                          : `${asset.maintenance_frequency.toFixed(2)}/yr`}
                      </td>
                      <td>
                        <strong>{asset.replacement_score}</strong> / 100
                      </td>
                      <td>
                        {asset.replacement_candidate ? (
                          <span className="flag-pill">Replacement candidate</span>
                        ) : (
                          <span className="muted-cell">Monitor</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <TablePager pager={replacementPager} total={replacementRanked.length} />
          </section>
        </>
      )}

      {breakdown && analysis && (
        <BreakdownModal
          analysis={analysis}
          kind={breakdown}
          onClose={() => setBreakdown(null)}
          onSelectAsset={(asset) => {
            setBreakdown(null);
            setSelected(asset);
          }}
        />
      )}
      {selected && <AssetAnalysisModal asset={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function BreakdownModal({
  analysis,
  kind,
  onClose,
  onSelectAsset,
}: {
  analysis: TriageAnalysis;
  kind: BreakdownKind;
  onClose: () => void;
  onSelectAsset: (asset: AssetAssessment) => void;
}) {
  const titles: Record<BreakdownKind, string> = {
    assets: "Assets analyzed — by institution",
    high: "High-risk assets (high + critical)",
    maintenance: "Maintenance candidates",
    replacement: "Replacement candidates",
  };
  const subtitles: Record<BreakdownKind, string> = {
    assets: "Every institution in scope and how many assets it contributes.",
    high: "Assets scoring in the high or critical risk band. Select one for full detail.",
    maintenance: "Assets whose maintenance priority is urgent, high, or medium.",
    replacement: "Assets exceeding the replacement threshold. Select one for full detail.",
  };

  const assetRows =
    kind === "high"
      ? analysis.assets
          .filter((asset) => asset.risk_level === "high" || asset.risk_level === "critical")
          .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
      : kind === "maintenance"
        ? analysis.assets
            .filter(
              (asset) =>
                asset.maintenance_priority === "urgent" ||
                asset.maintenance_priority === "high" ||
                asset.maintenance_priority === "medium",
            )
            .sort(
              (a, b) => PRIORITY_WEIGHT[b.maintenance_priority] - PRIORITY_WEIGHT[a.maintenance_priority],
            )
        : kind === "replacement"
          ? [...analysis.assets]
              .sort((a, b) => b.replacement_score - a.replacement_score)
              .filter((asset) => asset.replacement_candidate)
          : [];

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-card analytics-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={titles[kind]}
      >
        <div className="modal-heading">
          <div>
            <div className="eyebrow">Breakdown</div>
            <h2>{titles[kind]}</h2>
            <p className="page-subtitle">{subtitles[kind]}</p>
          </div>
          <button aria-label="Close" className="icon-button" onClick={onClose} type="button">
            <Icon name="close" />
          </button>
        </div>

        {kind === "assets" ? (
          <ul className="breakdown-list">
            {analysis.institutions.map((row) => (
              <li className="breakdown-row" key={row.institution_id ?? "unassigned"}>
                <span className="breakdown-label">
                  <strong>{row.institution_name}</strong>
                  <small>
                    {row.total_assets} assets · {row.high_risk_assets} high-risk
                  </small>
                </span>
                <span className="breakdown-value">{row.total_assets}</span>
              </li>
            ))}
          </ul>
        ) : assetRows.length === 0 ? (
          <p className="dist-note breakdown-empty">
            {kind === "replacement"
              ? "No asset currently exceeds the replacement threshold."
              : "No assets in this category."}
          </p>
        ) : (
          <ul className="breakdown-list">
            {assetRows.map((asset) => (
              <li key={asset.asset_id}>
                <button
                  className="breakdown-row"
                  onClick={() => onSelectAsset(asset)}
                  type="button"
                >
                  <span className="breakdown-label">
                    <strong>{asset.asset_code}</strong>
                    <small>{asset.institution_name ?? "Unassigned"}</small>
                  </span>
                  <span className="breakdown-value">
                    {kind === "high" && (
                      <>
                        <strong>{asset.risk_score ?? "—"}</strong>
                        <RiskBadge level={asset.risk_level} />
                      </>
                    )}
                    {kind === "maintenance" && <PriorityBadge level={asset.maintenance_priority} />}
                    {kind === "replacement" && <strong>{asset.replacement_score}</strong>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function AssetAnalysisModal({ asset, onClose }: { asset: AssetAssessment; onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-card analytics-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`Analysis for ${asset.asset_code}`}
      >
        <div className="modal-heading">
          <div>
            <div className="eyebrow">{asset.institution_name ?? "Unassigned"}</div>
            <h2>{asset.asset_code}</h2>
            <p className="page-subtitle">
              {[asset.make, asset.model].filter(Boolean).join(" ") || titleCase(asset.asset_type)}
              {asset.registration_number ? ` · ${asset.registration_number}` : ""}
            </p>
          </div>
          <button aria-label="Close" className="icon-button" onClick={onClose} type="button">
            <Icon name="close" />
          </button>
        </div>

        <div className="analytics-risk-strip">
          <RiskBadge level={asset.risk_level} />
          <span>
            Risk score <strong>{asset.risk_score ?? "—"}/100</strong> · Maintenance priority{" "}
            {titleCase(asset.maintenance_priority)} ({asset.priority_score}/100)
          </span>
          <strong>{asset.recommendation}</strong>
        </div>

        <div className="analytics-profile-summary">
          <article>
            <span>Age</span>
            <strong>{formatYears(asset.asset_age_years)}</strong>
            <small>From acquisition date</small>
          </article>
          <article>
            <span>Maintenance history</span>
            <strong>{asset.maintenance_count} events</strong>
            <small>
              {asset.maintenance_frequency === null
                ? "Frequency not calculable"
                : `${asset.maintenance_frequency.toFixed(2)} events/year`}
            </small>
          </article>
          <article>
            <span>Last maintenance</span>
            <strong>{formatDays(asset.days_since_last_maintenance)}</strong>
            <small>{asset.recent_repeat_count} events in last 90 days</small>
          </article>
          <article>
            <span>Replacement consideration</span>
            <strong>{asset.replacement_score}/100</strong>
            <small>{asset.replacement_candidate ? "Replacement candidate" : "Monitor"}</small>
          </article>
        </div>

        <div className="detail-section">
          <h3>Why this recommendation</h3>
          <ul className="analytics-note-list">
            {asset.reasons.map((reason) => (
              <li key={reason}>
                <Icon name="activity" />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="detail-section">
          <h3>Evidence</h3>
          <ul className="evidence-list">
            {asset.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        {Object.keys(asset.factor_scores).length > 0 && (
          <div className="detail-section">
            <h3>Contributing factors (normalized 0–100)</h3>
            <div className="factor-grid">
              {Object.entries(asset.factor_scores).map(([factor, score]) => (
                <div className="factor-row" key={factor}>
                  <span>{titleCase(factor)}</span>
                  <span className="dist-track">
                    <span className="dist-fill dist-medium" style={{ width: `${score}%` }} />
                  </span>
                  <strong>{score.toFixed(0)}</strong>
                </div>
              ))}
            </div>
          </div>
        )}

        {!asset.has_maintenance_history && (
          <p className="dist-note">
            Insufficient maintenance history — scoring reflects age and recorded condition only.
          </p>
        )}
      </div>
    </div>
  );
}
