"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { auth, authMetadata, isUnauthenticated, setToken, TOKEN_KEY } from "@/lib/grpc";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (!token) {
      router.replace("/login");
      return;
    }
    auth
      .Me({}, authMetadata())
      .then((u) => setUser(u.username))
      .catch((err) => {
        if (isUnauthenticated(err)) router.replace("/login");
      })
      .finally(() => setReady(true));
  }, [router]);

  function logout() {
    auth.Logout({}, authMetadata()).catch(() => undefined);
    setToken(null);
    router.replace("/login");
  }

  if (!ready) return null;

  const tabs = [
    { href: "/dashboard", label: "Books" },
    { href: "/dashboard/members", label: "Members" },
    { href: "/dashboard/loans", label: "Loans" },
  ];

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="font-semibold">Library</span>
            <nav className="flex gap-4 text-sm">
              {tabs.map((t) => (
                <Link
                  key={t.href}
                  href={t.href}
                  className={
                    pathname === t.href
                      ? "font-medium text-slate-900"
                      : "text-slate-500 hover:text-slate-900"
                  }
                >
                  {t.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">{user}</span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
    </div>
  );
}
