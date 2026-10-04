"use client";

import { useActionState, useState } from "react";
import { signIn, signUp } from "./actions";

type Props = {
  redirectTo: string;
  checkEmail: boolean;
};

export default function LoginForm({ redirectTo, checkEmail }: Props) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const action = mode === "signin" ? signIn : signUp;
  const [state, formAction, pending] = useActionState(action, undefined);

  return (
    <div className="w-full max-w-sm rounded-xl border border-black/10 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-white/5">
      <h1 className="text-xl font-semibold">
        {mode === "signin" ? "Iniciar sesión" : "Crear cuenta"}
      </h1>
      <p className="mt-1 text-sm text-black/60 dark:text-white/60">
        Driveway &amp; Foundation Estimator
      </p>

      {checkEmail && (
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          Revisa tu correo para confirmar la cuenta antes de iniciar sesión.
        </p>
      )}

      <form action={formAction} className="mt-6 space-y-4">
        <input type="hidden" name="redirectTo" value={redirectTo} />

        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            Correo
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            className="mt-1 w-full rounded-md border border-black/15 bg-transparent px-3 py-2 text-sm outline-none focus:border-[#f0a500] dark:border-white/15"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Contraseña
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={6}
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            className="mt-1 w-full rounded-md border border-black/15 bg-transparent px-3 py-2 text-sm outline-none focus:border-[#f0a500] dark:border-white/15"
          />
        </div>

        {state?.error && (
          <p className="text-sm text-red-600 dark:text-red-400">{state.error}</p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-md bg-[#f0a500] px-3 py-2 text-sm font-semibold text-black transition disabled:opacity-60"
        >
          {pending
            ? "Un momento…"
            : mode === "signin"
              ? "Entrar"
              : "Crear cuenta"}
        </button>
      </form>

      <button
        type="button"
        onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
        className="mt-4 text-sm text-black/60 underline hover:text-black dark:text-white/60 dark:hover:text-white"
      >
        {mode === "signin"
          ? "¿No tienes cuenta? Crear una"
          : "¿Ya tienes cuenta? Iniciar sesión"}
      </button>
    </div>
  );
}
