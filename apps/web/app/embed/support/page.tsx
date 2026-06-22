import { EmbeddableSupportWidgetClient } from "@/components/public/EmbeddableSupportWidgetClient";

export default async function EmbedSupportPage({
  searchParams,
}: {
  searchParams: Promise<{ org?: string }>;
}) {
  const params = await searchParams;
  const organizationSlug = params.org || "";

  return <EmbeddableSupportWidgetClient organizationSlug={organizationSlug} />;
}