"use client";

import { useState, type FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { Icon } from "@/components/icons";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

type ProfileField = "full_name" | "organization" | "department" | "phone";

function metadataValue(user: User, field: ProfileField) {
  const value = user.user_metadata[field];
  return typeof value === "string" ? value : "";
}

export function ProfilePanel({
  user,
  onClose,
}: {
  user: User;
  onClose: () => void;
}) {
  const [fullName, setFullName] = useState(metadataValue(user, "full_name"));
  const [organization, setOrganization] = useState(metadataValue(user, "organization"));
  const [department, setDepartment] = useState(metadataValue(user, "department"));
  const [phone, setPhone] = useState(metadataValue(user, "phone"));
  const [error, setError] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const isApproved = user.app_metadata.govasset_access === "approved";

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = fullName.trim();
    if (normalizedName.length < 2) {
      setError("Enter your name using at least 2 characters.");
      return;
    }

    setBusy(true);
    setError("");
    setSavedMessage("");
    try {
      const { error: updateError } = await getSupabaseBrowserClient().auth.updateUser({
        data: {
          full_name: normalizedName,
          organization: organization.trim() || null,
          department: department.trim() || null,
          phone: phone.trim() || null,
        },
      });
      if (updateError) throw updateError;
      setSavedMessage("Your profile has been updated.");
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Could not save your profile. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        aria-labelledby="profile-dialog-title"
        aria-describedby="profile-dialog-description"
        aria-modal="true"
        className="modal-card profile-modal"
        role="dialog"
      >
        <div className="modal-heading">
          <div>
            <h2 id="profile-dialog-title">User profile</h2>
            <p className="profile-modal-subtitle" id="profile-dialog-description">
              Manage your contact and organization details.
            </p>
          </div>
          <button
            aria-label="Close profile"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="profile-account-summary">
          <div className="avatar">{avatarInitials(fullName || user.email || "")}</div>
          <div className="profile-account-copy">
            <strong>{fullName.trim() || user.email || "Your account"}</strong>
            <span>{user.email}</span>
          </div>
          <span className={`access-badge ${isApproved ? "approved" : "pending"}`}>
            {isApproved ? "Approved" : "Pending approval"}
          </span>
        </div>

        <form className="form-stack profile-form" onSubmit={(event) => void saveProfile(event)}>
          <label className="field">
            <span>Email address</span>
            <input autoComplete="email" disabled type="email" value={user.email ?? ""} />
            <small>Email is managed by your sign-in provider.</small>
          </label>
          <label className="field">
            <span>Full name <b>*</b></span>
            <input
              autoComplete="name"
              maxLength={120}
              minLength={2}
              onChange={(event) => {
                setFullName(event.target.value);
                setSavedMessage("");
              }}
              required
              value={fullName}
            />
          </label>
          <label className="field">
            <span>Organization</span>
            <input
              autoComplete="organization"
              maxLength={160}
              onChange={(event) => {
                setOrganization(event.target.value);
                setSavedMessage("");
              }}
              value={organization}
            />
          </label>
          <div className="profile-form-row">
            <label className="field">
              <span>Department</span>
              <input
                maxLength={120}
                onChange={(event) => {
                  setDepartment(event.target.value);
                  setSavedMessage("");
                }}
                value={department}
              />
            </label>
            <label className="field">
              <span>Phone</span>
              <input
                autoComplete="tel"
                maxLength={40}
                onChange={(event) => {
                  setPhone(event.target.value);
                  setSavedMessage("");
                }}
                type="tel"
                value={phone}
              />
            </label>
          </div>
          {!isApproved && (
            <p className="profile-access-note">
              Profile details do not grant API access. An administrator must approve your account.
            </p>
          )}
          {savedMessage && <p className="profile-saved-message" role="status">{savedMessage}</p>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button className="button button-secondary" onClick={onClose} type="button">
              Close
            </button>
            <button className="button button-primary" disabled={busy} type="submit">
              {busy ? "Saving…" : "Save profile"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export function avatarInitials(value: string) {
  const words = value.trim().split(/[\s@._-]+/).filter(Boolean);
  return (words.length > 1
    ? `${words[0][0]}${words[1][0]}`
    : (words[0] ?? "U").slice(0, 2)
  ).toUpperCase();
}
