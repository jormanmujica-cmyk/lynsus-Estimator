"use client";

import { useState } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { AnimatePresence, motion } from "framer-motion";

export type HoverInfoStat = { label: string; value: string };

type HoverInfoCardProps = {
  /** La tarjeta/casilla que dispara el tooltip al pasar el mouse. */
  children: React.ReactNode;
  title: string;
  description: string;
  /** Contenido dinámico — ej. derivado de las props de la tarjeta. */
  stats?: HoverInfoStat[];
  side?: "top" | "right" | "bottom" | "left";
};

/**
 * Envoltorio de Radix Tooltip + Framer Motion: pop-up con scale 0.95 → 1 y
 * fade suave al aparecer (y a la inversa al desaparecer). El patrón
 * Tooltip.Content asChild + forceMount + AnimatePresence es el que permite
 * que Framer Motion controle la animación de salida (Radix por sí solo
 * desmonta el contenido de golpe, sin dar tiempo a animar el exit).
 */
export function HoverInfoCard({ children, title, description, stats, side = "top" }: HoverInfoCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip.Provider delayDuration={200} skipDelayDuration={100}>
      <Tooltip.Root open={open} onOpenChange={setOpen}>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <AnimatePresence>
          {open && (
            <Tooltip.Portal forceMount>
              <Tooltip.Content asChild side={side} sideOffset={10} collisionPadding={16}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 4 }}
                  transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
                  className="z-50 w-64 origin-[var(--radix-tooltip-content-transform-origin)] rounded-xl border border-white/10 bg-[#161c2c]/95 p-4 text-sm shadow-2xl shadow-black/40 backdrop-blur-xl"
                >
                  <p className="font-semibold text-[#f0a500]">{title}</p>
                  <p className="mt-1 text-white/70">{description}</p>

                  {stats && stats.length > 0 && (
                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-white/10 pt-3">
                      {stats.map((s) => (
                        <div key={s.label} className="flex flex-col">
                          <span className="text-[10px] uppercase tracking-wide text-white/40">
                            {s.label}
                          </span>
                          <span className="font-medium text-white">{s.value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <Tooltip.Arrow className="fill-[#161c2c]" />
                </motion.div>
              </Tooltip.Content>
            </Tooltip.Portal>
          )}
        </AnimatePresence>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
