import { NavigationLink } from "@/components/dashboard/navigation-link";

const navItems = [
  { label: "Overview", href: "/dashboard" },
  { label: "Sessions", href: "/dashboard/themes/sessions" },
  { label: "Ecommerce", href: "/dashboard/themes/ecommerce" },
  { label: "Unassigned Traffic", href: "/dashboard/themes/unassigned-traffic" },
  { label: "Reports", href: "/dashboard/reports" },
];

export function WorkspaceNav({ activeHref }: { activeHref?: string }) {
  return (
    <nav className="grid gap-3">
      <div className="text-[21px] font-semibold leading-none tracking-[-0.02em] text-foreground">Monitoring Workspace</div>
      <div className="flex flex-wrap gap-1 border-b border-border/80">
        {navItems.map((item) => {
          const activePath = activeHref ?? "/dashboard";
          const active = item.href === "/dashboard"
            ? activePath === item.href
            : activePath === item.href || activePath.startsWith(`${item.href}/`);

          return (
            <NavigationLink
              className={[
                "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              ].join(" ")}
              href={item.href}
              key={item.href}
              prefetch={false}
            >
              {item.label}
            </NavigationLink>
          );
        })}
      </div>
    </nav>
  );
}
