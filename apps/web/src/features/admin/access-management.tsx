"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import type { AdminUser } from "@/lib/api/types";

const PAGE_SIZE = 100;

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

type UserFilter = "all" | "pending" | "approved" | "unverified";

export function AccessManagement({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [busyUserId, setBusyUserId] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<UserFilter>("all");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const firstPage = await api.listAdminUsers(1, PAGE_SIZE);
      setUsers(firstPage);
      setPage(1);
      setHasMore(firstPage.length === PAGE_SIZE);
    } catch (loadError) {
      setError(message(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.listAdminUsers(1, PAGE_SIZE)
      .then((nextUsers) => {
        if (!cancelled) {
          setUsers(nextUsers);
          setHasMore(nextUsers.length === PAGE_SIZE);
        }
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

  async function loadMore() {
    setLoadingMore(true);
    setError("");
    try {
      const nextPage = page + 1;
      const nextUsers = await api.listAdminUsers(nextPage, PAGE_SIZE);
      setUsers((current) => [
        ...current,
        ...nextUsers.filter((user) => !current.some((entry) => entry.id === user.id)),
      ]);
      setPage(nextPage);
      setHasMore(nextUsers.length === PAGE_SIZE);
    } catch (loadError) {
      setError(message(loadError));
    } finally {
      setLoadingMore(false);
    }
  }

  async function setAccess(user: AdminUser, approved: boolean) {
    if (
      !approved &&
      !window.confirm(
        `Revoke API access for ${user.email ?? "this user"}? They may retain access until their current token expires or refreshes.`,
      )
    ) {
      return;
    }
    setBusyUserId(user.id);
    setError("");
    setNotice("");
    try {
      const updated = await api.setUserAccess(user.id, approved);
      setUsers((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
      setNotice(
        approved
          ? `${updated.email ?? "User"} access approved. They must sign out and back in before API access becomes available.`
          : `${updated.email ?? "User"} access revoked. Their current token may remain valid until it expires or refreshes.`,
      );
    } catch (updateError) {
      setError(message(updateError));
    } finally {
      setBusyUserId("");
    }
  }

  const pendingCount = users.filter(
    (user) => user.access === "pending" && user.email_confirmed_at,
  ).length;
  const visibleUsers = users.filter((user) => {
    const normalizedSearch = search.trim().toLowerCase();
    const matchesSearch =
      !normalizedSearch ||
      [user.email, user.full_name, user.organization]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(normalizedSearch));
    const matchesFilter =
      filter === "all" ||
      (filter === "pending" && user.access === "pending") ||
      (filter === "approved" && user.access === "approved") ||
      (filter === "unverified" && !user.email_confirmed_at);
    return matchesSearch && matchesFilter;
  });

  return (
    <section className="access-management">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ADMINISTRATION</div>
          <h1>User access</h1>
          <p>Review registered accounts and explicitly approve API access after email verification.</p>
        </div>
        <button className="button button-secondary" disabled={loading || loadingMore} onClick={() => void loadUsers()} type="button">
          <Icon name="refresh" />
          Refresh
        </button>
      </div>

      {error && <div className="feedback-banner error-banner" role="alert"><Icon name="warning" /><span>{error}</span></div>}
      {notice && <div className="feedback-banner success-banner" role="status"><Icon name="check" /><span>{notice}</span></div>}

      <div className="access-summary">
        <div className="panel access-summary-card">
          <span>Loaded accounts</span>
          <strong>{users.length}</strong>
        </div>
        <div className="panel access-summary-card">
          <span>Verified users awaiting approval (loaded)</span>
          <strong>{pendingCount}</strong>
        </div>
      </div>

      <section className="panel access-users-panel">
        <div className="panel-heading">
          <div>
            <h2>Registered users</h2>
            <p>Showing {users.length} loaded accounts. Accounts require email verification before approval.</p>
          </div>
        </div>
        {loading ? (
          <div className="loading-state"><span className="spinner" /> Loading accounts…</div>
        ) : users.length === 0 ? (
          <div className="empty-state"><strong>No registered accounts</strong><p>Accounts appear here after registration.</p></div>
        ) : (
          <>
            <div className="access-user-tools">
              <label className="access-user-search">
                <span className="sr-only">Search loaded accounts</span>
                <input
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search loaded accounts by name, email or organization"
                  type="search"
                  value={search}
                />
              </label>
              <div aria-label="Filter accounts" className="access-user-filters">
                {(["all", "pending", "approved", "unverified"] as const).map((option) => (
                  <button
                    aria-pressed={filter === option}
                    className={`button button-small ${filter === option ? "button-primary" : "button-secondary"}`}
                    key={option}
                    onClick={() => setFilter(option)}
                    type="button"
                  >
                    {option === "unverified" ? "Email unverified" : option}
                  </button>
                ))}
              </div>
            </div>
            {visibleUsers.length === 0 ? (
              <div className="empty-state">
                <strong>No accounts match this view</strong>
                <p>Clear the search or load more accounts to continue reviewing.</p>
              </div>
            ) : (
                  <div className="access-user-list">
                {visibleUsers.map((user) => {
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
                                disabled={Boolean(busyUserId) || !user.email_confirmed_at}
                                onClick={() => void setAccess(user, true)}
                                title={user.email_confirmed_at ? "Approve API access" : "Email confirmation is required first"}
                                type="button"
                              >
                                {busyUserId === user.id ? "Saving…" : "Approve"}
                              </button>
                            ) : (
                              <button
                                className="button button-secondary"
                                disabled={Boolean(busyUserId) || isCurrentAdmin}
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
            {hasMore && (
              <div className="access-user-pagination">
                <button
                  className="button button-secondary"
                  disabled={loadingMore}
                  onClick={() => void loadMore()}
                  type="button"
                >
                  {loadingMore ? "Loading…" : "Load more accounts"}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </section>
  );
}
