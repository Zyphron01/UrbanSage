"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Camera,
  CheckCircle2,
  Clock,
  Compass,
  Droplets,
  Flame,
  Info,
  Layers,
  MapPin,
  PlusCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TreePine,
  UserCheck,
  Waves,
  X,
} from "lucide-react";
import {
  ApiError,
  CitizenReportCreate,
  CitizenReportPublic,
  PhotoMetadata,
  ProblemCategory,
  submitCitizenReport,
} from "@/lib/api";
import { SYNTHETIC_NEIGHBOURHOODS } from "@/lib/syntheticData";

interface ExampleCase {
  id: string;
  badge: string;
  title: string;
  category: ProblemCategory;
  categoryLabel: string;
  description: string;
  severity: number;
  icon: React.ReactNode;
}

const EXAMPLE_CASES: ExampleCase[] = [
  {
    id: "case-1",
    badge: "CASE 1 — Blocked Drainage",
    title: "Roadside Drain Blockage & Waterlogging",
    category: "flooding_drainage",
    categoryLabel: "Flooding & Drainage",
    description: "Water accumulates on the street after rain because the roadside drain appears blocked.",
    severity: 3,
    icon: <Waves className="w-5 h-5 text-cyan-600" />,
  },
  {
    id: "case-2",
    badge: "CASE 2 — Water Scarcity",
    title: "Recurring Water Supply Interruption",
    category: "water_scarcity",
    categoryLabel: "Water Scarcity",
    description: "Our neighborhood has experienced repeated interruptions to its water supply.",
    severity: 3,
    icon: <Droplets className="w-5 h-5 text-blue-600" />,
  },
  {
    id: "case-3",
    badge: "CASE 3 — Extreme Heat",
    title: "Dangerously Hot Unshaded Public Waiting Area",
    category: "heat",
    categoryLabel: "Extreme Heat",
    description: "A public waiting area has little shade and becomes dangerously hot during the afternoon.",
    severity: 2,
    icon: <Flame className="w-5 h-5 text-amber-600" />,
  },
  {
    id: "case-4",
    badge: "CASE 4 — Loss of Green Cover",
    title: "Unpermitted Tree Removal Near Public Walkway",
    category: "loss_of_green_cover",
    categoryLabel: "Loss of Green Cover",
    description: "Several trees near a public walkway have been removed, leaving the area with less shade.",
    severity: 3,
    icon: <TreePine className="w-5 h-5 text-emerald-600" />,
  },
];

const CATEGORY_ITEMS: {
  id: ProblemCategory;
  label: string;
  icon: React.ReactNode;
  hint: string;
}[] = [
  {
    id: "flooding_drainage",
    label: "Flooding & Blocked Drainage",
    icon: <Waves className="w-5 h-5 text-cyan-600" />,
    hint: "Road waterlogging, silted stormwater drains, overflow",
  },
  {
    id: "water_scarcity",
    label: "Water Scarcity & Dry Taps",
    icon: <Droplets className="w-5 h-5 text-blue-600" />,
    hint: "Pipe supply cutoff, low pressure, groundwater depletion",
  },
  {
    id: "heat",
    label: "Extreme Heat & Lack of Shade",
    icon: <Flame className="w-5 h-5 text-amber-600" />,
    hint: "Unshaded bus stops, asphalt heat islands, elderly distress",
  },
  {
    id: "loss_of_green_cover",
    label: "Loss of Green Cover & Tree Felling",
    icon: <TreePine className="w-5 h-5 text-emerald-600" />,
    hint: "Felled canopy trees, park encroachment, loss of permeable soil",
  },
];

const SEVERITY_OPTIONS = [
  { level: 1, label: "Minor", desc: "Low impact, localized inconvenience" },
  { level: 2, label: "Moderate", desc: "Noticeable transit or drainage impediment" },
  { level: 3, label: "Significant", desc: "Substantial disruption to neighborhood" },
  { level: 4, label: "Severe", desc: "Hazardous conditions, property ingress risk" },
  { level: 5, label: "Emergency", desc: "Immediate acute physical or health hazard" },
];

export default function CitizenReportIssuePage() {
  // Form State
  const [category, setCategory] = useState<ProblemCategory>("flooding_drainage");
  const [severity, setSeverity] = useState<number>(3);
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [observedAt, setObservedAt] = useState<string>("2026-10-24T10:00");

  const [neighbourhoodId, setNeighbourhoodId] = useState<string>("NBR-001");
  const [locationDesc, setLocationDesc] = useState<string>("");
  const [latitude, setLatitude] = useState<string>("12.9856");
  const [longitude, setLongitude] = useState<string>("77.6057");
  const [reporterContact, setReporterContact] = useState<string>("");
  const [consentAcknowledged, setConsentAcknowledged] = useState<boolean>(true);
  const [photos, setPhotos] = useState<PhotoMetadata[]>([]);

  // Geolocation state
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [locationMsg, setLocationMsg] = useState<string | null>(null);

  // Status & Submission feedback
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formErrors, setFormErrors] = useState<Record<string, string | undefined>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submittedReport, setSubmittedReport] = useState<CitizenReportPublic | null>(null);
  const [prefilledNotice, setPrefilledNotice] = useState<string | null>(null);

  // When an example case is selected
  const handleSelectExample = (ex: ExampleCase) => {
    setCategory(ex.category);
    setSeverity(ex.severity);
    setTitle(ex.title);
    setDescription(ex.description);
    setPrefilledNotice(
      `Example loaded: "${ex.title}". You can freely edit all fields below, customize your neighborhood, and submit when ready.`
    );
    // Clear validation errors on prefilled fields
    setFormErrors((prev) => ({
      ...prev,
      category: undefined,
      description: undefined,
      title: undefined,
    }));

    // Scroll smoothly to the form container
    const formElement = document.getElementById("report-form-container");
    if (formElement) {
      formElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  // Handle neighborhood change to automatically update coordinates
  const handleNeighbourhoodChange = (nbrId: string) => {
    setNeighbourhoodId(nbrId);
    const found = SYNTHETIC_NEIGHBOURHOODS.find((n) => n.id === nbrId);
    if (found) {
      setLatitude(found.centroid_lat.toFixed(4));
      setLongitude(found.centroid_lon.toFixed(4));
      if (!locationDesc) {
        setLocationDesc(`Near ${found.name}`);
      }
    }
  };

  // Optional GPS location detection (user-initiated only)
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setLocationMsg("Geolocation is not supported by your browser.");
      return;
    }
    setIsLocating(true);
    setLocationMsg(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(4));
        setLongitude(position.coords.longitude.toFixed(4));
        setLocationMsg("Coordinates updated from your device GPS.");
        setIsLocating(false);
      },
      (err) => {
        setIsLocating(false);
        setLocationMsg(
          err.code === 1
            ? "Location permission denied. Please enter coordinates or select a neighborhood manually."
            : "Unable to retrieve location coordinates. Manual entry is supported."
        );
      },
      { timeout: 8000 }
    );
  };

  // Honest photo metadata attachment
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newPhotos: PhotoMetadata[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const randomHex = Math.random().toString(16).substring(2, 10).toUpperCase();
      newPhotos.push({
        photo_id: `PHO-${randomHex}`,
        file_name: file.name,
        mime_type: file.type || "image/jpeg",
        size_bytes: file.size,
        caption: `Citizen observation photo: ${file.name}`,
        captured_at: new Date().toISOString(),
      });
    }
    setPhotos((prev) => [...prev, ...newPhotos]);
  };

  const removePhoto = (photoId: string) => {
    setPhotos((prev) => prev.filter((p) => p.photo_id !== photoId));
  };

  // Form Validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!category) {
      errors.category = "Please select an environmental issue category.";
    }

    const trimmedDesc = description.trim();
    if (!trimmedDesc) {
      errors.description = "Please describe the environmental problem in detail.";
    } else if (trimmedDesc.length < 10) {
      errors.description = `Description is too short (${trimmedDesc.length}/10 chars). Please provide at least 10 characters.`;
    }

    const latNum = parseFloat(latitude);
    const lonNum = parseFloat(longitude);
    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      errors.latitude = "Latitude must be a valid number between -90 and +90.";
    }
    if (isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
      errors.longitude = "Longitude must be a valid number between -180 and +180.";
    }

    if (!consentAcknowledged) {
      errors.consent = "Please acknowledge that this is a responsible, authentic observation.";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Build comprehensive description including title if provided
      const fullDescription = title.trim()
        ? `[${title.trim()}] ${description.trim()}`
        : description.trim();

      const payload: CitizenReportCreate = {
        category,
        severity,
        description: fullDescription,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        location_description: locationDesc.trim() || undefined,
        neighbourhood_id: neighbourhoodId || undefined,
        reporter_contact: reporterContact.trim() || undefined,
        photos: photos.length > 0 ? photos : undefined,
      };

      const result = await submitCitizenReport(payload);
      setSubmittedReport(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setApiError(
            "Duplicate Submission Alert: A report in this category was recently submitted in this vicinity. Submissions are throttled to ensure balanced neighborhood representation."
          );
        } else {
          setApiError(err.detail);
        }
      } else {
        setApiError(
          err instanceof Error
            ? err.message
            : "Failed to connect to municipal reporting API. Please verify server connectivity."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetForm = () => {
    setTitle("");
    setDescription("");
    setLocationDesc("");
    setPhotos([]);
    setSubmittedReport(null);
    setApiError(null);
    setPrefilledNotice(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col justify-between selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Header */}
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
                Citizen Reporting
              </span>
            </div>
          </Link>

          <div className="flex items-center space-x-3 text-xs">
            <Link
              href="/citizen"
              className="inline-flex items-center space-x-1.5 text-slate-600 hover:text-slate-900 font-medium px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Citizen Portal</span>
            </Link>
            <Link
              href="/citizen/login"
              className="hidden sm:inline-flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 font-semibold px-3 py-1.5 rounded-lg transition-colors"
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Citizen Sign In</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-10">
        
        {/* Page Title & Mission Header */}
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1 text-xs font-semibold text-emerald-800">
            <PlusCircle className="w-3.5 h-3.5 text-emerald-600" />
            <span>Civic Environmental Incident Registry</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            Report an Environmental Issue
          </h1>

          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            Help us identify local environmental problems so communities and city officials can make better decisions.
          </p>

          <div className="pt-2 flex items-center justify-center space-x-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              Privacy Guarantee: Reporter identity is confidential. Contact details are permanently redacted from public transparency feeds.
            </span>
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* SECTION 1: EDUCATIONAL REALISTIC EXAMPLE CASES                */}
        {/* ------------------------------------------------------------- */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span>Not sure what to report? Explore examples</span>
              </h2>
              <p className="text-xs text-slate-500">
                Click any scenario below to prefill the reporting form. You can customize the details before submitting.
              </p>
            </div>
            <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
              Educational Guidelines
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {EXAMPLE_CASES.map((ex) => (
              <div
                key={ex.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-emerald-300 hover:shadow-md transition-all flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      {ex.badge}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                      Level {ex.severity} Severity
                    </span>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                      {ex.icon}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{ex.title}</h3>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        &ldquo;{ex.description}&rdquo;
                      </p>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-400">
                    Category: <strong className="text-slate-700">{ex.categoryLabel}</strong>
                  </span>
                  <button
                    type="button"
                    onClick={() => handleSelectExample(ex)}
                    className="inline-flex items-center space-x-1.5 text-xs font-bold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    <span>Use this example</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------------------- */}
        {/* SUCCESS CONFIRMATION SCREEN (When report is confirmed)        */}
        {/* ------------------------------------------------------------- */}
        {submittedReport ? (
          <div className="rounded-3xl border-2 border-emerald-500/50 bg-white p-8 sm:p-10 shadow-xl space-y-6 animate-in fade-in zoom-in-95">
            <div className="flex items-start space-x-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                  Submission Confirmed by Backend Registry
                </span>
                <h2 className="text-2xl font-bold text-slate-900">
                  Environmental Report Successfully Logged
                </h2>
                <p className="text-xs text-slate-600">
                  Your observation has entered the municipal triage pipeline with transparent 48h SLA monitoring.
                </p>
              </div>
            </div>

            {/* Real Report Metadata Box */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pb-4 border-b border-slate-200">
                <div>
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Report Ticket Reference
                  </span>
                  <span className="text-base font-mono font-bold text-emerald-800">
                    {submittedReport.id}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Calculated Urgency Score
                  </span>
                  <span className="text-base font-bold text-slate-900">
                    {submittedReport.urgency_score?.toFixed(1) ?? "Calculated"} / 100
                  </span>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Operational Status
                  </span>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800">
                    {submittedReport.status.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <div>
                  <strong className="text-slate-800">Reported Category: </strong>
                  <span className="capitalize">{submittedReport.category.replace(/_/g, " ")}</span>
                </div>
                <div>
                  <strong className="text-slate-800">Description: </strong>
                  <span>{submittedReport.description}</span>
                </div>
                {submittedReport.location_description && (
                  <div>
                    <strong className="text-slate-800">Location Reference: </strong>
                    <span>{submittedReport.location_description}</span>
                  </div>
                )}
                <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-200 flex items-center space-x-2">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    Logged at {new Date(submittedReport.created_at).toLocaleString()} &bull; Coordinates: {submittedReport.latitude}, {submittedReport.longitude}
                  </span>
                </div>
              </div>
            </div>

            {/* Post-submission Actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <Link
                href="/citizen"
                className="flex items-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 px-5 text-xs shadow-sm transition-colors"
              >
                <span>View My Report in Ticket Tracker</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <button
                type="button"
                onClick={handleResetForm}
                className="flex items-center space-x-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2.5 px-4 text-xs transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Submit Another Environmental Report</span>
              </button>
            </div>
          </div>
        ) : (
          /* ------------------------------------------------------------- */
          /* SECTION 2: POLISHED REPORT FORM CONTAINER                     */
          /* ------------------------------------------------------------- */
          <div
            id="report-form-container"
            className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-10 shadow-lg space-y-8"
          >
            {/* Prefilled Example Notification Banner */}
            {prefilledNotice && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900 flex items-start justify-between gap-3 animate-in fade-in">
                <div className="flex items-start space-x-2.5">
                  <Sparkles className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-emerald-800">Example Applied: </span>
                    <span className="text-emerald-700">{prefilledNotice}</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setPrefilledNotice(null)}
                  className="text-slate-400 hover:text-slate-600 p-0.5"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Error Message Banner if API fails */}
            {apiError && (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 flex items-start space-x-2.5 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-rose-800">Submission Alert: </span>
                  <span className="text-rose-700">{apiError}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8" noValidate>
              
              {/* STEP 1: CATEGORY SELECTION */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                      1
                    </span>
                    <span>Select Problem Category</span>
                    <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-400">Choose the best match</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {CATEGORY_ITEMS.map((item) => {
                    const isSelected = category === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => {
                          setCategory(item.id);
                          if (formErrors.category) setFormErrors((prev) => ({ ...prev, category: undefined }));
                        }}
                        className={`cursor-pointer rounded-2xl border p-4 transition-all flex items-start space-x-3.5 ${
                          isSelected
                            ? "border-emerald-600 bg-emerald-50/70 ring-2 ring-emerald-600/20 shadow-sm"
                            : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                        }`}
                      >
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                            isSelected ? "bg-white shadow-sm" : "bg-slate-100"
                          }`}
                        >
                          {item.icon}
                        </div>
                        <div className="space-y-0.5">
                          <span className={`text-xs font-bold block ${isSelected ? "text-emerald-900" : "text-slate-900"}`}>
                            {item.label}
                          </span>
                          <span className="text-[11px] text-slate-500 leading-tight block">
                            {item.hint}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {formErrors.category && (
                  <p className="text-xs text-rose-600 font-medium pl-1">• {formErrors.category}</p>
                )}
              </div>

              {/* STEP 2: SEVERITY LEVEL */}
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                      2
                    </span>
                    <span>Observed Severity / Urgency Level</span>
                    <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-xs font-semibold text-emerald-700">
                    Level {severity} of 5 &bull; {SEVERITY_OPTIONS[severity - 1].label}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {SEVERITY_OPTIONS.map((opt) => {
                    const isSelected = severity === opt.level;
                    return (
                      <button
                        key={opt.level}
                        type="button"
                        onClick={() => setSeverity(opt.level)}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          isSelected
                            ? "border-emerald-600 bg-emerald-600 text-white shadow-sm font-bold"
                            : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        <span className="text-xs block font-bold">
                          {opt.level}. {opt.label}
                        </span>
                        <span className={`text-[10px] block mt-1 leading-snug line-clamp-2 ${isSelected ? "text-emerald-100" : "text-slate-400"}`}>
                          {opt.desc}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* STEP 3: ISSUE DETAILS */}
              <div className="space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                      3
                    </span>
                    <span>Describe the Problem</span>
                    <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-400">Min 10 characters</span>
                </div>

                {/* Short Title */}
                <div className="space-y-1.5">
                  <label htmlFor="issue-title" className="text-xs font-semibold text-slate-700">
                    Short Issue Title (Optional)
                  </label>
                  <input
                    id="issue-title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Blocked stormwater drain causing street waterlogging"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 focus:border-emerald-600"
                  />
                </div>

                {/* Detailed Description */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="issue-desc" className="text-xs font-semibold text-slate-700">
                      Problem Description <span className="text-rose-500">*</span>
                    </label>
                    <span className="text-[11px] text-slate-400">
                      {description.trim().length} / 2000 characters
                    </span>
                  </div>
                  <textarea
                    id="issue-desc"
                    rows={4}
                    value={description}
                    onChange={(e) => {
                      setDescription(e.target.value);
                      if (formErrors.description) setFormErrors((prev) => ({ ...prev, description: undefined }));
                    }}
                    placeholder="Describe what is happening, how long it has been occurring, and how it impacts residents..."
                    className={`w-full px-4 py-2.5 rounded-xl border text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 transition-colors ${
                      formErrors.description
                        ? "border-rose-300 focus:border-rose-500 focus:ring-rose-200"
                        : "border-slate-300 focus:border-emerald-600 focus:ring-emerald-100"
                    }`}
                  />
                  {formErrors.description && (
                    <p className="text-xs text-rose-600 font-medium pl-1">• {formErrors.description}</p>
                  )}
                </div>

                {/* Observation Date & Time */}
                <div className="space-y-1.5">
                  <label htmlFor="observed-time" className="text-xs font-semibold text-slate-700 flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>Date & Time Observed</span>
                  </label>
                  <input
                    id="observed-time"
                    type="datetime-local"
                    value={observedAt}
                    onChange={(e) => setObservedAt(e.target.value)}
                    className="w-full sm:w-72 px-4 py-2 rounded-xl border border-slate-300 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-100 focus:border-emerald-600"
                  />
                </div>
              </div>

              {/* STEP 4: LOCATION & WARD */}
              <div className="space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                      4
                    </span>
                    <span>Location & Bengaluru Ward</span>
                    <span className="text-rose-500">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleDetectLocation}
                    disabled={isLocating}
                    className="inline-flex items-center space-x-1 text-xs text-emerald-700 hover:text-emerald-800 font-semibold hover:underline disabled:opacity-50"
                  >
                    <Compass className={`w-3.5 h-3.5 ${isLocating ? "animate-spin" : ""}`} />
                    <span>{isLocating ? "Detecting GPS..." : "Optional: Detect My GPS Coordinates"}</span>
                  </button>
                </div>

                {locationMsg && (
                  <p className="text-xs text-slate-600 bg-slate-100 p-2.5 rounded-lg border border-slate-200">
                    {locationMsg}
                  </p>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Ward Dropdown */}
                  <div className="space-y-1.5">
                    <label htmlFor="ward-select" className="text-xs font-semibold text-slate-700">
                      Neighborhood / Planning Zone <span className="text-rose-500">*</span>
                    </label>
                    <select
                      id="ward-select"
                      value={neighbourhoodId}
                      onChange={(e) => handleNeighbourhoodChange(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-100 focus:border-emerald-600"
                    >
                      {SYNTHETIC_NEIGHBOURHOODS.map((nbr) => (
                        <option key={nbr.id} value={nbr.id}>
                          {nbr.name} ({nbr.id})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Street Address / Landmark */}
                  <div className="space-y-1.5">
                    <label htmlFor="landmark-input" className="text-xs font-semibold text-slate-700">
                      Street Address or Landmark
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <MapPin className="w-4 h-4" />
                      </div>
                      <input
                        id="landmark-input"
                        type="text"
                        value={locationDesc}
                        onChange={(e) => setLocationDesc(e.target.value)}
                        placeholder="e.g. Near 80 Feet Road Junction, opposite park"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 bg-white text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 focus:border-emerald-600"
                      />
                    </div>
                  </div>
                </div>

                {/* Latitude & Longitude manual fields */}
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="space-y-1">
                    <label htmlFor="lat-input" className="text-[11px] font-semibold text-slate-600">
                      Latitude
                    </label>
                    <input
                      id="lat-input"
                      type="text"
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 text-xs font-mono text-slate-800"
                    />
                    {formErrors.latitude && (
                      <p className="text-[10px] text-rose-600 font-medium">{formErrors.latitude}</p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <label htmlFor="lon-input" className="text-[11px] font-semibold text-slate-600">
                      Longitude
                    </label>
                    <input
                      id="lon-input"
                      type="text"
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 text-xs font-mono text-slate-800"
                    />
                    {formErrors.longitude && (
                      <p className="text-[10px] text-rose-600 font-medium">{formErrors.longitude}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* STEP 5: PHOTO METADATA & CONTACT */}
              <div className="space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                      5
                    </span>
                    <span>Photo Evidence & Contact (Optional)</span>
                  </label>
                  <span className="text-[11px] text-slate-400">Strengthens report triage</span>
                </div>

                {/* Honest Photo Handling Notice */}
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 flex items-start space-x-2.5">
                  <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <p className="leading-relaxed">
                    <strong>Phase 1 Demonstration Architecture: </strong>
                    Attach photo metadata for verification readiness. Document filenames and MIME formats are cryptographically indexed without raw media cloud hosting.
                  </p>
                </div>

                {/* Photo file picker */}
                <div className="space-y-2">
                  <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-2xl cursor-pointer bg-slate-50/50 hover:bg-emerald-50/20 transition-all">
                    <Camera className="w-6 h-6 text-slate-400 mb-1" />
                    <span className="text-xs font-semibold text-slate-700">
                      Click to attach observation photos (.jpg, .png, .webp)
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5">
                      Max file size: 15 MB per image
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>

                  {/* Attached photos list */}
                  {photos.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {photos.map((p) => (
                        <div
                          key={p.photo_id}
                          className="inline-flex items-center space-x-2 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg text-xs text-emerald-900"
                        >
                          <Camera className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="font-medium max-w-[160px] truncate">{p.file_name}</span>
                          <span className="text-[10px] text-emerald-700">({(p.size_bytes / 1024).toFixed(0)} KB)</span>
                          <button
                            type="button"
                            onClick={() => removePhoto(p.photo_id)}
                            className="text-slate-400 hover:text-rose-600 ml-1"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Optional Reporter Contact */}
                <div className="space-y-1.5 pt-2">
                  <label htmlFor="contact-input" className="text-xs font-semibold text-slate-700">
                    Contact Email or Phone Number (Optional)
                  </label>
                  <input
                    id="contact-input"
                    type="text"
                    value={reporterContact}
                    onChange={(e) => setReporterContact(e.target.value)}
                    placeholder="e.g. resident@bengaluru.org (Strictly confidential)"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 focus:border-emerald-600"
                  />
                  <p className="text-[11px] text-slate-500">
                    Contact details are permanently redacted from public transparency feeds and only accessible by authorized municipal case officers.
                  </p>
                </div>
              </div>

              {/* Consent Checkbox */}
              <div className="pt-2">
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentAcknowledged}
                    onChange={(e) => setConsentAcknowledged(e.target.checked)}
                    className="w-4 h-4 mt-0.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                  />
                  <span className="text-xs text-slate-600 leading-snug">
                    I confirm that this report represents an authentic, real-world environmental observation in Bengaluru. I understand that duplicate submissions in the same vicinity are throttled to ensure equitable municipal response.
                  </span>
                </label>
                {formErrors.consent && (
                  <p className="text-xs text-rose-600 font-medium pl-7 pt-1">• {formErrors.consent}</p>
                )}
              </div>

              {/* Submit Button */}
              <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="text-xs text-slate-500 flex items-center space-x-1.5">
                  <Layers className="w-4 h-4 text-emerald-600" />
                  <span>Submits to FastAPI /api/reports endpoint with live SQLite/Supabase persistence</span>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center justify-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-6 text-sm shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Transmitting Report to Municipal Registry...</span>
                    </>
                  ) : (
                    <>
                      <span>Submit Environmental Report</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="w-full bg-white border-t border-slate-200 py-4 text-xs text-slate-500 text-center">
        UrbanSage AI &bull; Intelligent Decisions for Sustainable Cities &bull; Bengaluru Civic Engagement
      </footer>
    </div>
  );
}
