import { createClient } from "./client";

/**
 * Perfil de la empresa del contratista — mismo patrón merge-upsert que
 * database.py (save_app_state/load_app_state) usa en Streamlit, mismo
 * proyecto Supabase y misma tabla `user_config` (user_id, config jsonb).
 * Se guarda anidado bajo la clave "companyProfile" para no pisar las claves
 * planas que ya usa app.py (pdf_company_name, header_bg_image, etc.).
 */
export type CompanyProfile = {
  firstName: string;
  lastName: string;
  companyName: string;
  website: string;
  facebook: string;
  instagram: string;
  whatsapp: string;
  logoDataUrl: string | null;
};

export const EMPTY_COMPANY_PROFILE: CompanyProfile = {
  firstName: "",
  lastName: "",
  companyName: "",
  website: "",
  facebook: "",
  instagram: "",
  whatsapp: "",
  logoDataUrl: null,
};

// Evento local para que otros componentes (ej. Sidebar) se enteren al toque
// de que el perfil cambió, sin necesidad de Context/estado global.
export const COMPANY_PROFILE_EVENT = "lynsus:company-profile-updated";

export async function loadCompanyProfile(): Promise<CompanyProfile> {
  try {
    const supabase = createClient();
    const { data: auth } = await supabase.auth.getUser();
    if (!auth.user) return EMPTY_COMPANY_PROFILE;

    const { data, error } = await supabase
      .from("user_config")
      .select("config")
      .eq("user_id", auth.user.id)
      .maybeSingle();

    if (error || !data) return EMPTY_COMPANY_PROFILE;
    const saved = (data.config as Record<string, unknown> | null)?.companyProfile as
      | Partial<CompanyProfile>
      | undefined;
    return saved ? { ...EMPTY_COMPANY_PROFILE, ...saved } : EMPTY_COMPANY_PROFILE;
  } catch {
    return EMPTY_COMPANY_PROFILE;
  }
}

export async function saveCompanyProfile(profile: CompanyProfile): Promise<boolean> {
  try {
    const supabase = createClient();
    const { data: auth } = await supabase.auth.getUser();
    if (!auth.user) return false;

    const { data: existing } = await supabase
      .from("user_config")
      .select("config")
      .eq("user_id", auth.user.id)
      .maybeSingle();

    const merged = {
      ...((existing?.config as Record<string, unknown>) ?? {}),
      companyProfile: profile,
    };

    const { error } = await supabase
      .from("user_config")
      .upsert({ user_id: auth.user.id, config: merged }, { onConflict: "user_id" });

    if (!error && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(COMPANY_PROFILE_EVENT, { detail: profile }));
    }
    return !error;
  } catch {
    return false;
  }
}
