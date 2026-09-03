"use client";

import { useEffect, useState } from "react";

import { clearStoredOrgId, setStoredOrgId } from "@/lib/api";
import { useWorkspaceStore } from "@/lib/workspace-store";
import type { AuthMeResponse } from "@/types/api";

export function OrgSwitcher({
  me,
  orgId,
  onChanged,
}: {
  me: AuthMeResponse | null;
  orgId: string | null;
  onChanged?: (orgId: string) => void;
}) {
  const [value, setValue] = useState(orgId || "");
  const setWorkspaceOrgId = useWorkspaceStore((state) => state.setOrgId);

  useEffect(() => {
    setValue(orgId || "");
  }, [orgId]);

  const memberships = me?.memberships || [];

  if (memberships.length === 0) {
    return null;
  }

  function handleChange(nextOrgId: string) {
    setValue(nextOrgId);

    if (!nextOrgId) {
      clearStoredOrgId();
      return;
    }

    setStoredOrgId(nextOrgId);
    setWorkspaceOrgId(nextOrgId);
    onChanged?.(nextOrgId);

    window.location.reload();
  }

  return (
    <div>
      <label className="muted" style={{ display: "block", marginBottom: 8 }}>
        Organization
      </label>

      <select
        className="input"
        value={value}
        onChange={(event) => handleChange(event.target.value)}
      >
        {memberships.map((membership) => {
          const membershipOrgId =
            membership.organization?.id || membership.organization_id || "";

          return (
            <option key={membershipOrgId} value={membershipOrgId}>
              {membership.organization?.name || membershipOrgId}
            </option>
          );
        })}
      </select>
    </div>
  );
}