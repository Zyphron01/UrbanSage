"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { PortalHeader } from "@/components/PortalHeader";
import { CitizenPortalView } from "@/components/CitizenPortalView";

export default function CitizenPage() {
  const router = useRouter();

  const handleSwitch = (portal: "gateway" | "citizen" | "admin" | "contractor") => {
    if (portal === "gateway") router.push("/");
    else if (portal === "admin") router.push("/admin");
    else if (portal === "contractor") router.push("/contractor");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-emerald-100 selection:text-emerald-900">
      <PortalHeader currentPortal="citizen" onSwitchPortal={handleSwitch} />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <CitizenPortalView />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-xs text-slate-500 text-center">
        UrbanSage AI &bull; Citizen Action & Transparency Portal &bull; Bengaluru
      </footer>
    </div>
  );
}
