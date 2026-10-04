"use client";

import { useEffect, useState } from "react";

function timeGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}

export default function WelcomeHeader({ email }: { email: string }) {
  // Arranca neutral en el server; el saludo por hora de día se calcula en el
  // navegador del usuario (el server no conoce su zona horaria real).
  const [greeting, setGreeting] = useState("Hola");
  useEffect(() => {
    setGreeting(timeGreeting());
  }, []);

  const name = email.split("@")[0] || "";
  const displayName = name ? name.charAt(0).toUpperCase() + name.slice(1) : "";

  return (
    <div>
      <h1 className="text-xl font-semibold text-white">
        {greeting}{displayName ? `, ${displayName}` : ""} 👋
      </h1>
      <p className="mt-1 text-sm text-white/40">
        Bienvenido a Lynsus Estimator — elige un estimador para empezar.
      </p>
    </div>
  );
}
