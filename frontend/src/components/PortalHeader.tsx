"use client";

import React, { useEffect, useState } from "react";
import {
  TreePine,
  UserCheck,
  HardHat,
  Building2,
  Compass,
  Globe,
  LogIn,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import {
  AppRole,
  fetchHealth,
  getActiveRole,
  getActiveUserId,
  setActiveRole,
  setAuthToken,
} from "@/lib/api";
import { supabase } from "@/lib/supabaseClient";
import { useLanguage } from "@/lib/i18n";
import { UnifiedAuthModal } from "./UnifiedAuthModal";

interface PortalHeaderProps {
  currentPortal: "gateway" | "citizen" | "admin" | "contractor";
  onSwitchPortal?: (portal: "gateway" | "citizen" | "admin" | "contractor") => void;
}

export function PortalHeader({ currentPortal, onSwitchPortal }: PortalHeaderProps) {
  const { t, language, setLanguage } = useLanguage();
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [activeRole, setActiveRoleState] = useState<AppRole>(getActiveRole());
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");

  // Health check polling
  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        await fetchHealth();
        if (mounted) setIsOnline(true);
      } catch {
        if (mounted) setIsOnline(false);
      }
    };

    check();
    const interval = setInterval(check, 20000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Supabase Auth Session listener
  useEffect(() => {
    let mounted = true;

    // Fetch initial session
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!mounted) return;
      if (session?.access_token) {
        setAuthToken(session.access_token);
        setUserEmail(session.user.email || null);
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const res = await fetch(`${apiUrl}/api/auth/me`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          });
          if (res.ok) {
            const profile = await res.json();
            const role = profile.role as AppRole;
            setActiveRole(role, profile.vendor_id || profile.user_id);
            setActiveRoleState(role);
          }
        } catch {
          // Fallback to existing role
        }
      }
    });

    // Subscribe to auth changes
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (!mounted) return;
        if (session?.access_token) {
          setAuthToken(session.access_token);
          setUserEmail(session.user.email || null);
          try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/auth/me`, {
              headers: { Authorization: `Bearer ${session.access_token}` },
            });
            if (res.ok) {
              const profile = await res.json();
              const role = profile.role as AppRole;
              setActiveRole(role, profile.vendor_id || profile.user_id);
              setActiveRoleState(role);
            }
          } catch {
            // Keep existing role
          }
        } else {
          setUserEmail(null);
          setAuthToken(null);
          setActiveRole("citizen", "CITIZEN-DEMO-01");
          setActiveRoleState("citizen");
        }
      }
    );

    return () => {
      mounted = false;
      authListener.subscription.unsubscribe();
    };
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUserEmail(null);
    setAuthToken(null);
    setActiveRole("citizen", "CITIZEN-DEMO-01");
    setActiveRoleState("citizen");
    if (onSwitchPortal) onSwitchPortal("gateway");
  };

  const handleLoginSuccess = (
    role: "citizen" | "admin" | "contractor",
    email: string
  ) => {
    setUserEmail(email);
    if (role === "admin") {
      setActiveRoleState("administrator");
      onSwitchPortal?.("admin");
    } else if (role === "contractor") {
      setActiveRoleState("contractor");
      onSwitchPortal?.("contractor");
    } else {
      setActiveRoleState("citizen");
      onSwitchPortal?.("citizen");
    }
  };

  const portalBadge = {
    gateway: {
      label: t("nav.gateway"),
      color: "bg-slate-100 text-slate-700 border-slate-200",
      icon: <Compass className="w-3.5 h-3.5 text-teal-600" />,
    },
    citizen: {
      label: t("nav.citizen"),
      color: "bg-emerald-50 text-emerald-800 border-emerald-200",
      icon: <UserCheck className="w-3.5 h-3.5 text-emerald-600" />,
    },
    admin: {
      label: t("nav.admin"),
      color: "bg-teal-50 text-teal-800 border-teal-200",
      icon: <Building2 className="w-3.5 h-3.5 text-teal-600" />,
    },
    contractor: {
      label: t("nav.contractor"),
      color: "bg-indigo-50 text-indigo-800 border-indigo-200",
      icon: <HardHat className="w-3.5 h-3.5 text-indigo-600" />,
    },
  }[currentPortal];

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-xs">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Brand & Portal Identity */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onSwitchPortal?.("gateway")}
              className="flex items-center space-x-3 text-left group focus:outline-none"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 shadow-xs group-hover:border-emerald-400 transition-colors">
                <TreePine className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold tracking-tight text-slate-900 text-base sm:text-lg">
                    {t("app.title")}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${portalBadge.color}`}
                  >
                    {portalBadge.icon}
                    {portalBadge.label}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 hidden sm:block">
                  {t("app.tagline")}
                </p>
              </div>
            </button>
          </div>

          {/* Navigation, Role Pills, Language Switcher, Auth */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Portal Switcher Tabs */}
            <div className="hidden lg:flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
              <button
                onClick={() => onSwitchPortal?.("citizen")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                  currentPortal === "citizen"
                    ? "bg-white text-emerald-800 border border-emerald-200 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>{t("nav.citizen")}</span>
              </button>

              <button
                onClick={() => {
                  if (activeRole !== "administrator" && !userEmail) {
                    setAuthMode("signin");
                    setIsAuthModalOpen(true);
                  } else {
                    onSwitchPortal?.("admin");
                  }
                }}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                  currentPortal === "admin"
                    ? "bg-white text-teal-800 border border-teal-200 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                <Building2 className="w-3.5 h-3.5 text-teal-600" />
                <span>{t("nav.admin")}</span>
              </button>

              <button
                onClick={() => {
                  if (activeRole !== "contractor" && activeRole !== "administrator" && !userEmail) {
                    setAuthMode("signin");
                    setIsAuthModalOpen(true);
                  } else {
                    onSwitchPortal?.("contractor");
                  }
                }}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                  currentPortal === "contractor"
                    ? "bg-white text-indigo-800 border border-indigo-200 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                <HardHat className="w-3.5 h-3.5 text-indigo-600" />
                <span>{t("nav.contractor")}</span>
              </button>
            </div>

            {/* Language Switcher Button (English <-> Kannada) */}
            <button
              type="button"
              onClick={() => setLanguage(language === "en" ? "kn" : "en")}
              className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
              title="Toggle English / ಕನ್ನಡ"
            >
              <Globe className="w-3.5 h-3.5 text-teal-600" />
              <span>{language === "en" ? "ಕನ್ನಡ" : "English"}</span>
            </button>

            {/* User Session & Auth Controls */}
            {userEmail ? (
              <div className="flex items-center space-x-2">
                <div className="hidden sm:flex items-center space-x-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-mono text-slate-700 shadow-xs">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                  <span className="font-semibold text-slate-900 max-w-[120px] truncate">
                    {userEmail}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-teal-50 border border-teal-200 text-teal-800 font-semibold uppercase">
                    {activeRole}
                  </span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-rose-700 hover:bg-rose-50 border border-slate-200 transition-colors"
                  title={t("nav.signOut")}
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{t("nav.signOut")}</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-1.5">
                <button
                  onClick={() => {
                    setAuthMode("signin");
                    setIsAuthModalOpen(true);
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-600 text-white hover:bg-teal-700 shadow-xs transition-colors"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>{t("nav.signIn")}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Unified Supabase Auth Modal */}
      <UnifiedAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
        initialMode={authMode}
      />
    </>
  );
}
