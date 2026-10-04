import DrivewayForm from "./driveway-form";

export default function DrivewayPage() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold text-white print:hidden">Driveway Estimator</h1>
      <p className="mt-1 text-sm text-white/40 print:hidden">
        Fórmulas de campo — concreto, rebar, forms, stakes, EJ y gravel.
      </p>

      <div className="mt-6">
        <DrivewayForm />
      </div>
    </main>
  );
}
