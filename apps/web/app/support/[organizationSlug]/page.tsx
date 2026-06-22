import { PublicSupportFormClient } from "@/components/public/PublicSupportFormClient";

export default async function PublicSupportPage({
  params,
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;

  return <PublicSupportFormClient organizationSlug={organizationSlug} />;
}