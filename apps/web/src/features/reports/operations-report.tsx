"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import type { OperationsReport } from "@/lib/api/types";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Could not load the operations report.";
}

const metrics: {
  label: string;
  value: (report: OperationsReport) => number | string;
  note: (report: OperationsReport) => string;
}[] = [
  { label: "Registered assets", value: (report) => report.total_assets, note: () => "Active and inactive" },
  { label: "Active assets", value: (report) => report.active_assets, note: () => "Included in triage" },
  { label: "Assets with unknown condition", value: (report) => report.condition_unknown_assets, note: () => "Condition not recorded" },
  { label: "Service overdue", value: (report) => report.overdue_service_assets, note: () => "Based on recorded due dates" },
  { label: "Inspections recorded", value: (report) => report.inspection_records, note: () => "All-time records" },
  { label: "Maintenance records", value: (report) => report.maintenance_records, note: () => "All-time records" },
  { label: "Unplanned maintenance", value: (report) => report.unplanned_maintenance_records, note: () => "Recorded as unplanned" },
  { label: "Recorded downtime", value: (report) => `${report.downtime_hours_recorded} h`, note: (report) => `${report.maintenance_records_without_downtime} records have no duration` },
];

export function OperationsReportView() {
  const [report, setReport] = useState<OperationsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getOperationsReport()
      .then((value) => {
        if (!cancelled) setReport(value);
      })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(errorMessage(requestError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
          <span className="eyebrow">DATA READINESS & OPERATIONS</span>
          <h1>Data quality and reports</h1>
          <p className="page-subtitle">
            Coverage and recorded activity from the current asset register. This is a descriptive
            report, not a predictive performance score.
          </p>
        </div>
        <span className="report-as-of">
          {report ? `As of ${report.generated_on}` : "Current register"}
        </span>
      </div>

      {error && (
        <div className="feedback-banner error-banner" role="alert">
          <Icon name="warning" />
          <span>{error}</span>
        </div>
      )}

      {loading && <div className="loading-state"><span className="spinner" />Loading report…</div>}
      {!loading && !report && !error && (
        <div className="empty-state"><strong>No report available.</strong></div>
      )}
      {report && (
        <>
          <div className="metric-grid operations-metric-grid">
            {metrics.map((metric) => (
              <article className="metric-card" key={metric.label}>
                <div className="metric-top">{metric.label}</div>
                <strong className="metric-value">{metric.value(report)}</strong>
                <span className="metric-foot neutral">{metric.note(report)}</span>
              </article>
            ))}
          </div>

          <div className="operations-report-columns">
            <section className="panel">
              <header className="panel-heading">
                <div>
                  <h2>Asset register coverage</h2>
                  <p>Missing data is reported as missing, never treated as a healthy asset.</p>
                </div>
              </header>
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
              <header className="panel-heading">
                <div>
                  <h2>Rule-based risk overview</h2>
                  <p>Active assets only; rules do not predict a mechanical failure.</p>
                </div>
              </header>
              <dl className="report-list">
                {Object.entries(report.risk_counts).map(([risk, count]) => (
                  <div key={risk}><dt>{risk.replaceAll("_", " ")}</dt><dd>{count}</dd></div>
                ))}
              </dl>
            </section>
          </div>

          <section className="panel report-gaps">
            <header className="panel-heading">
              <div>
                <h2>Not captured by the current application</h2>
                <p>These roadmap items need approved data definitions and access before implementation.</p>
              </div>
            </header>
            <div className="report-gap-tags">
              {report.untracked_domains.map((domain) => <span key={domain}>{domain}</span>)}
            </div>
          </section>

          <section className="panel report-exports">
            <header className="panel-heading">
              <div>
                <h2>Export current records</h2>
                <p>CSV exports are limited to 10,000 rows and escape spreadsheet formulas.</p>
              </div>
            </header>
            <div className="report-export-actions">
              {(["assets", "maintenance", "inspections"] as const).map((dataset) => (
                <button
                  className="button button-secondary"
                  disabled={Boolean(downloading)}
                  key={dataset}
                  onClick={() => void exportCsv(dataset)}
                  type="button"
                >
                  {downloading === dataset ? "Preparing…" : `Export ${dataset}`}
                </button>
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
