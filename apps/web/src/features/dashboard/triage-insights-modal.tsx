"use client";

import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import { DrawerHeader, SectionTitle, DetailRow } from "@/features/dashboard/dashboard";

interface TriageInsightsModalProps {
  runId: number;
  onClose: () => void;
}

export function TriageInsightsModal({ runId, onClose }: TriageInsightsModalProps) {
  const { data: insights, isLoading, error } = useQuery({
    queryKey: ["triage-insights", runId],
    queryFn: () => api.getTriageRunInsights(runId),
  });

  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <aside
        aria-label="Triage insights"
        aria-modal="true"
        className="detail-drawer"
        role="dialog"
        style={{ maxWidth: '700px' }}
      >
        <DrawerHeader
          eyebrow="TRIAGE INSIGHTS"
          title={`Run #${runId}`}
          subtitle={insights ? new Date(insights.evaluated_on).toLocaleDateString() : 'Loading...'}
          onClose={onClose}
        />
        <div className="drawer-content">
          {isLoading && (
            <div className="loading-state">
              <span className="spinner" /> Loading insights…
            </div>
          )}

          {error && (
            <div className="feedback-banner error-banner" role="alert">
              <Icon name="warning" />
              <span>{error instanceof Error ? error.message : "Unknown error"}</span>
            </div>
          )}

          {insights && (
            <div className="detail-section">
              <SectionTitle title="Summary" />
              <DetailRow label="Total recommendations" value={insights.total_recommendations.toString()} />
              <DetailRow label="Evaluated on" value={new Date(insights.evaluated_on).toLocaleDateString()} />
            </div>
          )}

          {insights && (
            <div className="detail-section">
              <SectionTitle title="Risk Distribution" />
              {Object.entries(insights.summary.risk_distribution).map(([risk, count]) => (
                <DetailRow 
                  key={risk} 
                  label={risk.replace('_', ' ')} 
                  value={count.toString()} 
                />
              ))}
            </div>
          )}

          {insights && (
            <div className="detail-section">
              <SectionTitle title="Condition Distribution" />
              {Object.entries(insights.summary.condition_distribution).map(([condition, count]) => (
                <DetailRow 
                  key={condition} 
                  label={condition} 
                  value={count.toString()} 
                />
              ))}
            </div>
          )}

          {insights && Object.entries(insights.assets_by_condition).map(([condition, assets]) => (
            assets.length > 0 && (
              <div key={condition} className="detail-section">
                <SectionTitle title={`${condition} Condition (${assets.length})`} />
                <div className="flex flex-wrap gap-2">
                  {assets.map((assetCode) => (
                    <span
                      key={assetCode}
                      className="condition-badge condition-unknown"
                    >
                      {assetCode}
                    </span>
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
        <div className="drawer-footer">
          <button
            className="button button-secondary full-width"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>
      </aside>
    </div>
  );
}
