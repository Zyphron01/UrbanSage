"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { PortalHeader } from "@/components/PortalHeader";
import { ContractorPortalView } from "@/components/ContractorPortalView";

export default function ContractorPage() {
  const router = useRouter();

  const handleSwitch = (portal: "gateway" | "citizen" | "admin" | "contractor") => {
    if (portal === "gateway") router.push("/");
    else if (portal === "citizen") router.push("/citizen");
    else if (portal === "admin") router.push("/admin");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <PortalHeader currentPortal="contractor" onSwitchPortal={handleSwitch} />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <ContractorPortalView />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-xs text-slate-500 text-center">
        UrbanSage AI &bull; Field Implementation & Contractor Execution Portal &bull; VND-BBMP-WORKS-01
      </footer>
    </div>
  );
}
