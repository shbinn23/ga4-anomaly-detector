import { ThemeDetectionView } from "../theme-page";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function EcommerceThemePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const query = await searchParams;
  return <ThemeDetectionView activeTab={query.tab === "table" ? "table" : "chart"} theme="ecommerce" />;
}
