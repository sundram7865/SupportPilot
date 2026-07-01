"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { Section } from "@/components/ui/Section";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import type {
  AuthMeResponse,
  OrganizationDetails,
  OrganizationInvitation,
  OrganizationMember,
} from "@/types/api";

import { OrganizationInviteForm } from "./OrganizationInviteForm";
import { OrganizationInvitationsTable } from "./OrganizationInvitationsTable";
import { OrganizationMembersTable } from "./OrganizationMembersTable";
import { OrganizationProfileCard } from "./OrganizationProfileCard";

export function OrganizationSettingsClient() {
  const { getToken, isSignedIn } = useAuth();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [organization, setOrganization] = useState<OrganizationDetails | null>(
    null
  );
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tokenGetter = isSignedIn ? getToken : undefined;

  async function load() {
    if (!tokenGetter) return;

    try {
      setLoading(true);
      setError(null);

      const boot = await bootstrapAuth(tokenGetter);

      setMe(boot.me);
      setOrgId(boot.orgId);

      const [orgResponse, membersResponse, invitationsResponse] =
        await Promise.all([
          apiFetch<OrganizationDetails>("/organizations/current", {
            getToken: tokenGetter,
          }),
          apiFetch<OrganizationMember[]>("/organizations/members", {
            getToken: tokenGetter,
          }),
          apiFetch<OrganizationInvitation[]>("/organizations/invitations", {
            getToken: tokenGetter,
          }),
        ]);

      setOrganization(orgResponse);
      setMembers(membersResponse);
      setInvitations(invitationsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [isSignedIn]);

  return (
    <AppShell
      title="Organization Settings"
      subtitle="Manage company profile, members, and pending invitations."
    >
      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState message="Loading organization settings..." />
      ) : (
        <div className="stack">
          <Section title="Organization Profile">
            {organization ? (
              <OrganizationProfileCard
                organization={organization}
                getToken={tokenGetter}
                onSaved={load}
              />
            ) : null}
          </Section>

          <Section title="Invite Member">
            <OrganizationInviteForm getToken={tokenGetter} onInvited={load} />
          </Section>

          <Section title="Members">
            <OrganizationMembersTable
              members={members}
              getToken={tokenGetter}
              onChanged={load}
            />
          </Section>

          <Section title="Pending Invitations">
            <OrganizationInvitationsTable invitations={invitations} />
          </Section>
        </div>
      )}
    </AppShell>
  );
}