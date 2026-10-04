import LoginForm from "./login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ redirectTo?: string; checkEmail?: string }>;
}) {
  const params = await searchParams;

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <LoginForm
        redirectTo={params.redirectTo ?? "/dashboard"}
        checkEmail={params.checkEmail === "1"}
      />
    </main>
  );
}
