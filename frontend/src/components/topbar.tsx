"use client";

import { useState, useRef, useEffect } from "react";
import { Search, Bell, ChevronDown, LogOut } from "lucide-react";
import { signOut } from "@/app/login/actions";

export default function Topbar({ email }: { email: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const initial = email.charAt(0).toUpperCase();

  return (
    <header className="flex items-center justify-between gap-4 border-b border-white/10 bg-[#0b0f19] px-6 py-4 print:hidden">
      <div className="relative w-full max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
        <input
          type="text"
          placeholder="Buscar…"
          disabled
          className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder:text-white/30 outline-none"
        />
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          className="rounded-full p-2 text-white/50 hover:bg-white/5 hover:text-white"
          title="Notificaciones (próximamente)"
        >
          <Bell className="h-5 w-5" />
        </button>

        <div className="relative" ref={ref}>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-white hover:bg-white/5"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f0a500] text-xs font-bold text-black">
              {initial}
            </span>
            <span className="max-w-[160px] truncate text-white/80">{email}</span>
            <ChevronDown className="h-3.5 w-3.5 text-white/40" />
          </button>

          {open && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-lg border border-white/10 bg-[#0f1420] p-1 shadow-xl">
              <form action={signOut}>
                <button
                  type="submit"
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-white/70 hover:bg-white/5 hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                  Cerrar sesión
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
