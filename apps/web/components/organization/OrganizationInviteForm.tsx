"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import type { InviteMemberResult } from "@/types/api";

const roles = ["ADMIN", "MANAGER", "SUPPORT_AGENT", "VIEWER"];

export function OrganizationInviteForm({
  getToken,
  onInvited,
}: {
  getToken?: () => Promise<string | null>;
  onInvited: () => void;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("SUPPORT_AGENT");
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();

    if (!getToken) return;

    setSubmitting(true);
    setMessage(null);

    try {
      const result = await apiFetch<InviteMemberResult>(
        "/organizations/invite",
        {
          method: "POST",
          getToken,
          body: JSON.stringify({
            email,
            name: name || null,
            role,
          }),
        }
      );

      setEmail("");
      setName("");
      setRole("SUPPORT_AGENT");
      setMessage(result.message);

      await onInvited();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Invitation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="grid-two" onSubmit={submit}>
      <div>
        <label className="label">Email</label>
        <input
          className="input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="agent@company.com"
          required
        />
      </div>

      <div>
        <label className="label">Name</label>
        <input
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Agent name"
        />
      </div>

      <div>
        <label className="label">Role</label>
        <select
          className="input"
          value={role}
          onChange={(event) => setRole(event.target.value)}
        >
          {roles.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", alignItems: "end" }}>
        <button className="button" disabled={submitting}>
          {submitting ? "Inviting..." : "Invite"}
        </button>
      </div>

      {message ? <p className="muted">{message}</p> : null}
    </form>
  );
}