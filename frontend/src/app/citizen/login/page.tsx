"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Info,
  Lock,
  Mail,
  ShieldCheck,
  TreePine,
  UserCheck,
} from "lucide-react";
import { fetchDemoToken, setActiveRole } from "@/lib/api";
import { HeroBackground } from "@/components/ui/tweenly-hero-background";

export default function CitizenLoginPage() {
  const router = useRouter();

  // Form State
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [rememberMe, setRememberMe] = useState<boolean>(true);

  // Status & Feedback
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<{ email?: string; password?: string }>({});
  const [demoNotice, setDemoNotice] = useState<string | null>(null);

  const validate = (): boolean => {
    const errors: { email?: string; password?: string } = {};
    if (!email.trim()) {
      errors.email = "Please enter your email address or citizen ID.";
    } else if (email.includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = "Please enter a valid email format.";
    }

    if (!password) {
      errors.password = "Please enter your password.";
    } else if (password.length < 4) {
      errors.password = "Password must be at least 4 characters.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setDemoNotice(null);

    if (!validate()) {
      return;
    }

    setIsLoading(true);

    try {
      // Derive a safe citizen identifier from the email or handle
      const citizenHandle = email.trim().replace(/[^a-zA-Z0-9_-]/g, "-").toLowerCase();
      const userId = `CITIZEN-${citizenHandle || "RESIDENT-01"}`;

      // Authenticate against real backend /api/auth/token endpoint
      await fetchDemoToken("citizen", userId, "Bengaluru Residents Civic Council");
      setActiveRole("citizen");

      // Successful login navigation to Citizen Portal
      router.push("/citizen");
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Authentication failed. Unable to establish secure citizen session with the backend."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoCitizen = async () => {
    setEmail("citizen.bangalore@urban-sage.org");
    setPassword("DemoCitizen2026!");
    setErrorMessage(null);
    setValidationErrors({});
    setIsLoading(true);

    try {
      await fetchDemoToken("citizen", "CITIZEN-BLR-RESIDENT-01", "Bengaluru Residents Civic Council");
      setActiveRole("citizen");
      router.push("/citizen");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Quick login failed.");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col justify-between selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Simple Civic Header */}
      <header className="w-full bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center space-x-2.5 text-slate-900 hover:opacity-90 transition-opacity"
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <TreePine className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-slate-900">
                UrbanSage <span className="text-emerald-600">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs text-slate-500 font-medium border-l border-slate-200 pl-2">
                Citizen Portal
              </span>
            </div>
          </Link>

          <div className="flex items-center space-x-3 text-xs">
            <Link
              href="/"
              className="inline-flex items-center space-x-1.5 text-slate-600 hover:text-slate-900 font-medium px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Gateway</span>
            </Link>
            <Link
              href="/citizen/report"
              className="hidden sm:inline-flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 font-semibold px-3 py-1.5 rounded-lg transition-colors"
            >
              <span>Submit Report Without Account</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Dual-Column Body: Clean White Form + Integrated Hero Canvas */}
      <main className="flex-1 flex items-center justify-center py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-5xl bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
          
          {/* Left Column: Polished White-Theme Citizen Login Form (7 cols on lg) */}
          <div className="lg:col-span-7 p-6 sm:p-10 lg:p-12 flex flex-col justify-between bg-white z-10">
            <div className="space-y-6">
              
              {/* Badge & Welcome Header */}
              <div className="space-y-2">
                <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Citizen Observation & Transparency Portal</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                  Welcome back
                </h1>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Sign in to report environmental issues, track community verification milestones, and stay connected with your ward.
                </p>
              </div>

              {/* Informational Alert if active */}
              {demoNotice && (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs text-blue-900 flex items-start space-x-2.5 animate-in fade-in">
                  <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-semibold text-blue-800">Demonstration Identity System</p>
                    <p className="text-blue-700 leading-relaxed">{demoNotice}</p>
                  </div>
                </div>
              )}

              {/* Error Message if API fails */}
              {errorMessage && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 flex items-start space-x-2.5 animate-in fade-in">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-rose-800">Authentication Error: </span>
                    <span className="text-rose-700">{errorMessage}</span>
                  </div>
                </div>
              )}

              {/* Login Form */}
              <form onSubmit={handleSignIn} className="space-y-4" noValidate>
                {/* Email Field */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="email-input"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700"
                  >
                    Email address or Citizen ID <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      id="email-input"
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (validationErrors.email) setValidationErrors((prev) => ({ ...prev, email: undefined }));
                      }}
                      placeholder="citizen.bangalore@urban-sage.org"
                      className={`w-full pl-10 pr-4 py-2.5 rounded-xl border bg-white text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:outline-none focus:ring-2 ${
                        validationErrors.email
                          ? "border-rose-300 focus:border-rose-500 focus:ring-rose-200"
                          : "border-slate-300 focus:border-emerald-600 focus:ring-emerald-100"
                      }`}
                      disabled={isLoading}
                    />
                  </div>
                  {validationErrors.email && (
                    <p className="text-xs text-rose-600 font-medium pl-1 flex items-center space-x-1">
                      <span>•</span>
                      <span>{validationErrors.email}</span>
                    </p>
                  )}
                </div>

                {/* Password Field */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="password-input"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700"
                    >
                      Password <span className="text-rose-500">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        setDemoNotice(
                          "Automated password recovery via SMS/Email OTP is scheduled for Stage 6 production deployment. In this demonstration mode, test accounts authenticate directly with your citizen identifier."
                        )
                      }
                      className="text-xs font-medium text-emerald-700 hover:text-emerald-800 hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      id="password-input"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (validationErrors.password) setValidationErrors((prev) => ({ ...prev, password: undefined }));
                      }}
                      placeholder="••••••••••••"
                      className={`w-full pl-10 pr-11 py-2.5 rounded-xl border bg-white text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:outline-none focus:ring-2 ${
                        validationErrors.password
                          ? "border-rose-300 focus:border-rose-500 focus:ring-rose-200"
                          : "border-slate-300 focus:border-emerald-600 focus:ring-emerald-100"
                      }`}
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {validationErrors.password && (
                    <p className="text-xs text-rose-600 font-medium pl-1 flex items-center space-x-1">
                      <span>•</span>
                      <span>{validationErrors.password}</span>
                    </p>
                  )}
                </div>

                {/* Remember Me Checkbox */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center space-x-2.5 cursor-pointer text-xs text-slate-700">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 focus:ring-offset-0 cursor-pointer"
                    />
                    <span className="font-medium">Remember my session on this device</span>
                  </label>
                </div>

                {/* Sign In Primary Action Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full mt-2 flex items-center justify-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-4 text-sm shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Authenticating with Municipal Gateway...</span>
                    </>
                  ) : (
                    <>
                      <span>Sign in to Citizen Portal</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Demo 1-Click Fast Pass */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleQuickDemoCitizen}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center space-x-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-semibold py-2.5 px-4 text-xs transition-colors"
                >
                  <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Use Quick Demo Citizen Credentials</span>
                </button>
              </div>

              {/* Create Account Link */}
              <div className="pt-2 text-center text-xs text-slate-600">
                <span>Don&apos;t have an account yet? </span>
                <button
                  type="button"
                  onClick={() =>
                    setDemoNotice(
                      "Citizen account creation is open for all Bengaluru residents. For this evaluation deployment, entering any email above grants instant access with an authenticated citizen role."
                    )
                  }
                  className="font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
                >
                  Create an account
                </button>
              </div>
            </div>

            {/* Bottom Trust & Privacy Note */}
            <div className="pt-8 mt-6 border-t border-slate-100 flex items-center space-x-2 text-[11px] text-slate-500">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                Privacy Guarantee: Personal contact info is strictly confidential and never displayed in public transparency feeds.
              </span>
            </div>
          </div>

          {/* Right Column: HeroBackground Canvas Container (5 cols on lg) */}
          <div className="hidden lg:block lg:col-span-5 relative bg-gradient-to-br from-emerald-950 via-slate-900 to-slate-950 text-white overflow-hidden">
            {/* Interactive Hero Animation Component Reused */}
            <HeroBackground
              variant="waves"
              color="#10b981"
              accent="#34d399"
              background="transparent"
              size={1.6}
              opacity={0.45}
              speed={0.7}
              interactive={true}
              interaction="repel"
              clickRipple={true}
              mask="fade-edges"
              className="w-full h-full min-h-[640px] flex flex-col justify-between p-10 pointer-events-auto"
            >
              {/* Civic Impact Overlay */}
              <div className="relative z-10 space-y-6">
                <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-500/40 bg-emerald-900/60 px-3.5 py-1 text-xs font-semibold text-emerald-300 backdrop-blur-md">
                  <TreePine className="w-3.5 h-3.5 text-emerald-400" />
                  <span>UrbanSage AI Civic Network</span>
                </div>

                <div className="space-y-3">
                  <h2 className="text-2xl font-bold text-white tracking-tight leading-snug">
                    Intelligent Decisions for Sustainable Cities.
                  </h2>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Bridging grassroots citizen environmental observations with mathematical optimization and verified municipal field accountability.
                  </p>
                </div>
              </div>

              {/* Bottom Feature Cards Overlay */}
              <div className="relative z-10 space-y-3 pt-6 border-t border-emerald-500/20 text-xs">
                <div className="flex items-start space-x-3 bg-white/10 p-3.5 rounded-xl border border-white/20 backdrop-blur-md shadow-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white block">Transparent 48h SLA Triage</span>
                    <span className="text-[11px] text-slate-200">
                      Every submission receives algorithmic urgency scoring and community corroboration.
                    </span>
                  </div>
                </div>

                <div className="flex items-start space-x-3 bg-white/10 p-3.5 rounded-xl border border-white/20 backdrop-blur-md shadow-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white block">Citizen Resolution Sign-Off</span>
                    <span className="text-[11px] text-slate-200">
                      Municipal contractors cannot close tickets without resident physical verification.
                    </span>
                  </div>
                </div>

                <p className="text-[10px] text-emerald-300/80 pt-1 text-center font-mono">
                  Move cursor over canvas to interact with urban wave lines
                </p>
              </div>
            </HeroBackground>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="w-full bg-white border-t border-slate-200 py-4 text-xs text-slate-500 text-center">
        UrbanSage AI &bull; Bengaluru Urban Sustainability & Civic Transparency Platform
      </footer>
    </div>
  );
}
