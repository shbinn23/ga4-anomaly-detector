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
            <h1 className="serif-heading text-2xl">Dashboard could not load</h1>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">{error.message}</p>
          <button
            type="button"
            onClick={reset}
            className="w-fit rounded-md border bg-card px-4 py-2 text-sm font-medium"
          >
            Try again
          </button>
        </CardContent>
      </Card>
    </main>
  );
}
