import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <main className="min-h-screen px-5 py-6 md:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <div className="space-y-3 border-b pb-6">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-12 w-96 max-w-full" />
          <Skeleton className="h-5 w-[32rem] max-w-full" />
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    </main>
  );
}
