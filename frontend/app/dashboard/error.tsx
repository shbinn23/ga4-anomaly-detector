"use client";

import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-6">
      <Card className="max-w-xl">
        <CardContent className="flex flex-col gap-4 p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-[color:var(--destructive)]" />
            <h1 className="text-2xl font-semibold tracking-[-0.02em]">Dashboard could not load</h1>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">{error.message}</p>
          <button
            type="button"
            onClick={reset}
            className="w-fit rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[color:color-mix(in_srgb,var(--primary)_88%,black)] active:scale-[0.98]"
          >
            Try again
          </button>
        </CardContent>
      </Card>
    </main>
  );
}
