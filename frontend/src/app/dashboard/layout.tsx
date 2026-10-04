import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Sidebar from "@/components/sidebar";
import Topbar from "@/components/topbar";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();

  if (!data.user) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen w-full bg-[#0d1117]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar email={data.user.email ?? ""} />
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
