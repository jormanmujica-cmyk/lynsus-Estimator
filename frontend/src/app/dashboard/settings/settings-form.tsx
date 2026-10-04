"use client";

import { useEffect, useRef, useState } from "react";
import {
  EMPTY_COMPANY_PROFILE,
  loadCompanyProfile,
  saveCompanyProfile,
  type CompanyProfile,
} from "@/lib/supabase/user-config";

const inputClass =
  "mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]";

export default function SettingsForm() {
  const [profile, setProfile] = useState<CompanyProfile>(EMPTY_COMPANY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // React (dev) invoca efectos 2 veces al montar — sin este guard, la
    // promesa del primer montaje puede resolver tarde y pisar lo que el
    // usuario ya escribió. Patrón estándar de cancelación de React.
    let ignore = false;
    loadCompanyProfile().then((p) => {
      if (ignore) return;
      setProfile(p);
      setLoading(false);
    });
    return () => {
      ignore = true;
    };
  }, []);

  const set = <K extends keyof CompanyProfile>(key: K, value: CompanyProfile[K]) =>
    setProfile((p) => ({ ...p, [key]: value }));

  const onLogoChange = (file: File | null) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => set("logoDataUrl", reader.result as string);
    reader.readAsDataURL(file);
  };

  const onSave = async () => {
    setSaveState("saving");
    const ok = await saveCompanyProfile(profile);
    setSaveState(ok ? "saved" : "error");
    if (ok) setTimeout(() => setSaveState("idle"), 2500);
  };

  if (loading) {
    return <p className="text-sm text-white/40">Cargando…</p>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">👤 Tu información</h2>
        <div className="mt-5 grid grid-cols-2 gap-4">
          <label className="block text-sm">
            <span className="text-white/70">Nombre</span>
            <input
              type="text"
              value={profile.firstName}
              onChange={(e) => set("firstName", e.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/70">Apellido</span>
            <input
              type="text"
              value={profile.lastName}
              onChange={(e) => set("lastName", e.target.value)}
              className={inputClass}
            />
          </label>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">🏢 Tu empresa</h2>
        <div className="mt-5 grid grid-cols-2 gap-4">
          <div className="col-span-full">
            <label className="block text-sm">
              <span className="text-white/70">Nombre de la empresa</span>
              <input
                type="text"
                value={profile.companyName}
                onChange={(e) => set("companyName", e.target.value)}
                placeholder="ej. Pérez Concrete LLC"
                className={inputClass}
              />
            </label>
          </div>

          <div className="col-span-full">
            <span className="text-sm text-white/70">Logo</span>
            <div className="mt-1.5 flex items-center gap-4">
              {profile.logoDataUrl ? (
                // Logo del contratista: viene de localStorage/base64, no es un
                // asset del proyecto — <img> normal, no next/image.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.logoDataUrl}
                  alt="Logo"
                  className="h-16 w-16 rounded-lg border border-white/10 object-contain"
                />
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-lg border border-dashed border-white/15 text-xs text-white/30">
                  Sin logo
                </div>
              )}
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-white/70 transition hover:border-[#f0a500]/50 hover:text-[#f0a500]"
                >
                  Subir logo
                </button>
                {profile.logoDataUrl && (
                  <button
                    type="button"
                    onClick={() => set("logoDataUrl", null)}
                    className="text-xs text-white/40 transition hover:text-red-400"
                  >
                    Quitar logo
                  </button>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onLogoChange(e.target.files?.[0] ?? null)}
              />
            </div>
            <p className="mt-2 text-xs text-white/30">
              Aparece en el menú de la izquierda y en el estimado que le mandas al cliente.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">🔗 Web y redes sociales</h2>
        <div className="mt-5 grid grid-cols-2 gap-4">
          <div className="col-span-full">
            <label className="block text-sm">
              <span className="text-white/70">Página web</span>
              <input
                type="text"
                value={profile.website}
                onChange={(e) => set("website", e.target.value)}
                placeholder="www.tuempresa.com"
                className={inputClass}
              />
            </label>
          </div>
          <label className="block text-sm">
            <span className="text-white/70">Facebook</span>
            <input
              type="text"
              value={profile.facebook}
              onChange={(e) => set("facebook", e.target.value)}
              placeholder="facebook.com/tuempresa"
              className={inputClass}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/70">Instagram</span>
            <input
              type="text"
              value={profile.instagram}
              onChange={(e) => set("instagram", e.target.value)}
              placeholder="@tuempresa"
              className={inputClass}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/70">WhatsApp</span>
            <input
              type="text"
              value={profile.whatsapp}
              onChange={(e) => set("whatsapp", e.target.value)}
              placeholder="(305) 555-1234"
              className={inputClass}
            />
          </label>
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onSave}
          disabled={saveState === "saving"}
          className="rounded-lg bg-[#f0a500] px-5 py-2.5 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-60"
        >
          {saveState === "saving" ? "Guardando…" : "Guardar"}
        </button>
        {saveState === "saved" && <span className="text-sm text-green-400">✓ Guardado</span>}
        {saveState === "error" && (
          <span className="text-sm text-red-400">No se pudo guardar — intenta de nuevo</span>
        )}
      </div>
    </div>
  );
}
