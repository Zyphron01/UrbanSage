"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Mail,
  Lock,
  User,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
  KeyRound,
  Building2,
  HardHat,
  UserCheck,
  Globe,
} from "lucide-react";
import { supabase } from "@/lib/supabaseClient";
import { setAuthToken, setActiveRole } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

interface UnifiedAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (role: "citizen" | "admin" | "contractor", email: string, name?: string) => void;
  initialMode?: "signin" | "signup" | "forgot" | "reset";
}

export function UnifiedAuthModal({
  isOpen,
  onClose,
  onLoginSuccess,
  initialMode = "signin",
}: UnifiedAuthModalProps) {
  const { t, language, setLanguage } = useLanguage();
  const [mode, setMode] = useState<"signin" | "signup" | "forgot" | "reset">(initialMode);

  // Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");

  // Status State
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    setMode(initialMode);
    setErrorMsg(null);
    setSuccessMsg(null);
  }, [initialMode, isOpen]);

  // Check URL hash for recovery tokens on mount
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash.includes("type=recovery")) {
      setMode("reset");
    }
  }, []);

  if (!isOpen) return null;

  // 1. Unified Sign In Handler
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

      // Verify server-side role via /api/auth/me
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const meRes = await fetch(`${apiUrl}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!meRes.ok) {
        throw new Error("Server-side token validation failed. Unauthorized session.");
      }

      const profile = await meRes.json();
      const verifiedRole = profile.role as "citizen" | "administrator" | "contractor";

      // Map verified backend role to UI portal
      let portalRole: "citizen" | "admin" | "contractor" = "citizen";
      if (verifiedRole === "administrator") {
        portalRole = "admin";
        setActiveRole("administrator", profile.user_id);
      } else if (verifiedRole === "contractor") {
        portalRole = "contractor";
        setActiveRole("contractor", profile.vendor_id || profile.user_id);
      } else {
        portalRole = "citizen";
        setActiveRole("citizen", profile.user_id);
      }

      setSuccessMsg(`${t("auth.roleVerifiedAs")} ${verifiedRole}`);
      setTimeout(() => {
        onLoginSuccess(portalRole, profile.email || email, profile.name);
        onClose();
      }, 700);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : t("auth.invalidCreds"));
    } finally {
      setIsLoading(false);
    }
  };

  // 2. Citizen Sign-Up Handler
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      if (password !== confirmPassword) {
        throw new Error(t("auth.passwordMismatch"));
      }
      if (password.length < 6) {
        throw new Error(t("auth.passwordTooShort"));
      }

      const redirectUrl = typeof window !== "undefined" ? window.location.origin : undefined;
      const { data, error } = await supabase.auth.signUp({
        email: email.trim().toLowerCase(),
        password,
        options: {
          data: {
            full_name: fullName.trim() || undefined,
          },
          emailRedirectTo: redirectUrl,
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      if (data.user && !data.session) {
        // Verification email dispatched
        setSuccessMsg(t("auth.verificationSentDesc"));
      } else if (data.session) {
        // Auto-confirmed or immediately verified
        setAuthToken(data.session.access_token);
        setActiveRole("citizen", data.user?.id || "citizen");
        onLoginSuccess("citizen", email, fullName);
        onClose();
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Password Recovery Request Handler
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const redirectUrl = typeof window !== "undefined" ? `${window.location.origin}/#type=recovery` : undefined;
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim().toLowerCase(), {
        redirectTo: redirectUrl,
      });

      if (error) {
        throw new Error(error.message);
      }

      setSuccessMsg(t("auth.resetSentDesc"));
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to send password recovery email.");
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Password Update Handler
  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      if (newPassword !== confirmNewPassword) {
        throw new Error(t("auth.passwordMismatch"));
      }
      if (newPassword.length < 6) {
        throw new Error(t("auth.passwordTooShort"));
      }

      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        throw new Error(error.message);
      }

      setSuccessMsg("Password updated successfully. You may now sign in.");
      setTimeout(() => {
        setMode("signin");
        setSuccessMsg(null);
      }, 1500);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update password.");
    } finally {
      setIsLoading(false);
    }
  };

  // Preset demo account fillers for convenience
  const fillCredentials = (roleEmail: string, pass: string) => {
    setEmail(roleEmail);
    setPassword(pass);
    setErrorMsg(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl border border-slate-200">
        {/* Header Ribbon */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-6 py-4">
          <div className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-white shadow-xs">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">{t("app.title")}</h2>
              <p className="text-[11px] text-slate-500">{t("auth.modalTitle")}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* Language Toggle in Modal */}
            <button
              type="button"
              onClick={() => setLanguage(language === "en" ? "kn" : "en")}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-teal-600" />
              <span>{language === "en" ? "ಕನ್ನಡ" : "English"}</span>
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Status Banners */}
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

          {/* ========================================================= */}
          {/* TAB 1: UNIFIED SIGN IN                                    */}
          {/* ========================================================= */}
          {mode === "signin" && (
            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{t("nav.signIn")}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{t("auth.modalSubtitle")}</p>
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
                {isLoading ? (
                  <span>{t("auth.signingIn")}</span>
                ) : (
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

              {/* Demo Provisioned Quick Fill */}
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

          {/* ========================================================= */}
          {/* TAB 2: CITIZEN REGISTRATION                               */}
          {/* ========================================================= */}
          {mode === "signup" && (
            <form onSubmit={handleSignUp} className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{t("auth.signUpTitle")}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{t("auth.signUpSubtitle")}</p>
              </div>

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

              <div className="rounded-lg bg-emerald-50/70 border border-emerald-100 p-2.5 text-[11px] text-emerald-800">
                Notice: Accounts registered here are automatically assigned the verified <strong>Citizen</strong> role. Privileged municipal roles cannot be self-assigned.
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

          {/* ========================================================= */}
          {/* TAB 3: FORGOT PASSWORD RECOVERY                           */}
          {/* ========================================================= */}
          {mode === "forgot" && (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{t("auth.forgotTitle")}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{t("auth.forgotSubtitle")}</p>
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

          {/* ========================================================= */}
          {/* TAB 4: PASSWORD RESET UPDATE                              */}
          {/* ========================================================= */}
          {mode === "reset" && (
            <form onSubmit={handleUpdatePassword} className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{t("auth.resetTitle")}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{t("auth.resetSubtitle")}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.newPassword")}</label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder={t("auth.passwordPlaceholder")}
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">{t("auth.confirmNewPassword")}</label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
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
                {isLoading ? <span>{t("auth.updatingPassword")}</span> : <span>{t("auth.updatePasswordBtn")}</span>}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
