"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { TreePine, Globe, ShieldCheck, Mail, Lock, User, ArrowRight, CheckCircle2, AlertCircle, Building2, HardHat, UserCheck, KeyRound } from "lucide-react";
import { supabase } from "@/lib/supabaseClient";
import { setAuthToken, setActiveRole } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { t, language, setLanguage } = useLanguage();
  const [mode, setMode] = useState<"signin" | "signup" | "forgot">("signin");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password,
      });

      if (error) {
        if (error.message.toLowerCase().includes("email not confirmed")) {
          throw new Error(t("auth.unverifiedEmail"));
        }
        throw new Error(error.message || t("auth.invalidCreds"));
      }

      if (!data.session?.access_token) {
        throw new Error("Missing session credentials from Supabase Auth.");
      }

      const token = data.session.access_token;
      setAuthToken(token);

      // Verify server-side role
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const meRes = await fetch(`${apiUrl}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!meRes.ok) {
        throw new Error("Server-side authorization check failed.");
      }

      const profile = await meRes.json();
      const verifiedRole = profile.role as "citizen" | "administrator" | "contractor";

      setSuccessMsg(`${t("auth.roleVerifiedAs")} ${verifiedRole}`);
      setTimeout(() => {
        if (verifiedRole === "administrator") {
          setActiveRole("administrator", profile.user_id);
          router.push("/admin");
        } else if (verifiedRole === "contractor") {
          setActiveRole("contractor", profile.vendor_id || profile.user_id);
          router.push("/contractor");
        } else {
          setActiveRole("citizen", profile.user_id);
          router.push("/citizen");
        }
      }, 600);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : t("auth.invalidCreds"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      if (password !== confirmPassword) throw new Error(t("auth.passwordMismatch"));
      if (password.length < 6) throw new Error(t("auth.passwordTooShort"));

      const { data, error } = await supabase.auth.signUp({
        email: email.trim().toLowerCase(),
        password,
        options: {
          data: { full_name: fullName.trim() || undefined },
          emailRedirectTo: typeof window !== "undefined" ? window.location.origin : undefined,
        },
      });

      if (error) throw new Error(error.message);

      if (data.user && !data.session) {
        setSuccessMsg(t("auth.verificationSentDesc"));
      } else if (data.session) {
        setAuthToken(data.session.access_token);
        setActiveRole("citizen", data.user?.id || "citizen");
        router.push("/citizen");
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim().toLowerCase(), {
        redirectTo: typeof window !== "undefined" ? `${window.location.origin}/login#type=recovery` : undefined,
      });
      if (error) throw new Error(error.message);
      setSuccessMsg(t("auth.resetSentDesc"));
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to send reset email.");
    } finally {
      setIsLoading(false);
    }
  };

  const fillCredentials = (roleEmail: string, pass: string) => {
    setEmail(roleEmail);
    setPassword(pass);
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between font-sans selection:bg-teal-100 selection:text-teal-900">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-md px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center space-x-2.5 text-left group"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-white shadow-xs group-hover:bg-teal-700 transition-colors">
              <TreePine className="h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-slate-900">
                {t("app.title")}
              </span>
              <span className="block text-[11px] text-slate-500 font-medium">
                {t("app.tagline")}
              </span>
            </div>
          </button>

          {/* Language Selector */}
          <button
            type="button"
            onClick={() => setLanguage(language === "en" ? "kn" : "en")}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 transition-colors shadow-xs"
          >
            <Globe className="w-3.5 h-3.5 text-teal-600" />
            <span>{language === "en" ? "ಕನ್ನಡ" : "English"}</span>
          </button>
        </div>
      </header>

      {/* Main Login Form Container */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden p-6 sm:p-8 space-y-6">
          <div className="text-center space-y-1">
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Supabase Auth &bull; RBAC</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              {mode === "signin"
                ? t("auth.modalTitle")
                : mode === "signup"
                ? t("auth.signUpTitle")
                : t("auth.forgotTitle")}
            </h1>
            <p className="text-xs text-slate-500">
              {mode === "signin"
                ? t("auth.modalSubtitle")
                : mode === "signup"
                ? t("auth.signUpSubtitle")
                : t("auth.forgotSubtitle")}
            </p>
          </div>

          {errorMsg && (
            <div className="flex items-start space-x-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{errorMsg}</div>
            </div>
          )}

          {successMsg && (
            <div className="flex items-start space-x-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{successMsg}</div>
            </div>
          )}

          {/* Sign In Mode */}
          {mode === "signin" && (
            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.email")}</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t("auth.emailPlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-700">{t("auth.password")}</label>
                  <button
                    type="button"
                    onClick={() => {
                      setMode("forgot");
                      setErrorMsg(null);
                      setSuccessMsg(null);
                    }}
                    className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                  >
                    {t("auth.forgotPasswordLink")}
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t("auth.passwordPlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center space-x-2 rounded-lg bg-teal-600 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                {isLoading ? <span>{t("auth.signingIn")}</span> : (
                  <>
                    <span>{t("auth.signInBtn")}</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </>
                )}
              </button>

              <div className="pt-2 text-center border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setErrorMsg(null);
                    setSuccessMsg(null);
                  }}
                  className="text-xs font-medium text-teal-600 hover:text-teal-700 hover:underline"
                >
                  {t("auth.createCitizenLink")}
                </button>
              </div>

              {/* Demo Accounts */}
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-[11px] space-y-2">
                <div className="font-semibold text-slate-700 flex items-center justify-between">
                  <span>{t("auth.demoAccounts")}:</span>
                  <span className="text-[10px] text-slate-400">Click to autofill</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
                  <button
                    type="button"
                    onClick={() => fillCredentials("admin@urbansage.gov.in", "AdminSecure2026!")}
                    className="flex items-center space-x-1.5 p-1.5 rounded-md bg-white border border-slate-200 hover:border-teal-500 text-left text-slate-700 hover:bg-teal-50/50 transition-all"
                  >
                    <Building2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                    <span className="truncate font-medium">Administrator</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => fillCredentials("partner@bbmp-works.in", "PartnerSecure2026!")}
                    className="flex items-center space-x-1.5 p-1.5 rounded-md bg-white border border-slate-200 hover:border-indigo-500 text-left text-slate-700 hover:bg-indigo-50/50 transition-all"
                  >
                    <HardHat className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                    <span className="truncate font-medium">Infra Partner</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => fillCredentials("citizen@urbansage.in", "CitizenSecure2026!")}
                    className="flex items-center space-x-1.5 p-1.5 rounded-md bg-white border border-slate-200 hover:border-emerald-500 text-left text-slate-700 hover:bg-emerald-50/50 transition-all"
                  >
                    <UserCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span className="truncate font-medium">Citizen</span>
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Sign Up Mode */}
          {mode === "signup" && (
            <form onSubmit={handleSignUp} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.fullName")}</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder={t("auth.fullNamePlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.email")}</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t("auth.emailPlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.password")}</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("auth.passwordPlaceholder")}
                      className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.confirmPassword")}</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder={t("auth.passwordPlaceholder")}
                      className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center space-x-2 rounded-lg bg-teal-600 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                {isLoading ? <span>{t("auth.signingUp")}</span> : <span>{t("auth.signUpBtn")}</span>}
              </button>

              <div className="pt-2 text-center border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setErrorMsg(null);
                    setSuccessMsg(null);
                  }}
                  className="text-xs font-medium text-teal-600 hover:text-teal-700 hover:underline"
                >
                  {t("auth.backToSignIn")}
                </button>
              </div>
            </form>
          )}

          {/* Forgot Password Mode */}
          {mode === "forgot" && (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.email")}</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t("auth.emailPlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center space-x-2 rounded-lg bg-teal-600 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                {isLoading ? <span>{t("auth.sendingReset")}</span> : <span>{t("auth.sendResetBtn")}</span>}
              </button>

              <div className="pt-2 text-center border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setErrorMsg(null);
                    setSuccessMsg(null);
                  }}
                  className="text-xs font-medium text-teal-600 hover:text-teal-700 hover:underline"
                >
                  {t("auth.backToSignIn")}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        UrbanSage AI &bull; Supabase Auth Integrated &bull; Bengaluru
      </footer>
    </div>
  );
}
