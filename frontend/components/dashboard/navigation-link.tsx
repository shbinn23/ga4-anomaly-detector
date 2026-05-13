"use client";

import Link from "next/link";
import type { MouseEvent, ReactNode } from "react";

export function NavigationLink({
  children,
  className,
  href,
  prefetch,
}: {
  children: ReactNode;
  className?: string;
  href: string;
  prefetch?: boolean;
}) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.altKey ||
      event.ctrlKey ||
      event.shiftKey
    ) {
      return;
    }

    const targetUrl = new URL(href, window.location.origin);
    const currentUrl = new URL(window.location.href);

    if (targetUrl.pathname !== currentUrl.pathname || targetUrl.search !== currentUrl.search) {
      window.location.assign(`${targetUrl.pathname}${targetUrl.search}${targetUrl.hash}`);
    }
  }

  return (
    <Link className={className} href={href} onClick={handleClick} prefetch={prefetch}>
      {children}
    </Link>
  );
}
