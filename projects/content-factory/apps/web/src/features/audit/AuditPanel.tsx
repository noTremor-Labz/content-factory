import { formatDateTime } from "../../shared/format";
import type { AuditLog } from "../../shared/api/types";

interface AuditPanelProps {
  auditLogs: AuditLog[];
  canView: boolean;
}

export function AuditPanel({ auditLogs, canView }: AuditPanelProps) {
  return (
    <section className="surface panel-stack">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Audit</p>
          <h2>Recent control-plane actions</h2>
        </div>
        <span className="count-pill">{auditLogs.length} entries</span>
      </div>

      {!canView ? (
        <p className="empty-state">Your current role cannot view the audit feed.</p>
      ) : auditLogs.length === 0 ? (
        <p className="empty-state">No audit entries yet.</p>
      ) : (
        <div className="list-stack">
          {auditLogs.map((auditLog) => (
            <article className="list-card" key={auditLog.id}>
              <div className="list-card-header">
                <h3>{auditLog.action}</h3>
                <span className="status-badge neutral">{auditLog.entity_type}</span>
              </div>
              <p>{auditLog.entity_id}</p>
              <p className="meta-copy">Logged {formatDateTime(auditLog.created_at)}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
