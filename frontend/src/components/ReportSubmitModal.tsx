"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Droplets,
  Flame,
  Loader2,
  MapPin,
  ShieldCheck,
  TreePine,
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

interface ReportSubmitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (report: CitizenReportPublic) => void;
}

const CATEGORY_OPTIONS: {
  id: ProblemCategory;
  label: string;
  icon: React.ReactNode;
  desc: string;
}[] = [
  {
    id: "flooding_drainage",
    label: "Flooding & Drainage",
    icon: <Waves className="w-5 h-5 text-teal-600" />,
    desc: "Street waterlogging, drain blockages, runoff overflow",
  },
  {
    id: "water_scarcity",
    label: "Water Scarcity",
    icon: <Droplets className="w-5 h-5 text-blue-600" />,
    desc: "Dry taps, borewell depletion, tanker dependency",
  },
  {
    id: "heat",
    label: "Urban Heat Island",
    icon: <Flame className="w-5 h-5 text-amber-600" />,
    desc: "Extreme asphalt surface heat, lack of shade canopy",
  },
  {
    id: "loss_of_green_cover",
    label: "Loss of Green Cover",
    icon: <TreePine className="w-5 h-5 text-emerald-600" />,
    desc: "Tree felling, unpermitted clearing of permeable soil",
  },
];

const SEVERITY_LEVELS = [
  { level: 1, label: "Minor", desc: "Low impact, localized inconvenience" },
  { level: 2, label: "Moderate", desc: "Noticeable impediment to transit or access" },
  { level: 3, label: "Significant", desc: "Substantial disruption to neighborhood" },
  { level: 4, label: "Severe", desc: "Hazardous conditions, property ingress risk" },
  { level: 5, label: "Emergency", desc: "Immediate acute physical or health hazard" },
];

export function ReportSubmitModal({ isOpen, onClose, onSuccess }: ReportSubmitModalProps) {
  const [category, setCategory] = useState<ProblemCategory>("flooding_drainage");
  const [severity, setSeverity] = useState<number>(3);
  const [description, setDescription] = useState<string>("");
  const [latitude, setLatitude] = useState<string>("12.9716");
  const [longitude, setLongitude] = useState<string>("77.5946");
  const [locationDesc, setLocationDesc] = useState<string>("");
  const [neighbourhoodId, setNeighbourhoodId] = useState<string>("");
  const [reporterContact, setReporterContact] = useState<string>("");
  const [photos, setPhotos] = useState<PhotoMetadata[]>([]);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submittedReport, setSubmittedReport] = useState<CitizenReportPublic | null>(null);

  if (!isOpen) return null;

  // Handle local photo attachment metadata extraction
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newPhotos: PhotoMetadata[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // Generate client photo ID PHO-XXXXXXXX (8 hex)
      const randomHex = Math.random().toString(16).substring(2, 10).toUpperCase();
      newPhotos.push({
        photo_id: `PHO-${randomHex}`,
        file_name: file.name,
        mime_type: file.type || "image/jpeg",
        size_bytes: file.size,
        caption: `Evidence photo: ${file.name}`,
        captured_at: new Date().toISOString(),
      });
    }
    setPhotos([...photos, ...newPhotos]);
  };

  const handlePresetLocation = (lat: number, lon: number, wardId: string, name: string) => {
    setLatitude(lat.toFixed(4));
    setLongitude(lon.toFixed(4));
    setNeighbourhoodId(wardId);
    setLocationDesc(`Near ${name}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    // Validation checks
    const latNum = parseFloat(latitude);
    const lonNum = parseFloat(longitude);

    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      setErrorMsg("Latitude must be a valid number between -90 and 90.");
      return;
    }
    if (isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
      setErrorMsg("Longitude must be a valid number between -180 and 180.");
      return;
    }
    if (description.trim().length < 10) {
      setErrorMsg("Description must be at least 10 characters long.");
      return;
    }

    const payload: CitizenReportCreate = {
      category,
      severity,
      description: description.trim(),
      latitude: latNum,
      longitude: lonNum,
      location_description: locationDesc.trim() || undefined,
      neighbourhood_id: neighbourhoodId || undefined,
      reporter_contact: reporterContact.trim() || undefined,
      photos: photos.length > 0 ? photos : undefined,
    };

    setIsSubmitting(true);

    try {
      const result = await submitCitizenReport(payload);
      setSubmittedReport(result);
      onSuccess(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrorMsg(
            "Duplicate Submission Alert: A report in this category was recently submitted from your session in this vicinity. Duplicate reports are throttled to prevent artificial score inflation."
          );
        } else {
          setErrorMsg(err.detail);
        }
      } else {
        setErrorMsg("Failed to communicate with backend server. Check connectivity.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-xl p-6 my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                Submit Citizen Environmental Report
              </h2>
              <p className="text-xs text-slate-500">
                Direct crowd-sourced reporting with deterministic triaging scores
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Success View */}
        {submittedReport ? (
          <div className="py-6 space-y-6">
            <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto mb-2" />
              <h3 className="text-base font-bold text-slate-900">Report Successfully Submitted</h3>
              <p className="text-xs text-slate-600 mt-1">
                Persisted to local database and processed through scoring engine.
              </p>
              <div className="mt-3 inline-block rounded bg-white px-3 py-1 font-mono text-sm text-teal-800 border border-emerald-200 shadow-xs">
                {submittedReport.id}
              </div>
            </div>

            {/* Calculated Scores Display */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3.5">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Urgency Score
                </div>
                <div className="text-2xl font-black text-rose-700 mt-1 font-mono">
                  {submittedReport.urgency_score.toFixed(1)}
                  <span className="text-xs font-normal text-slate-400"> / 100</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Operational triaging priority based on severity & acute hazard weights.
                </p>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3.5">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Evidence Completeness
                </div>
                <div className="text-2xl font-black text-teal-700 mt-1 font-mono">
                  {submittedReport.evidence_confidence_score.toFixed(1)}
                  <span className="text-xs font-normal text-slate-400"> / 100</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Documentary richness (text length, GPS precision, attached photos).
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 flex items-start space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>
                <strong>Privacy Guaranteed:</strong> Reporter identity and contact details have been safely decoupled and will never appear in public views or API responses.
              </span>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 shadow-xs"
              >
                Close & Return to Dashboard
              </button>
            </div>
          </div>
        ) : (
          /* Submission Form */
          <form onSubmit={handleSubmit} className="py-4 space-y-4">
            {errorMsg && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* 1. Category Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                1. Environmental Problem Category <span className="text-rose-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORY_OPTIONS.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategory(cat.id)}
                    className={`flex items-start space-x-3 p-3 rounded-lg border text-left transition-all ${
                      category === cat.id
                        ? "bg-emerald-50/50 border-emerald-500 ring-1 ring-emerald-500 shadow-xs"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 shadow-xs"
                    }`}
                  >
                    <div className="mt-0.5">{cat.icon}</div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">{cat.label}</div>
                      <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                        {cat.desc}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Severity Rating */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  2. Assessed Severity Level <span className="text-rose-500">*</span>
                </label>
                <span className="text-xs font-bold text-amber-700 font-mono">
                  Level {severity} — {SEVERITY_LEVELS[severity - 1].label}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {SEVERITY_LEVELS.map((s) => (
                  <button
                    key={s.level}
                    type="button"
                    onClick={() => setSeverity(s.level)}
                    className={`py-2 rounded text-xs font-bold transition-all border ${
                      severity === s.level
                        ? "bg-amber-100 border-amber-500 text-amber-900 shadow-xs"
                        : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    {s.level}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                {SEVERITY_LEVELS[severity - 1].desc}
              </p>
            </div>

            {/* 3. Description Narrative */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  3. Description of Observed Issue <span className="text-rose-500">*</span>
                </label>
                <span className="text-[11px] text-slate-400 font-mono">
                  {description.length} / 2000 chars (min 10)
                </span>
              </div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the environmental disruption in detail (e.g. depth of standing water, duration of dry taps, felled tree species, affected roadway)..."
                rows={3}
                required
                className="w-full rounded-lg bg-white border border-slate-300 px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none shadow-xs"
              />
            </div>

            {/* 4. Geographic Location */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                4. Location Coordinates & Landmark <span className="text-rose-500">*</span>
              </label>

              {/* Quick Preset Wards */}
              <div className="flex flex-wrap gap-1.5 items-center mb-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                  Quick Wards:
                </span>
                {SYNTHETIC_NEIGHBOURHOODS.slice(0, 4).map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    onClick={() =>
                      handlePresetLocation(
                        w.centroid_lat,
                        w.centroid_lon,
                        w.id,
                        w.name
                      )
                    }
                    className="rounded bg-slate-100 px-2 py-0.5 text-[10px] text-slate-700 hover:bg-slate-200 border border-slate-200"
                  >
                    {w.name}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-slate-500">Latitude (-90 to 90)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    required
                    className="mt-0.5 w-full rounded bg-white border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 font-mono focus:border-emerald-500 focus:outline-none shadow-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-500">Longitude (-180 to 180)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    required
                    className="mt-0.5 w-full rounded bg-white border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 font-mono focus:border-emerald-500 focus:outline-none shadow-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] text-slate-500">Specific Landmark (Optional)</label>
                  <input
                    type="text"
                    value={locationDesc}
                    onChange={(e) => setLocationDesc(e.target.value)}
                    placeholder="e.g. Opposite Metro Pillar 142"
                    className="mt-0.5 w-full rounded bg-white border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-emerald-500 focus:outline-none shadow-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-500">Linked Ward (Optional)</label>
                  <select
                    value={neighbourhoodId}
                    onChange={(e) => setNeighbourhoodId(e.target.value)}
                    className="mt-0.5 w-full rounded bg-white border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-emerald-500 focus:outline-none shadow-xs"
                  >
                    <option value="">-- No specific ward --</option>
                    {SYNTHETIC_NEIGHBOURHOODS.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.id} — {w.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* 5. Contact & Photo Documentation */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="text-[11px] text-slate-700 font-semibold">
                  Follow-up Contact (Confidential)
                </label>
                <input
                  type="text"
                  value={reporterContact}
                  onChange={(e) => setReporterContact(e.target.value)}
                  placeholder="phone or email (never shown publicly)"
                  className="mt-0.5 w-full rounded bg-white border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-emerald-500 focus:outline-none shadow-xs"
                />
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Increases evidence completeness. Redacted from public views.
                </p>
              </div>

              <div>
                <label className="text-[11px] text-slate-700 font-semibold">
                  Attach Photo Evidence (Metadata)
                </label>
                <div className="mt-0.5 flex items-center space-x-2">
                  <label className="cursor-pointer inline-flex items-center space-x-1.5 rounded bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 border border-slate-300 shadow-xs">
                    <Camera className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Attach Photo</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                  <span className="text-[11px] text-slate-500">
                    {photos.length} photo(s) selected
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Phase 1 tracks metadata (size, time). Cloud S3 uploads deferred.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="rounded-lg bg-white border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center space-x-2 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 shadow-xs transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Submitting & Scoring...</span>
                  </>
                ) : (
                  <span>Submit Problem Report</span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
