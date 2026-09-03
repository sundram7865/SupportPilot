"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import type { OrganizationDetails } from "@/types/api";

export function OrganizationProfileCard({
  organization,
  getToken,
  onSaved,
}: {
  organization: OrganizationDetails;
  getToken?: () => Promise<string | null>;
  onSaved: () => void;
}) {
  const [name, setName] = useState(organization.name);
  const [supportEmail, setSupportEmail] = useState(
    organization.support_email || ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!getToken) return;

    setSaving(true);
    setError(null);

    try {
      await apiFetch("/organizations/current", {
        method: "PATCH",
        getToken,
        body: JSON.stringify({
          name,
          support_email: supportEmail || null,
        }),
      });

      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save organization.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid-two">
      <div>
        <label className="label">Organization Name</label>
        <input
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <div>
        <label className="label">Support Email</label>
        <input
          className="input"
          value={supportEmail}
          onChange={(event) => setSupportEmail(event.target.value)}
          placeholder="support@company.com"
        />
      </div>

      <div>
        <label className="label">Slug</label>
        <input className="input" value={organization.slug} disabled />
      </div>

      <div>
        <label className="label">Plan</label>
        <input className="input" value={organization.plan || "FREE"} disabled />
      </div>

      <div>
        {error ? <p className="error">{error}</p> : null}
        <button className="button" disabled={saving} onClick={save}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  );
}