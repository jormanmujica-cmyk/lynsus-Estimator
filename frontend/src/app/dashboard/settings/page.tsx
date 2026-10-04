import SettingsForm from "./settings-form";

export default function SettingsPage() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold text-white">Ajustes</h1>
      <p className="mt-1 text-sm text-white/40">
        Tu información y la de tu empresa — aparece en el menú y en el estimado que le mandas al cliente.
      </p>

      <div className="mt-6 max-w-2xl">
        <SettingsForm />
      </div>
    </main>
  );
}
