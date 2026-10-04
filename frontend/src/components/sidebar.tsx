"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Construction, Building2, FileText, Settings } from "lucide-react";
import { Logo } from "./logo";
import {
  COMPANY_PROFILE_EVENT,
  loadCompanyProfile,
  type CompanyProfile,
} from "@/lib/supabase/user-config";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/driveway", label: "Driveway", icon: Construction },
  { href: "/dashboard/foundation", label: "Foundation", icon: Building2, disabled: true },
  { href: "/dashboard/quotes", label: "Cotizaciones", icon: FileText, disabled: true },
  { href: "/dashboard/settings", label: "Ajustes", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [profile, setProfile] = useState<CompanyProfile | null>(null);

  useEffect(() => {
    // Guard contra doble-invocación de efectos en dev (ver settings-form.tsx).
    let ignore = false;
    loadCompanyProfile().then((p) => {
      if (!ignore) setProfile(p);
    });
    const onUpdate = (e: Event) => setProfile((e as CustomEvent<CompanyProfile>).detail);
    window.addEventListener(COMPANY_PROFILE_EVENT, onUpdate);
    return () => {
      ignore = true;
      window.removeEventListener(COMPANY_PROFILE_EVENT, onUpdate);
    };
  }, []);

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-white/10 bg-[#0b0f19] px-4 py-5 print:hidden">
      <div className="px-2">
        {profile?.companyName ? (
          <div className="flex items-center gap-3">
            {profile.logoDataUrl ? (
              <Image
                src={profile.logoDataUrl}
                alt={profile.companyName}
                width={32}
                height={32}
                unoptimized
                className="h-8 w-8 rounded object-contain"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded bg-[#f0a500]/15 text-sm font-bold text-[#f0a500]">
                {profile.companyName.charAt(0).toUpperCase()}
              </span>
            )}
            <div className="min-w-0">
              <div className="truncate text-sm font-bold uppercase tracking-wider text-white">
                {profile.companyName}
              </div>
              <div className="text-[11px] text-white/40">Estimator</div>
            </div>
          </div>
        ) : (
          <Logo subtitle="Estimator" />
        )}
      </div>

      <nav className="mt-8 flex flex-col gap-1">
        {NAV.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const Icon = item.icon;

          if (item.disabled) {
            return (
              <div
                key={item.href}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/25"
                title="Próximamente"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </div>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-[#f0a500]/10 font-medium text-[#f0a500]"
                  : "text-white/60 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-2 pt-6 text-[11px] text-white/25">
        Driveway &amp; Foundation Estimator
      </div>
    </aside>
  );
}
