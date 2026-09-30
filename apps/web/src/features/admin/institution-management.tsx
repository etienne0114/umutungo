"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api/client";
import type {
  Institution,
  InstitutionCreate,
  InstitutionMembership,
  InstitutionRole,
  InstitutionType,
} from "@/lib/api/institutions";
import type { AdminUser } from "@/lib/api/types";

const institutionTypes: InstitutionType[] = [
  "ministry",
  "agency",
  "authority",
  "commission",
  "public_institution",
  "other_government_entity",
  "province",
  "city",
  "district",
];

const institutionRoles: InstitutionRole[] = [
  "institution_admin",
  "fleet_manager",
  "maintenance_officer",
  "technician",
  "driver",
  "auditor",
  "viewer",
];

type CatalogFilter = "all" | "central" | "local" | "custom";

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "Could not complete the request.";
}

function optionLabel(institution: Institution, depth = 0) {
  const prefix = depth ? "— " : "";
  return `${prefix}${institution.short_name || institution.code} · ${institution.name}`;
}

export function InstitutionManagement() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [memberships, setMemberships] = useState<InstitutionMembership[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [directoryError, setDirectoryError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [catalogFilter, setCatalogFilter] = useState<CatalogFilter>("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const [catalogResult, usersResult] = await Promise.allSettled([
      Promise.all([api.listAdminInstitutions(), api.listInstitutionMemberships()]),
      api.listAdminUsers(1, 100),
    ]);

    if (catalogResult.status === "fulfilled") {
      setInstitutions(catalogResult.value[0]);
      setMemberships(catalogResult.value[1]);
    } else {
      setError(message(catalogResult.reason));
    }
    if (usersResult.status === "fulfilled") {
      setUsers(usersResult.value);
      setDirectoryError("");
    } else {
      setUsers([]);
      setDirectoryError(message(usersResult.reason));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      Promise.all([api.listAdminInstitutions(), api.listInstitutionMemberships()]),
      api.listAdminUsers(1, 100),
    ]).then(([catalogResult, usersResult]) => {
      if (cancelled) return;
      if (catalogResult.status === "fulfilled") {
        setInstitutions(catalogResult.value[0]);
        setMemberships(catalogResult.value[1]);
      } else {
        setError(message(catalogResult.reason));
      }
      if (usersResult.status === "fulfilled") {
        setUsers(usersResult.value);
        setDirectoryError("");
      } else {
        setDirectoryError(message(usersResult.reason));
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const institutionById = useMemo(
    () => new Map(institutions.map((institution) => [institution.id, institution])),
    [institutions],
  );
  const userById = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);
  const approvedUsers = users.filter((user) => user.access === "approved");
  const roots = useMemo(
    () => institutions.filter((institution) => institution.parent_institution_id === null),
    [institutions],
  );
  const childrenByParent = useMemo(() => {
    const result = new Map<number, Institution[]>();
    institutions.forEach((institution) => {
      if (institution.parent_institution_id === null) return;
      const children = result.get(institution.parent_institution_id) ?? [];
      children.push(institution);
      result.set(institution.parent_institution_id, children);
    });
    return result;
  }, [institutions]);
  const orderedInstitutions = useMemo(
    () => roots.flatMap((root) => [root, ...(childrenByParent.get(root.id) ?? [])]),
    [childrenByParent, roots],
  );
  const visibleRoots = useMemo(() => {
    const query = search.trim().toLowerCase();
    return roots.filter((root) => {
      const children = childrenByParent.get(root.id) ?? [];
      const filterMatch =
        catalogFilter === "all" ||
        (catalogFilter === "central" && root.institution_type === "ministry") ||
        (catalogFilter === "local" && ["province", "city"].includes(root.institution_type)) ||
        (catalogFilter === "custom" && !root.is_official);
      if (!filterMatch) return false;
      if (!query) return true;
      return [root, ...children].some((institution) =>
        [institution.name, institution.code, institution.short_name]
          .filter(Boolean)
          .some((value) => value!.toLowerCase().includes(query)),
      );
    });
  }, [catalogFilter, childrenByParent, roots, search]);
  const verifiedOn = institutions
    .map((institution) => institution.source_verified_on)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);

  async function createInstitution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const parent = String(values.get("parent_institution_id") ?? "");
    const payload: InstitutionCreate = {
      name: String(values.get("name") ?? "").trim(),
      code: String(values.get("code") ?? "").trim().toUpperCase(),
      short_name: String(values.get("short_name") ?? "").trim() || null,
      description: String(values.get("description") ?? "").trim() || null,
      institution_type: String(values.get("institution_type")) as InstitutionType,
      active: true,
      parent_institution_id: parent ? Number(parent) : null,
    };
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.createInstitution(payload);
      form.reset();
      setNotice(`${payload.name} was added to the reporting hierarchy.`);
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function syncOfficialCatalog() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api.syncOfficialInstitutionCatalog();
      setNotice(
        `Official catalog synchronized: ${result.created} added, ${result.updated} updated, ${result.unchanged} unchanged.`,
      );
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function toggleInstitution(institution: Institution) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.updateInstitution(institution.id, { active: !institution.active });
      setNotice(`${institution.name} is now ${institution.active ? "inactive" : "active"}.`);
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function createMembership(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.createInstitutionMembership({
        user_id: String(values.get("user_id")),
        institution_id: Number(values.get("institution_id")),
        role: String(values.get("role")) as InstitutionRole,
      });
      form.reset();
      setNotice("Institution membership assigned.");
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function removeMembership(membership: InstitutionMembership) {
    if (!window.confirm("Remove this user from the institution?")) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.deleteInstitutionMembership(membership.user_id, membership.institution_id);
      setNotice("Institution membership removed.");
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function updateMembershipRole(
    membership: InstitutionMembership,
    role: InstitutionRole,
  ) {
    setBusy(true);
    setError("");
    try {
      await api.updateInstitutionMembership(membership.user_id, membership.institution_id, role);
      setNotice("Institution role updated.");
      await load();
    } catch (requestError) {
      setError(message(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="access-management institution-management">
      <div className="page-heading">
        <div>
          <div className="eyebrow">GOVERNMENT ADMINISTRATION</div>
          <h1>Institution directory</h1>
          <p>
            Manage reporting parents, verified government entities, and institution access.
          </p>
        </div>
        <div className="heading-actions">
          <button className="button button-primary" disabled={loading || busy} onClick={() => void syncOfficialCatalog()} type="button">
            <Icon name="activity" /> {busy ? "Working…" : "Sync official directory"}
          </button>
          <button className="button button-secondary" disabled={loading || busy} onClick={() => void load()} type="button">
            <Icon name="refresh" /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="feedback-banner error-banner" role="alert"><Icon name="warning" /><span>{error}</span></div>}
      {notice && <div className="feedback-banner success-banner" role="status"><Icon name="check" /><span>{notice}</span></div>}

      <div className="institution-summary-grid">
        <div className="panel access-summary-card"><span>Ministries</span><strong>{institutions.filter((item) => item.institution_type === "ministry").length}</strong><small>Central government reporting roots</small></div>
        <div className="panel access-summary-card"><span>Local government</span><strong>{institutions.filter((item) => ["province", "city", "district"].includes(item.institution_type)).length}</strong><small>City, provinces and districts</small></div>
        <div className="panel access-summary-card"><span>Verified entries</span><strong>{institutions.filter((item) => item.is_official).length}</strong><small>{verifiedOn ? `Checked ${verifiedOn}` : "Awaiting catalog sync"}</small></div>
        <div className="panel access-summary-card"><span>Memberships</span><strong>{memberships.length}</strong><small>Active institution assignments</small></div>
      </div>

      <section className="panel institution-directory-panel">
        <header className="panel-heading institution-directory-heading">
          <div>
            <div className="panel-title-row"><h2>Administration structure</h2><span className="count-pill">{institutions.length}</span></div>
            <p>Each asset rolls up once through its primary reporting parent.</p>
          </div>
          {verifiedOn && (
            <a className="official-source-link" href="https://www.gov.rw/government/institutions/ministries" rel="noreferrer" target="_blank">Government source ↗</a>
          )}
        </header>
        <div className="institution-toolbar">
          <label className="search-field institution-search">
            <Icon name="search" />
            <input aria-label="Search institutions" onChange={(event) => setSearch(event.target.value)} placeholder="Search MINALOC, MINIJUST, district…" value={search} />
            {search && <button aria-label="Clear search" onClick={() => setSearch("")} type="button"><Icon name="close" /></button>}
          </label>
          <div className="institution-filter-tabs" role="group" aria-label="Institution type filter">
            {(["all", "central", "local", "custom"] as CatalogFilter[]).map((value) => (
              <button className={catalogFilter === value ? "active" : ""} key={value} onClick={() => setCatalogFilter(value)} type="button">{titleCase(value)}</button>
            ))}
          </div>
        </div>
        {loading ? <div className="loading-state"><span className="spinner" /> Loading government directory…</div> : visibleRoots.length === 0 ? <div className="empty-state"><strong>No matching institutions</strong><p>Change the search/filter or synchronize the official directory.</p></div> : (
          <div className="institution-tree-grid">
            {visibleRoots.map((root) => {
              const children = childrenByParent.get(root.id) ?? [];
              return (
                <article className="institution-tree-card" key={root.id}>
                  <header>
                    <div className="institution-mark">{root.short_name || root.code}</div>
                    <div><strong>{root.name}</strong><span>{titleCase(root.institution_type)} · {children.length} linked {children.length === 1 ? "institution" : "institutions"}</span></div>
                    <span className={`access-badge ${root.active ? "approved" : "pending"}`}>{root.active ? "Active" : "Inactive"}</span>
                  </header>
                  {root.description && <p className="institution-note">{root.description}</p>}
                  <div className="institution-child-list">
                    {children.length === 0 ? <span className="institution-no-children">No listed subordinate institutions</span> : children.map((child) => (
                      <div className="institution-child" key={child.id} title={child.description ?? undefined}>
                        <span className="institution-branch" aria-hidden="true" />
                        <div><strong>{child.short_name || child.code}</strong><span>{child.name}</span></div>
                        <small>{titleCase(child.institution_type)}</small>
                      </div>
                    ))}
                  </div>
                  <footer>
                    <span>{root.is_official ? `Verified ${root.source_verified_on ?? ""}` : "Custom record"}</span>
                    <button className="text-button" disabled={busy} onClick={() => void toggleInstitution(root)} type="button">{root.active ? "Deactivate" : "Activate"}</button>
                  </footer>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <details className="panel institution-create-panel">
        <summary><span><strong>Add a custom institution</strong><small>Use this only for an entity not present in the verified directory.</small></span><span aria-hidden="true">＋</span></summary>
        <form className="form-stack" onSubmit={(event) => void createInstitution(event)}>
          <div className="form-grid">
            <label className="field"><span>Official name *</span><input name="name" required /></label>
            <label className="field"><span>Unique code *</span><input maxLength={80} name="code" required /></label>
            <label className="field"><span>Short name</span><input maxLength={80} name="short_name" /></label>
            <label className="field"><span>Institution type</span><select name="institution_type">{institutionTypes.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label>
            <label className="field"><span>Primary reporting parent</span><select defaultValue="" name="parent_institution_id"><option value="">Top-level institution</option>{orderedInstitutions.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{optionLabel(item, item.parent_institution_id ? 1 : 0)}</option>)}</select></label>
            <label className="field"><span>Description</span><input maxLength={1000} name="description" /></label>
          </div>
          <div className="modal-actions"><button className="button button-primary" disabled={busy} type="submit">{busy ? "Saving…" : "Add institution"}</button></div>
        </form>
      </details>

      <section className="panel access-users-panel">
        <header className="panel-heading"><div><h2>Institution memberships</h2><p>Assign approved accounts to an institution and a least-privilege role.</p></div></header>
        {directoryError && (
          <div className="institution-directory-warning" role="status">
            <Icon name="warning" />
            <div><strong>Auth user directory is unavailable</strong><p>The institution catalog remains usable. Configure <code>SUPABASE_SECRET_KEY</code> (or the legacy service-role key) on the API server to populate the approved-user dropdown.</p></div>
          </div>
        )}
        <form className="form-stack membership-form" onSubmit={(event) => void createMembership(event)}>
          <div className="form-grid">
            <label className="field"><span>Approved user</span><select disabled={Boolean(directoryError)} name="user_id" required><option value="">{directoryError ? "User directory not configured" : "Select approved user"}</option>{approvedUsers.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.email || user.id}</option>)}</select></label>
            <label className="field"><span>Institution</span><select name="institution_id" required><option value="">Select institution</option>{orderedInstitutions.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{optionLabel(item, item.parent_institution_id ? 1 : 0)}</option>)}</select></label>
            <label className="field"><span>Role</span><select name="role">{institutionRoles.map((role) => <option key={role} value={role}>{titleCase(role)}</option>)}</select></label>
          </div>
          <div className="modal-actions"><button className="button button-primary" disabled={busy || Boolean(directoryError) || approvedUsers.length === 0 || institutions.length === 0} type="submit">{busy ? "Saving…" : "Assign membership"}</button></div>
        </form>
        {memberships.length > 0 && (
          <div className="table-scroll"><table className="data-table"><thead><tr><th>User</th><th>Institution</th><th>Role</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{memberships.map((membership) => { const user = userById.get(membership.user_id); return <tr key={`${membership.user_id}-${membership.institution_id}`}><td><strong>{user?.full_name || user?.email || membership.user_id}</strong></td><td>{institutionById.get(membership.institution_id)?.name ?? `Institution ${membership.institution_id}`}</td><td><select aria-label={`Role for ${user?.email ?? membership.user_id}`} disabled={busy} onChange={(event) => void updateMembershipRole(membership, event.currentTarget.value as InstitutionRole)} value={membership.role}>{institutionRoles.map((role) => <option key={role} value={role}>{titleCase(role)}</option>)}</select></td><td><button className="button button-secondary button-small" disabled={busy} onClick={() => void removeMembership(membership)} type="button">Remove</button></td></tr>; })}</tbody></table></div>
        )}
      </section>
    </section>
  );
}
