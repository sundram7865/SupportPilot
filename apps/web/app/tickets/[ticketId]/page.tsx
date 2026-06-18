import { TicketWorkspace } from "@/components/ticket/TicketWorkspace";

export default async function TicketPage({
  params,
}: {
  params: Promise<{ ticketId: string }>;
}) {
  const { ticketId } = await params;

  return <TicketWorkspace ticketId={ticketId} />;
}