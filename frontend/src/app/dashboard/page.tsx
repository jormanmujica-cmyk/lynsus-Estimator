import Link from "next/link";
import { ArrowRight, Building2, Check, Construction } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import WelcomeHeader from "@/components/welcome-header";
import { HoverInfoCard } from "@/components/hover-info-card";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();

  return (
    <main className="p-6">
      <WelcomeHeader email={data.user?.email ?? ""} />

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <EstimatorCard
          href="/dashboard/driveway"
          icon={Construction}
          title="Driveway"
          description="Cotización completa de driveways de concreto, con fórmulas de campo reales."
          features={[
            "Concreto, rebar, lumber/forms, EJ y gravel",
            "Waste factors por material",
            "Mano de obra por día o por SQFT",
            "Overhead, margen y extras",
            "Alertas si algo no cuadra antes de cotizar",
          ]}
        />
        <EstimatorCard
          icon={Building2}
          title="Foundation / Slab on Grade"
          description="Beams, slab, stirrups y forms — estándar Ethoscapes."
          features={[
            "Perfiles Ligero 10×8\" y Estándar 10×24\"",
            "Beams interiores automáticos por tipo de suelo",
            "Rebar #5 con splices y stirrups #3",
          ]}
          comingSoon
        />
      </div>

      <h2 className="mt-12 text-sm font-semibold uppercase tracking-wide text-[#f0a500]">
        🚀 Primeros pasos
      </h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <StepCard
          n={1}
          title="Elige un estimador"
          description="Driveway ya está listo. Foundation llega en la siguiente fase."
        />
        <StepCard
          n={2}
          title="Llena los datos del proyecto"
          description="Dimensiones, materiales, waste, mano de obra, equipo y margen."
        />
        <StepCard
          n={3}
          title="Revisa las alertas"
          description="Si algo no cuadra (precio en $0, margen en 0%) te lo marca en rojo antes de cotizar."
        />
      </div>
    </main>
  );
}

function EstimatorCard({
  href,
  icon: Icon,
  title,
  description,
  features,
  comingSoon,
}: {
  href?: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  features: string[];
  comingSoon?: boolean;
}) {
  const content = (
    <>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f0a500]/10 text-[#f0a500]">
            <Icon className="h-5 w-5" />
          </span>
          <h2 className="font-medium text-white">{title}</h2>
        </div>
        {comingSoon && (
          <span className="rounded-full bg-[#f0a500]/15 px-2 py-0.5 text-xs font-medium text-[#f0a500]">
            Próximamente
          </span>
        )}
      </div>

      <p className="mt-3 text-sm text-white/50">{description}</p>

      <ul className="mt-4 space-y-2">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-white/70">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#f0a500]" />
            {f}
          </li>
        ))}
      </ul>

      {href && (
        <div className="mt-5 flex items-center gap-1.5 text-sm font-medium text-[#f0a500]">
          Abrir estimador <ArrowRight className="h-4 w-4" />
        </div>
      )}
    </>
  );

  // Contenido del tooltip: dinámico, derivado de las props reales de la
  // tarjeta (no inventado) — cuántas categorías incluye y si ya está
  // disponible o sigue en "Próximamente".
  const stats = [
    { label: "Incluye", value: `${features.length} categorías` },
    { label: "Estado", value: comingSoon ? "Próximamente" : "Disponible" },
  ];

  if (href) {
    return (
      <HoverInfoCard title={title} description={description} stats={stats}>
        <Link
          href={href}
          className="block rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl transition hover:border-[#f0a500]/40 hover:bg-[#f0a500]/[0.06]"
        >
          {content}
        </Link>
      </HoverInfoCard>
    );
  }

  return (
    <HoverInfoCard title={title} description={description} stats={stats}>
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 opacity-60 shadow-lg shadow-black/20 backdrop-blur-xl">
        {content}
      </div>
    </HoverInfoCard>
  );
}

function StepCard({ n, title, description }: { n: number; title: string; description: string }) {
  return (
    <HoverInfoCard title={title} description={description} stats={[{ label: "Paso", value: `${n} de 3` }]}>
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20 backdrop-blur-xl">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f0a500]/15 text-sm font-semibold text-[#f0a500]">
          {n}
        </span>
        <h3 className="mt-3 text-sm font-medium text-white">{title}</h3>
        <p className="mt-1.5 text-sm text-white/50">{description}</p>
      </div>
    </HoverInfoCard>
  );
}
