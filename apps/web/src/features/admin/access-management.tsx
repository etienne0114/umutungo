"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import type { AdminUser } from "@/lib/api/types";

function message(error: unknown) {
  return error instanceof Error ? error.message : "Could not load account access.";
}

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function AccessManagement({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setUsers(await api.listAdminUsers());
    } catch (loadError) {
      setError(message(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.listAdminUsers()
      .then((nextUsers) => {
        if (!cancelled) setUsers(nextUsers);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(message(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function setAccess(user: AdminUser, approved: boolean) {
    setBusyUserId(user.id);
    setError("");
    setNotice("");
    try {
      const updated = await api.setUserAccess(user.id, approved);
      setUsers((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
      setNotice(`${updated.email ?? "User"} access ${approved ? "approved" : "revoked"}.`);
    } catch (updateError) {
      setError(message(updateError));
    } finally {
      setBusyUserId("");
    }
  }

  const pendingCount = users.filter((user) => user.access === "pending").length;

  return (
    <section className="access-management">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ADMINISTRATION</div>
          <h1>User access</h1>
          <p>Review registered accounts and explicitly approve API access.</p>
        </div>
        <button className="button button-secondary" disabled={loading} onClick={() => void loadUsers()} type="button">
          <Icon name="refresh" />
          Refresh
        </button>
      </div>

      {error && <div className="feedback-banner error-banner" role="alert"><Icon name="warning" /><span>{error}</span></div>}
      {notice && <div className="feedback-banner success-banner" role="status"><Icon name="check" /><span>{notice}</span></div>}

      <div className="access-summary">
        <div className="panel access-summary-card">
          <span>Registered accounts</span>
          <strong>{users.length}</strong>
        </div>
        <div className="panel access-summary-card">
          <span>Awaiting approval</span>
          <strong>{pendingCount}</strong>
        </div>
      </div>

      <section className="panel access-users-panel">
        <div className="panel-heading">
          <div>
            <h2>Registered users</h2>
            <p>Only verified administrator claims can change access.</p>
          </div>
        </div>
        {loading ? (
          <div className="loading-state"><span className="spinner" /> Loading accounts…</div>
        ) : users.length === 0 ? (
          <div className="empty-state"><strong>No registered accounts</strong><p>Accounts appear here after registration.</p></div>
        ) : (
          <div className="access-user-list">
            {users.map((user) => {
              const isCurrentAdmin = user.id === currentUserId;
              return (
                <article className="access-user-row" key={user.id}>
                  <div className="access-user-avatar">
                    {(user.full_name || user.email || "U").slice(0, 1).toUpperCase()}
                  </div>
                  <div className="access-user-identity">
                    <strong>{user.full_name || user.email || "Unnamed user"}</strong>
                    <span>{user.email ?? "No email"}</span>
                    <small>
                      {user.organization ? `${user.organization} · ` : ""}
                      Registered {formatDate(user.created_at)}
                      {user.email_confirmed_at ? " · Email verified" : " · Email not verified"}
                      {user.last_sign_in_at ? ` · Last sign-in ${formatDate(user.last_sign_in_at)}` : ""}
                    </small>
                  </div>
                  <div className="access-user-state">
                    {user.role === "admin" && <span className="access-badge approved">Admin</span>}
                    <span className={`access-badge ${user.access === "approved" ? "approved" : "pending"}`}>
                      {user.access === "approved" ? "Approved" : "Pending"}
                    </span>
                  </div>
                  <div className="access-user-action">
                    {user.access === "pending" ? (
                      <button
                        className="button button-primary"
                        disabled={busyUserId === user.id || !user.email_confirmed_at}
                        onClick={() => void setAccess(user, true)}
                        title={user.email_confirmed_at ? "Approve API access" : "Email confirmation is required first"}
                        type="button"
                      >
                        {busyUserId === user.id ? "Saving…" : "Approve"}
                      </button>
                    ) : (
                      <button
                        className="button button-secondary"
                        disabled={busyUserId === user.id || isCurrentAdmin}
                        onClick={() => void setAccess(user, false)}
                        title={isCurrentAdmin ? "You cannot revoke your own access" : "Revoke API access"}
                        type="button"
                      >
                        {busyUserId === user.id ? "Saving…" : isCurrentAdmin ? "Current admin" : "Revoke"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </section>
  );
}
