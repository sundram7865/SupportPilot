"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import type { OrganizationMember } from "@/types/api";

const roles = ["OWNER", "ADMIN", "MANAGER", "SUPPORT_AGENT", "VIEWER"];

export function OrganizationMembersTable({
  members,
  getToken,
  onChanged,
}: {
  members: OrganizationMember[];
  getToken?: () => Promise<string | null>;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);

  async function updateRole(memberId: string, role: string) {
    if (!getToken) return;

    try {
      setError(null);
      await apiFetch(`/organizations/members/${memberId}/role`, {
        method: "PATCH",
        getToken,
        body: JSON.stringify({ role }),
      });
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update member.");
    }
  }

  async function removeMember(memberId: string) {
    if (!getToken) return;

    const ok = window.confirm("Remove this member from organization?");
    if (!ok) return;

    try {
      setError(null);
      await apiFetch(`/organizations/members/${memberId}`, {
        method: "DELETE",
        getToken,
      });
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member.");
    }
  }

  if (members.length === 0) {
    return <p className="muted">No members found.</p>;
  }

  return (
    <div className="table-wrap">
      {error ? <p className="error">{error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>

        <tbody>
          {members.map((member) => (
            <tr key={member.id}>
              <td>{member.user?.name || "Unnamed"}</td>
              <td>{member.user?.email || "-"}</td>
              <td>
                <select
                  className="input"
                  value={member.role}
                  onChange={(event) =>
                    updateRole(member.id, event.target.value)
                  }
                  disabled={member.role === "OWNER"}
                >
                  {roles.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </td>
              <td>{member.status}</td>
              <td>
                <button
                  className="button secondary"
                  onClick={() => removeMember(member.id)}
                  disabled={member.role === "OWNER"}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}