"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import type { InstitutionTreeReport, OperationsReport } from "@/lib/api/types";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Could not load the operations report.";
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

const metrics: {
  label: string;
  value: (report: OperationsReport) => number | string;
  note: (report: OperationsReport) => string;
}[] = [
  { label: "Registered assets", value: (report) => report.total_assets, note: () => "Active and inactive" },
  { label: "Active assets", value: (report) => report.active_assets, note: () => "Included in triage" },
  { label: "Unknown condition", value: (report) => report.condition_unknown_assets, note: () => "Condition not recorded" },
  { label: "Service overdue", value: (report) => report.overdue_service_assets, note: () => "Based on recorded due dates" },
  { label: "Inspections", value: (report) => report.inspection_records, note: () => "All-time records" },
  { label: "Maintenance records", value: (report) => report.maintenance_records, note: () => "All-time records" },
  { label: "Unplanned maintenance", value: (report) => report.unplanned_maintenance_records, note: () => "Recorded as unplanned" },
  { label: "Recorded downtime", value: (report) => `${report.downtime_hours_recorded} h`, note: (report) => `${report.maintenance_records_without_downtime} records lack duration` },
];

export function OperationsReportView({ isAdmin }: { isAdmin: boolean }) {
  const [report, setReport] = useState<OperationsReport | null>(null);
  const [treeReport, setTreeReport] = useState<InstitutionTreeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [treeError, setTreeError] = useState("");
  const [downloading, setDownloading] = useState("");

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError("");
    setTreeError("");
    const [operationsResult, treeResult] = await Promise.allSettled([
      api.getOperationsReport(undefined, isAdmin),
      isAdmin ? api.getInstitutionTreeReport() : Promise.resolve(null),
    ]);
    if (operationsResult.status === "fulfilled") setReport(operationsResult.value);
    else setError(errorMessage(operationsResult.reason));
    if (treeResult.status === "fulfilled") setTreeReport(treeResult.value);
    else setTreeError(errorMessage(treeResult.reason));
    setLoading(false);
  }, [isAdmin]);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api.getOperationsReport(undefined, isAdmin),
      isAdmin ? api.getInstitutionTreeReport() : Promise.resolve(null),
    ]).then(([operationsResult, treeResult]) => {
      if (cancelled) return;
      if (operationsResult.status === "fulfilled") setReport(operationsResult.value);
      else setError(errorMessage(operationsResult.reason));
      if (treeResult.status === "fulfilled") setTreeReport(treeResult.value);
      else setTreeError(errorMessage(treeResult.reason));
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  async function exportCsv(dataset: "assets" | "maintenance" | "inspections") {
    setDownloading(dataset);
    setError("");
    try {
      await api.downloadCsv(dataset);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setDownloading("");
    }
  }

  return (
    <section className="operations-report">
      <div className="page-heading">
        <div>
          <span className="eyebrow">INSTITUTION REPORTING</span>
          <h1>Asset operations report</h1>
          <p className="page-subtitle">
            Actual register coverage and activity rolled up through the selected institution tree.
          </p>
        </div>
        <div className="report-heading-meta">
          <span className="report-as-of">{report ? `As of ${report.generated_on}` : "Current register"}</span>
          <button className="button button-secondary button-small" disabled={loading} onClick={() => void loadReport()} type="button"><Icon name="refresh" /> Refresh</button>
        </div>
      </div>

      {error && <div className="feedback-banner error-banner" role="alert"><Icon name="warning" /><span>{error}</span></div>}
      {loading && <div className="loading-state"><span className="spinner" />Loading institution report…</div>}
      {!loading && !report && !error && <div className="empty-state"><strong>No report available.</strong></div>}
      {report && (
        <>
          <section className="report-scope-banner">
            <div><span>Reporting scope</span><strong>{report.scope_name}</strong></div>
            <p>{report.included_institutions.toLocaleString()} {report.included_institutions === 1 ? "institution" : "institutions"} included in this roll-up.</p>
          </section>

          <div className="metric-grid operations-metric-grid">
            {metrics.map((metric) => (
              <article className="metric-card" key={metric.label}>
                <div className="metric-top">{metric.label}</div>
                <strong className="metric-value">{metric.value(report)}</strong>
                <span className="metric-foot neutral">{metric.note(report)}</span>
              </article>
            ))}
          </div>

          {isAdmin && treeReport && (
            <section className="panel institution-report-panel">
              <header className="panel-heading">
                <div><div className="panel-title-row"><h2>Institution tree performance</h2><span className="count-pill">{treeReport.root_count}</span></div><p>Ministries and local-government roots aggregate their descendants once; no assets are duplicated between rows.</p></div>
              </header>
              {treeReport.unassigned_assets > 0 && <div className="institution-report-warning"><Icon name="warning" /><span>{treeReport.unassigned_assets} legacy assets have no institution and appear only in the national total.</span></div>}
              {treeError && <div className="institution-report-warning"><Icon name="warning" /><span>{treeError}</span></div>}
              <div className="table-scroll">
                <table className="data-table institution-report-table">
                  <thead><tr><th>Reporting root</th><th>Tree size</th><th>Assets</th><th>Critical / high</th><th>Overdue service</th><th>Missing condition</th></tr></thead>
                  <tbody>
                    {treeReport.rows.map((row) => (
                      <tr key={row.institution.id}>
                        <td><div className="report-institution-cell"><span>{row.institution.short_name || row.institution.code}</span><div><strong>{row.institution.name}</strong><small>{titleCase(row.institution.institution_type)}</small></div></div></td>
                        <td>{row.descendant_count + 1}<small className="table-subvalue">{row.descendant_count} linked</small></td>
                        <td><strong>{row.report.total_assets}</strong><small className="table-subvalue">{row.report.active_assets} active</small></td>
                        <td>{row.report.risk_counts.critical + row.report.risk_counts.high}<small className="table-subvalue">{row.report.risk_counts.critical} critical</small></td>
                        <td>{row.report.overdue_service_assets}</td>
                        <td>{row.report.condition_unknown_assets}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="operations-report-columns">
            <section className="panel">
              <header className="panel-heading"><div><h2>Asset register coverage</h2><p>Missing data is reported as missing, never treated as a healthy asset.</p></div></header>
              <dl className="report-list">
                <div><dt>Missing acquisition date</dt><dd>{report.missing_acquisition_date}</dd></div>
                <div><dt>Never inspected / no inspection date</dt><dd>{report.missing_inspection_date}</dd></div>
                <div><dt>No scheduled-service date</dt><dd>{report.missing_service_schedule}</dd></div>
                <div><dt>Service due now or overdue</dt><dd>{report.service_due_assets}</dd></div>
                <div><dt>Service dates out of order</dt><dd>{report.inconsistent_service_dates}</dd></div>
                <div><dt>Assets with maintenance history</dt><dd>{report.assets_with_maintenance_history}</dd></div>
                <div><dt>Assets with a recorded condition</dt><dd>{report.condition_recorded_assets}</dd></div>
                <div><dt>Planned maintenance records</dt><dd>{report.planned_maintenance_records}</dd></div>
              </dl>
            </section>

            <section className="panel">
              <header className="panel-heading"><div><h2>Rule-based risk overview</h2><p>Active assets only; rules do not predict a mechanical failure.</p></div></header>
              <dl className="report-list">
                {Object.entries(report.risk_counts).map(([risk, count]) => <div key={risk}><dt>{risk.replaceAll("_", " ")}</dt><dd>{count}</dd></div>)}
              </dl>
            </section>
          </div>

          <section className="panel report-gaps">
            <header className="panel-heading"><div><h2>Not captured by the current application</h2><p>These domains need approved definitions and source-system access before implementation.</p></div></header>
            <div className="report-gap-tags">{report.untracked_domains.map((domain) => <span key={domain}>{domain}</span>)}</div>
          </section>

          <section className="panel report-exports">
            <header className="panel-heading"><div><h2>Export current institution records</h2><p>CSV exports follow the active institution selection, are limited to 10,000 rows, and escape spreadsheet formulas.</p></div></header>
            <div className="report-export-actions">{(["assets", "maintenance", "inspections"] as const).map((dataset) => <button className="button button-secondary" disabled={Boolean(downloading)} key={dataset} onClick={() => void exportCsv(dataset)} type="button">{downloading === dataset ? "Preparing…" : `Export ${dataset}`}</button>)}</div>
          </section>
        </>
      )}
    </section>
  );
}
