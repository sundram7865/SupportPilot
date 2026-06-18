import TicketDetailClient from "./ticket-detail-client";

export default function TicketDetailPage({
  params,
}: {
  params: { ticketId: string };
}) {
  return <TicketDetailClient ticketId={params.ticketId} />;
}