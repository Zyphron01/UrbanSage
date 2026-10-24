"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CitizenReportPublic, fetchReports } from "@/lib/api";
import { PortalHeader } from "@/components/PortalHeader";
import { AdminPortalView } from "@/components/AdminPortalView";

export default function AdminPage() {
  const router = useRouter();
  const [reports, setReports] = useState<CitizenReportPublic[]>([]);
  const [totalReports, setTotalReports] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchReportsData = async () => {
    try {
      const data = await fetchReports({ limit: 50, offset: 0 });
      setReports(data.items);
      setTotalReports(data.total);
    } catch {
      // Graceful error handling
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchReports({ limit: 50, offset: 0 });
        if (!ignore) {
          setReports(data.items);
          setTotalReports(data.total);
          setIsLoading(false);
        }
      } catch {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const handleReportCreated = (newReport: CitizenReportPublic) => {
    setReports((prev) => [newReport, ...prev]);
    setTotalReports((prev) => prev + 1);
  };

  const handleSwitch = (portal: "gateway" | "citizen" | "admin" | "contractor") => {
    if (portal === "gateway") router.push("/");
    else if (portal === "citizen") router.push("/citizen");
    else if (portal === "contractor") router.push("/contractor");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-teal-100 selection:text-teal-900">
      <PortalHeader currentPortal="admin" onSwitchPortal={handleSwitch} />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <AdminPortalView
          reports={reports}
          totalReports={totalReports}
          isLoadingReports={isLoading}
          onRefreshReports={fetchReportsData}
          onReportCreated={handleReportCreated}
        />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-xs text-slate-500 text-center">
        UrbanSage AI &bull; Municipal Administration & Decision Support Command &bull; Bengaluru
      </footer>
    </div>
  );
}
