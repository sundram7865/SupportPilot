import type { OrganizationInvitation } from "@/types/api";

export function OrganizationInvitationsTable({
  invitations,
}: {
  invitations: OrganizationInvitation[];
}) {
  if (invitations.length === 0) {
    return <p className="muted">No invitations found.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Name</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>

        <tbody>
          {invitations.map((invitation) => (
            <tr key={invitation.id}>
              <td>{invitation.email}</td>
              <td>{invitation.name || "-"}</td>
              <td>{invitation.role}</td>
              <td>{invitation.status}</td>
              <td>
                {invitation.created_at
                  ? new Date(invitation.created_at).toLocaleString()
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}