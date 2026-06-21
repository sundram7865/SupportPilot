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

  async function save() {
    if (!getToken) return;

    setSaving(true);

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
        <button className="button" disabled={saving} onClick={save}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  );
}