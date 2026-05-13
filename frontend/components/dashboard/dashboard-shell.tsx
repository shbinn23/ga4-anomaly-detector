import type { ReactNode } from "react";
import { NavigationLink } from "@/components/dashboard/navigation-link";
import { WorkspaceNav } from "@/components/dashboard/workspace-nav";
import { cn } from "@/lib/utils";

export function DashboardShell({
  children,
  title,
  eyebrow,
  description,
  activeHref,
  actions,
}: {
  children: ReactNode;
  title: string;
  eyebrow?: string;
  description?: ReactNode;
  activeHref?: string;
  actions?: ReactNode;
}) {
  return (
    <main className="min-h-screen px-4 py-5 md:px-8 lg:px-10">
      <div className="mx-auto grid max-w-7xl gap-7">
        <header className="border-b border-border/80 pb-8">
          <WorkspaceNav activeHref={activeHref} />
          <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div className="min-w-0">
              {eyebrow ? (
                <p className="mb-2 text-sm font-semibold text-[color:var(--primary)]">{eyebrow}</p>
              ) : null}
              <h1 className="text-4xl font-semibold leading-[1.08] tracking-[-0.03em] text-foreground md:text-5xl">
                {title}
              </h1>
              {description ? (
                <div className="mt-4 max-w-3xl text-[15px] leading-6 text-muted-foreground">
                  {description}
                </div>
              ) : null}
            </div>
            {actions ? <div className="flex flex-wrap gap-2 lg:justify-end">{actions}</div> : null}
          </div>
        </header>
        {children}
      </div>
    </main>
  );
}

export function PageActionLink({
  href,
  children,
  muted = false,
}: {
  href: string;
  children: ReactNode;
  muted?: boolean;
}) {
  return (
    <NavigationLink
      className={cn(
        "inline-flex h-9 items-center rounded-full border px-4 text-sm font-medium transition-colors active:scale-[0.98]",
        muted
          ? "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
          : "border-transparent bg-primary text-primary-foreground hover:bg-[color:color-mix(in_srgb,var(--primary)_88%,black)]",
      )}
      href={href}
    >
      {children}
    </NavigationLink>
  );
}

export function PageTabs({
  items,
}: {
  items: Array<{ href: string; label: string; active: boolean }>;
}) {
  return (
    <div className="inline-flex w-fit rounded-full border bg-card p-1">
      {items.map((item) => (
        <NavigationLink
          className={cn(
            "rounded-full px-4 py-2 text-sm font-medium transition-colors active:scale-[0.98]",
            item.active
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
          href={item.href}
          key={item.href}
        >
          {item.label}
        </NavigationLink>
      ))}
    </div>
  );
}
